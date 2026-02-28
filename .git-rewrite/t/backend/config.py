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

# Airbyte Agent Connectors
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")
