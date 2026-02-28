import os
from dotenv import load_dotenv

load_dotenv()

# Vapi
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
VAPI_PUBLIC_KEY = os.getenv("VAPI_PUBLIC_KEY", "")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID", "")

# Vapi Tool IDs (comma-separated in env, or set individually)
VAPI_TOOL_IDS = os.getenv("VAPI_TOOL_IDS", "").split(",") if os.getenv("VAPI_TOOL_IDS") else []

# Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Senso Context OS
SENSO_API_KEY = os.getenv("SENSO_API_KEY", "")
SENSO_BASE_URL = os.getenv("SENSO_BASE_URL", "https://sdk.senso.ai/api/v1")

# Overshoot Vision AI
OVERSHOOT_API_KEY = os.getenv("OVERSHOOT_API_KEY", "")
OVERSHOOT_BASE_URL = os.getenv("OVERSHOOT_BASE_URL", "https://api.overshoot.ai")

# Modulate Velma 2 Voice Intelligence
MODULATE_API_KEY = os.getenv("MODULATE_API_KEY", "")

# Airbyte Agent Connectors
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")

# User Consult Call
USER_PHONE_NUMBER = os.getenv("USER_PHONE_NUMBER", "")   # Phone agent calls YOU
BACKEND_URL = os.getenv("BACKEND_URL", "https://agenthackathon.onrender.com")

# Gmail
# Option A (simplest): App Password — Google Account → Security → 2-Step → App Passwords
GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
# Option B: OAuth2 — run one-time local auth to get these three values
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN", "")
# Recipient (who receives the emails — can be same as sender)
GMAIL_RECIPIENT_EMAIL = os.getenv("GMAIL_RECIPIENT_EMAIL", "")
# Dashboard URL embedded in email buttons
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://agenthackathon.onrender.com")

# Modulate Velma 2 (voice emotion + PII + diarization)
MODULATE_API_KEY = os.getenv("MODULATE_API_KEY", "")

# Reka Vision (bill image / document analysis)
REKA_API_KEY = os.getenv("REKA_API_KEY", "")

# Yutori Scouts (proactive web monitoring)
YUTORI_API_KEY = os.getenv("YUTORI_API_KEY", "")
