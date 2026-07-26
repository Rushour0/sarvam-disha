# Disha voice-agent worker
Run: `agent/.venv/bin/python agent/main.py dev`
Env: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `SARVAM_API_KEY` are loaded from repo-root `.env`, then `.env.local`.
Events: every tool publishes reliable JSON on LiveKit data topic `disha` with `type`, Unix `ts`, and tool-specific fields.
Persistence: the same events append as one JSON object per line to `agent/cases/<room_name>.json`; existing events are never replaced.
