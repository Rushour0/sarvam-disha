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

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
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


# HMAC key for the session cookie. The default keeps the demo working out of
# the box; set a real value in the deployment env. The cookie only gates the
# student's own profile page — the OTP itself is still the hardcoded demo one,
# so this is a soft gate either way.
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


@app.post("/signup")
def create_signup(signup: SignupRequest, response: Response) -> dict:
    if len(signup.phone) != 10 or not signup.phone.isascii() or not signup.phone.isdigit():
        raise HTTPException(status_code=400, detail="phone must be exactly 10 digits")

    safe = _safe_name(signup.case)
    if not safe:
        raise HTTPException(status_code=400, detail="case must contain a valid filename character")

    event = {"type": "signup", "ts": int(time.time()), "phone": signup.phone}
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    _append_json_line(CASES_DIR / f"{safe}.json", event)

    # The browser reaches this route through the web app's /api/disha rewrite,
    # so the cookie lands on the product's own origin. HttpOnly keeps it out of
    # page scripts; the profile page forwards it back server-side.
    response.set_cookie(
        key=SESSION_COOKIE,
        value=mint_session(signup.phone),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"ok": True, "case": safe, "event": event}


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
