import os
from edupilot.tutor import make_agent

# Live (bidirectional audio) model for `adk web`; dev UI only, not the production deployment path.
root_agent = make_agent(os.environ.get("GEMINI_LIVE_MODEL", "gemini-live-2.5-flash-preview"))
