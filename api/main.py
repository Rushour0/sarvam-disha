"""Disha case API — serves session events written by the agent worker.

Reads the JSONL case files the worker appends under agent/cases/. Deployed
next to the worker (same host) so the filesystem is the single source of
truth; Mongo can replace this later without changing the response shapes.

Run: uvicorn main:app --host 0.0.0.0 --port 8090
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

import httpx
from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

CASES_DIR = Path(os.environ.get("DISHA_CASES_DIR", Path(__file__).resolve().parent.parent / "agent" / "cases"))

app = FastAPI(title="Disha case API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class SignupRequest(BaseModel):
    case: str
    phone: str


class OtpStartRequest(BaseModel):
    phone: str


class OtpVerifyRequest(BaseModel):
    phone: str
    code: str


# HMAC key for the session cookie. The default keeps the demo working out of
# the box; set a real value in the deployment env. The session is now only
# minted after a real Twilio-verified OTP (see /otp/verify), so this key is
# what makes the profile gate meaningful — set it in production.
SESSION_SECRET = (os.environ.get("DISHA_SESSION_SECRET") or "disha-demo-secret").encode()
SESSION_COOKIE = "disha_session"
SESSION_TTL_SECONDS = 180 * 24 * 3600


def _sign_session(phone: str, expires_at: int) -> str:
    message = f"{phone}.{expires_at}".encode()
    return hmac.new(SESSION_SECRET, message, hashlib.sha256).hexdigest()


def mint_session(phone: str) -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    return f"{phone}.{expires_at}.{_sign_session(phone, expires_at)}"


def verify_session(token: str | None) -> str | None:
    """Return the phone number a valid, unexpired session belongs to."""
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    phone, expires_text, signature = parts
    if not expires_text.isdigit() or int(expires_text) < time.time():
        return None
    if not hmac.compare_digest(signature, _sign_session(phone, int(expires_text))):
        return None
    return phone


def _safe_name(room: str) -> str:
    return "".join(c for c in room if c.isalnum() or c in "_-.")


def _read_events(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _append_json_line(path: Path, event: dict[str, object]) -> None:
    line = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, line)
    finally:
        os.close(descriptor)


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@app.get("/tree")
def get_tree() -> dict:
    """The full pathway tree for the front end to render.

    Flat node list with parent/child ids — the client builds whatever shape it
    needs (tree, breadcrumb, graph) without the server picking one.
    """
    path = DATA_DIR / "pathway_tree.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="pathway tree not built")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/scholarships")
def get_scholarships() -> list[dict]:
    """Scholarship schemes, each with the source it was read from."""
    path = DATA_DIR / "scholarships.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="scholarships not built")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict:
    return {"ok": True, "cases_dir": str(CASES_DIR), "exists": CASES_DIR.is_dir()}


@app.get("/cases")
def list_cases() -> list[dict]:
    # WARNING: This unauthenticated route exposes phone numbers and verbatim
    # wellbeing quotes. It must not be exposed publicly as-is.
    if not CASES_DIR.is_dir():
        return []
    out = []
    for path in sorted(CASES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        events = _read_events(path)
        flags = [e for e in events if e.get("type") == "flag"]
        constraints = {e["name"]: e["value"] for e in events if e.get("type") == "constraint" and "name" in e}
        summary = next((e for e in reversed(events) if e.get("type") == "summary"), None)
        signup = next((e for e in reversed(events) if e.get("type") == "signup"), None)
        out.append(
            {
                "room": path.stem,
                "updated": int(path.stat().st_mtime),
                "event_count": len(events),
                "flags": flags,
                "constraints": constraints,
                "has_summary": summary is not None,
                "phone": signup.get("phone") if signup is not None else None,
                "has_signup": signup is not None,
            }
        )
    return out


def _write_signup_and_cookie(case_safe: str, phone: str, response: Response) -> dict:
    """Append the signup event and set the session cookie on `response`.

    Shared by POST /signup and POST /otp/verify so both mint the session the
    exact same way. The browser reaches these routes through the web app's
    /api/disha rewrite, so the cookie lands on the product's own origin.
    HttpOnly keeps it out of page scripts; the profile page forwards it back
    server-side.
    """
    event = {"type": "signup", "ts": int(time.time()), "phone": phone}
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    _append_json_line(CASES_DIR / f"{case_safe}.json", event)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=mint_session(phone),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return event


# The old public POST /signup minted a session from a phone number alone, with
# no OTP — reachable directly through the /api/disha rewrite, so anyone could
# forge a session and read another student's profile. It is removed: a session
# is now only minted by /otp/verify after a real Twilio-verified code, through
# the shared _write_signup_and_cookie helper below.

TWILIO_VERIFY_BASE = "https://verify.twilio.com/v2/Services"
DEV_BYPASS_CODE = "123456"


def _twilio_config() -> tuple[str, str, str] | None:
    """Twilio Verify creds, or None if any are missing (fail closed).

    Read per-request so an unset secret yields a clean 503 rather than a
    boot-time crash.
    """
    sid = (os.environ.get("TWILIO_SID") or "").strip()
    token = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    service = (os.environ.get("TWILIO_VERIFY_SERVICE_SID") or "").strip()
    if not sid or not token or not service:
        return None
    return sid, token, service


def _dev_bypass_enabled() -> bool:
    """Local-dev escape hatch: accept the fixed code when Twilio is absent.

    Requires DISHA_OTP_DEV_BYPASS to be set and the service not marked
    production, so it can never be flipped on in the deployed image.
    """
    if not os.environ.get("DISHA_OTP_DEV_BYPASS"):
        return False
    return os.environ.get("DISHA_ENV", "").lower() != "production"


def _normalize_phone(raw: str) -> str:
    """Return exactly 10 digits or raise 400. We reject rather than repair —
    a wrong number silently 'fixed' would send an OTP to a stranger."""
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) != 10:
        raise HTTPException(status_code=400, detail="phone must be exactly 10 digits")
    return digits


@app.post("/otp/start")
def otp_start(req: OtpStartRequest) -> Response:
    """Send an SMS verification code via Twilio Verify."""
    phone = _normalize_phone(req.phone)
    config = _twilio_config()

    if config is None:
        if _dev_bypass_enabled():
            return JSONResponse({"ok": True})
        return JSONResponse({"ok": False, "error": "not_configured"}, status_code=503)

    sid, token, service = config
    try:
        twilio = httpx.post(
            f"{TWILIO_VERIFY_BASE}/{service}/Verifications",
            data={"To": f"+91{phone}", "Channel": "sms"},
            auth=(sid, token),
            timeout=10.0,
        )
    except httpx.HTTPError:
        return JSONResponse({"ok": False, "error": "send_failed"}, status_code=503)

    if twilio.is_success:
        return JSONResponse({"ok": True})
    if twilio.status_code == 429:
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)

    # Map Twilio's own error codes without echoing their payload (may hold PII).
    twilio_code = None
    try:
        twilio_code = twilio.json().get("code")
    except (ValueError, AttributeError):
        pass
    if twilio_code in (20429, 60203):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    if twilio_code == 60200 or twilio.status_code == 400:
        return JSONResponse({"ok": False, "error": "invalid_phone"}, status_code=400)
    return JSONResponse({"ok": False, "error": "send_failed"}, status_code=503)


@app.post("/otp/verify")
def otp_verify(req: OtpVerifyRequest) -> Response:
    """Check the SMS code; only an approved result mints the session.

    On success this reuses the exact /signup logic (write the signup event +
    set the disha_session cookie), so the browser can never obtain a session
    without a real approved code.
    """
    phone = _normalize_phone(req.phone)
    code = "".join(c for c in req.code if c.isdigit())
    if not code:
        return JSONResponse({"ok": False, "error": "invalid_request"}, status_code=400)

    config = _twilio_config()

    if config is None:
        if _dev_bypass_enabled():
            if code != DEV_BYPASS_CODE:
                return JSONResponse({"ok": False, "error": "invalid_code"}, status_code=400)
            return _mint_otp_session(phone)
        return JSONResponse({"ok": False, "error": "not_configured"}, status_code=503)

    sid, token, service = config
    try:
        twilio = httpx.post(
            f"{TWILIO_VERIFY_BASE}/{service}/VerificationCheck",
            data={"To": f"+91{phone}", "Code": code},
            auth=(sid, token),
            timeout=10.0,
        )
    except httpx.HTTPError:
        return JSONResponse({"ok": False, "error": "verify_failed"}, status_code=503)

    approved = False
    if twilio.is_success:
        try:
            approved = twilio.json().get("status") == "approved"
        except (ValueError, AttributeError):
            approved = False
    elif twilio.status_code == 429:
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    # A 404 (expired/consumed) or any non-approved status falls through to 400.

    if not approved:
        return JSONResponse({"ok": False, "error": "invalid_code"}, status_code=400)

    return _mint_otp_session(phone)


def _mint_otp_session(phone: str) -> Response:
    case = f"case_91{phone}"
    safe = _safe_name(case)
    response = JSONResponse({"ok": True, "case": safe})
    _write_signup_and_cookie(safe, phone, response)
    return response


@app.get("/me")
def get_me(disha_session: str | None = Cookie(default=None)) -> dict:
    """The signed-in student's own case, resolved from the session cookie.

    Unlike /cases this only ever returns the caller's own rows, so it can sit
    behind the public rewrite without basic auth.
    """
    phone = verify_session(disha_session)
    if phone is None:
        raise HTTPException(status_code=401, detail="no valid session")

    case = f"case_91{phone}"
    path = CASES_DIR / f"{case}.json"
    events = _read_events(path) if path.is_file() else []
    return {"phone": phone, "case": case, "events": events}


@app.get("/cases/{room}")
def get_case(room: str) -> dict:
    safe = _safe_name(room)
    path = CASES_DIR / f"{safe}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="case not found")
    return {"room": safe, "events": _read_events(path)}
