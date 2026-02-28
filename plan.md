# LifePilot — Build Plan v2

## Hackathon: Autonomous Agents, Feb 27

---

## What's Already Built

| Component | Status | Details |
|-----------|--------|---------|
| FastAPI Backend | DONE | 15 files, all endpoints tested, deployed to Render |
| Vapi Assistant | DONE | Deepgram Nova-3 + Groq Llama 3.3 70B + ElevenLabs Flash v2.5 |
| Vapi Tools (5x) | DONE | search_task_context, tavily_search, extract_entities, update_neo4j, end_task |
| Render Deploy | DONE | `https://agenthackathon.onrender.com` |
| GitHub Repo | DONE | `https://github.com/neelb1/agenthackathon` |
| Tavily Service | DONE (code) | Search + pre-call research, needs API key |
| Neo4j Service | DONE (code) | Graph CRUD + seed data, needs AuraDB setup |
| SSE Streaming | DONE | `/api/events` ready for dashboard |
| Task Engine | DONE | CRUD + trigger + research + call flow |

---

## The Pivot: Sponsor-Aligned Architecture

### Old Plan
Vapi + Neo4j + Tavily + Hume AI + Yutori

### New Plan (Feb 27 hackathon sponsors)
Vapi + Neo4j + Tavily + **Senso** + **Airbyte** + **Overshoot** + **Render**

### Why
- **Senso** (Context OS) = verified knowledge layer for grounded call scripts. Judge-impressing "responsible AI" angle.
- **Airbyte** (Agent Connectors) = pull financial data from multiple sources into Neo4j. 21 standalone pip packages.
- **Overshoot** (Vision AI) = monitor live financial broadcasts for threats. Creative differentiator no one else will do.
- **Render** = full-stack deploy (web service + background workers). Already deployed.
- Drop Hume AI (not a sponsor). Drop Yutori (not a sponsor). Keep Vapi, Neo4j, Tavily (still core).

---

## Architecture (5 Layers)

```
Layer 1: DATA INGESTION (eyes)
  Airbyte Agent Connectors → pull financial data from Stripe, Gmail, Slack
  Overshoot Vision API → monitor live CNBC/Bloomberg for breaking financial news
  Tavily Search → discover URLs, extract content, research leverage

Layer 2: KNOWLEDGE & CONTEXT (brain)
  Neo4j AuraDB → knowledge graph of user's financial life
  Senso Context OS → verified compliance policies, resolution scripts, grounded answers

Layer 3: TASK ENGINE (coordinator)
  FastAPI on Render → receives triggers, researches context, queues calls
  Background Worker → persistent monitoring loop (Render background worker)

Layer 4: VOICE AGENT (mouth)
  Vapi → outbound calls with Deepgram + Groq + ElevenLabs
  5 custom tools → search context, web search, extract entities, update graph, end task

Layer 5: DASHBOARD (face)
  React + Neovis.js → 3-panel live view (tasks / call transcript / graph)
  SSE streaming → real-time updates from backend
```

### Data Flow

```
Airbyte pulls Stripe transactions → detects bill increase
  OR Overshoot spots "Comcast rate hike" on CNBC stream
  OR Tavily search finds your provider raised rates
    ↓
Task Engine creates task → researches via Tavily + Senso
    ↓
Vapi makes outbound call → agent negotiates using Senso-grounded scripts
    ↓
During call: extract entities → update Neo4j graph → stream to dashboard
    ↓
Dashboard shows live transcript, growing graph, savings counter
```

---

## Sponsor Integration Map

| Sponsor | Layer | Integration | Depth |
|---------|-------|-------------|-------|
| **Render** | All | Web Service + Background Worker + render.yaml | Full stack, infrastructure-as-code |
| **Airbyte** | 1 | Agent Connectors (Stripe, Gmail, Slack) pull financial data | Standalone pip packages, entity-action pattern |
| **Senso** | 2 | Context OS grounds call scripts in verified policies | /search, /generate, /triggers endpoints |
| **Neo4j** | 2 | Knowledge graph grows live during calls | Cypher, Neovis.js visualization |
| **Tavily** | 1+3 | Pre-call research + mid-call web search | Advanced search, intent enrichment |
| **Vapi** | 4 | Voice calling with 5 custom tools | Outbound calls, tool dispatch, analysis |
| **Overshoot** | 1 | Vision AI monitors financial news broadcasts | Real-time VLM on video, structured extraction |

**7 sponsors integrated. Hackathon requires 3.**

---

## Judge Strategy

### Vladimir de Turckheim (Node.js core, security)
**Wants:** Simple architecture, no frameworks, security-first, observability
**Our play:**
- Present as "a loop, some tools, and a prompt" — no LangGraph/LangChain
- Show structured logging: what the agent decided and why
- Input validation on all endpoints, rate limiting on LLM calls
- Financial data handled with proper auth + audit trail

### Jon Turdiev (AWS SA, cybersecurity, hackathon organizer)
**Wants:** Secure agents, enterprise-grade, proper data handling, demo quality
**Our play:**
- Encryption, access controls, audit trails on financial data
- Mention AWS as production-scale path (Bedrock, Connect, Neptune)
- Clean live demo with backup video
- Show full render.yaml defining entire stack as IaC

### Andrew Bihl (Numeric CTO, ex-Segment/Twilio)
**Wants:** Clean data pipelines, event-driven architecture, real financial problems
**Our play:**
- Frame as "Numeric watches inside your books; LifePilot watches the outside world"
- Airbyte connectors = clean data pipeline from multiple sources
- Event-driven: webhook triggers → task creation → call execution
- Real financial use case (bill negotiation, cancellation)

### Senso Team
**Wants:** Creative use of Context OS, grounded AI, verified knowledge
**Our play:**
- Ingest compliance playbooks + resolution scripts into Senso
- Agent queries /search before calls for verified procedures
- /generate drafts call scripts grounded in real policies
- /triggers classify threat types (BILLING_INCREASE, FRAUD_ALERT)

### Airbyte Team
**Wants:** Meaningful connector usage, AI agents interacting with multiple systems
**Our play:**
- Stripe connector: detect billing anomalies
- Slack connector: send threat alerts to user
- Multiple connectors showing real multi-source data integration
- Not just an API call — genuine data pipeline into Neo4j

### Overshoot Team (YC W26, won 3 hackathons)
**Wants:** Creative, surprising use of vision AI, working real-time demo
**Our play:**
- Monitor financial news broadcasts via screen capture
- VLM extracts structured financial data before text feeds
- The "eyes" layer no other team will think of
- Sub-200ms latency for real-time demo wow-factor

### Render Team (Ojus Save, Shifra Williams)
**Wants:** Full platform usage, Background Workers, render.yaml, IaC
**Our play:**
- Web Service (FastAPI dashboard API)
- Background Worker (persistent monitoring agent loop)
- render.yaml defines entire stack
- Managed Postgres potential for persistence upgrade

---

## Build Order (Priority-Sorted)

### Sprint 1: Core Backend — COMPLETE
1. [x] FastAPI app with CORS, health check
2. [x] Vapi tool-call router (all 5 tools)
3. [x] Vapi webhook receiver
4. [x] Task store + task engine
5. [x] Neo4j service (graceful when not configured)
6. [x] Tavily service (graceful when no key)
7. [x] Vapi outbound call service
8. [x] SSE streaming endpoint
9. [x] Deploy to Render

### Sprint 2: Sponsor Integrations (HIGH PRIORITY)
10. [ ] Set up Neo4j AuraDB Free — add URI/password to Render env vars
11. [ ] Get Tavily API key — add to Render env vars
12. [ ] Add Senso service (`services/senso_service.py`)
      - POST /content/raw — ingest compliance docs
      - POST /search — query verified knowledge before calls
      - POST /generate — draft call scripts from policies
      - Wire into search_task_context tool (Senso grounds the context)
13. [ ] Add Airbyte connector service (`services/airbyte_service.py`)
      - `pip install airbyte-agent-stripe` — detect billing anomalies
      - `pip install airbyte-agent-slack` — send threat alerts
      - Entity-action pattern: `connector.execute("charges", "list", {...})`
      - Wire into monitoring loop / task creation
14. [ ] Add Overshoot service (`services/overshoot_service.py`)
      - REST API at api.overshoot.ai
      - Point at screen capture of financial news
      - VLM prompt: "Extract any financial rate changes, billing announcements, or price increases"
      - Push detected threats into task queue
15. [ ] Add Senso /triggers for threat classification
16. [ ] Test all integrations end-to-end

### Sprint 3: Background Worker + Monitoring Loop
17. [ ] Create `worker/monitor.py` — persistent background agent
      - Runs on Render Background Worker (no timeout limit)
      - Loop: check Airbyte sources → check Overshoot → check Tavily
      - On detection: create task → optionally auto-trigger call
18. [ ] Add to render.yaml as `type: worker`
19. [ ] Add structured logging (what agent decided and why — for Vladimir)
20. [ ] Add audit trail for financial data access (for Jon)

### Sprint 4: Dashboard (DEMO WOW)
21. [ ] Scaffold React + Vite + Tailwind frontend
22. [ ] TaskQueue component (left panel — detected threats + task status)
23. [ ] LiveCallView component (center — real-time transcript streaming)
24. [ ] KnowledgeGraph component (right — Neovis.js force graph)
25. [ ] SSE hook connecting to `/api/events`
26. [ ] "Handle It" button → POST /api/tasks/:id/trigger
27. [ ] Savings counter (total saved across all tasks)
28. [ ] Deploy frontend on Render as Static Site

### Sprint 5: Polish + Demo Prep
29. [ ] Pre-record demo video (OBS)
30. [ ] Buy Vapi phone number for live demo
31. [ ] Seed Neo4j with rich demo data
32. [ ] Ingest compliance docs into Senso
33. [ ] Prepare backup slides
34. [ ] Test full flow end-to-end 3x
35. [ ] Pre-warm Render before demo slot

---

## New Services to Build

### `services/senso_service.py`

```python
import httpx
import config

SENSO_BASE = "https://sdk.senso.ai/api/v1"
HEADERS = {"X-API-Key": config.SENSO_API_KEY, "Content-Type": "application/json"}

async def ingest_content(title: str, text: str) -> dict:
    """Ingest compliance docs / resolution scripts into Senso."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SENSO_BASE}/content/raw",
            headers=HEADERS,
            json={"title": title, "summary": title, "text": text})
        return resp.json()

async def search_knowledge(query: str, max_results: int = 3) -> str:
    """Query Senso for verified, grounded context. Used before/during calls."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SENSO_BASE}/search",
            headers=HEADERS,
            json={"query": query, "max_results": max_results})
        data = resp.json()
        # Return answer + sources as single-line string for Vapi
        answer = data.get("answer", "")
        return answer.replace("\n", " ").strip()

async def generate_script(instructions: str) -> str:
    """Generate a call script grounded in ingested knowledge."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SENSO_BASE}/generate",
            headers=HEADERS,
            json={"content_type": "call_script", "instructions": instructions})
        return resp.json().get("content", "")

async def classify_threat(text: str) -> str:
    """Use Senso triggers to classify threat type."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SENSO_BASE}/triggers",
            headers=HEADERS,
            json={"text": text})
        return resp.json().get("classification", "unknown")
```

### `services/airbyte_service.py`

```python
# Standalone agent connectors — no Airbyte platform needed
# pip install airbyte-agent-stripe airbyte-agent-slack

async def check_stripe_charges(api_key: str, days: int = 30) -> list[dict]:
    """Pull recent charges from Stripe, detect anomalies."""
    from airbyte_agent_stripe import StripeConnector
    from airbyte_agent_stripe.models import StripeApiKeyAuthConfig

    connector = StripeConnector(
        auth_config=StripeApiKeyAuthConfig(api_key=api_key)
    )
    result = await connector.execute("charges", "list", {
        "limit": 50,
        "created": {"gte": int(time.time()) - (days * 86400)}
    })
    return result.data

async def send_slack_alert(token: str, channel: str, message: str):
    """Send threat alert to user's Slack."""
    from airbyte_agent_slack import SlackConnector
    from airbyte_agent_slack.models import SlackBotTokenAuthConfig

    connector = SlackConnector(
        auth_config=SlackBotTokenAuthConfig(token=token)
    )
    await connector.execute("messages", "create", {
        "channel": channel,
        "text": message
    })
```

### `services/overshoot_service.py`

```python
import httpx
import config

OVERSHOOT_BASE = "https://api.overshoot.ai"

async def analyze_financial_broadcast(video_url: str) -> dict:
    """Point Overshoot at a financial news stream, extract structured data."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{OVERSHOOT_BASE}/analyze",
            headers={
                "Authorization": f"Bearer {config.OVERSHOOT_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "source": video_url,
                "prompt": (
                    "Extract any financial announcements: rate changes, "
                    "price increases, service cancellations, billing updates. "
                    "Return structured JSON with company, change_type, "
                    "old_value, new_value, and summary."
                ),
                "model": "qwen3-vl-30b",
            })
        return resp.json()
```

---

## Updated Environment Variables

```env
# Vapi
VAPI_API_KEY=
VAPI_PUBLIC_KEY=
VAPI_ASSISTANT_ID=
VAPI_PHONE_NUMBER_ID=
VAPI_TOOL_IDS=

# Neo4j AuraDB
NEO4J_URI=
NEO4J_USER=neo4j
NEO4J_PASSWORD=

# Tavily
TAVILY_API_KEY=

# Senso Context OS
SENSO_API_KEY=

# Airbyte Agent Connectors
STRIPE_API_KEY=
SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=

# Overshoot Vision AI
OVERSHOOT_API_KEY=
```

---

## Updated render.yaml

```yaml
services:
  # API + Webhook server
  - type: web
    name: lifepilot-backend
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars: [all env vars above]

  # Persistent monitoring agent (no timeout!)
  - type: worker
    name: lifepilot-monitor
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: python -m worker.monitor
    envVars: [all env vars above]

  # Dashboard frontend
  - type: web
    name: lifepilot-dashboard
    runtime: static
    rootDir: frontend
    buildCommand: npm install && npm run build
    staticPublishPath: dist
```

---

## Updated Demo Script (3 minutes)

### 0:00-0:15 — Problem
> "Americans lose $120 billion a year to hidden fees, rate hikes, and subscriptions they forgot to cancel. The phone call to fix it takes 45 minutes on average. Nobody wants to make that call."

### 0:15-0:30 — Solution
> "LifePilot is an autonomous AI agent that monitors your financial life, detects threats, and makes the phone calls to resolve them — all without you lifting a finger."

### 0:30-0:50 — Tech Stack (name every sponsor)
> "We pull financial data through Airbyte's agent connectors, ground our agent's knowledge with Senso's Context OS for verified compliance scripts, store everything in a Neo4j knowledge graph, research leverage with Tavily, and make outbound calls through Vapi — all deployed on Render with persistent background workers. Overshoot's vision AI even monitors live financial news for breaking rate changes."

### 0:50-2:15 — Live Demo
> "Here's our dashboard. Our Airbyte Stripe connector detected Neel's Comcast bill jumped from $55 to $85. Senso classified it as a BILLING_INCREASE and generated a negotiation script grounded in Comcast's actual retention policies. Watch what happens when I click 'Handle It'..."
>
> *Phone rings on speaker. Agent negotiates using Senso-grounded script. Neo4j graph grows. Transcript streams live.*
>
> "There — confirmation number captured, Neo4j updated, $20/month saved."

### 2:15-2:45 — Impact + Architecture
> "That's $240 a year from one call. And the architecture is dead simple — Vladimir, you'd approve: it's a loop, some tools, and a prompt. No frameworks. Just a FastAPI server, a monitoring worker, and a voice agent, all defined in a single render.yaml."

### 2:45-3:00 — Vision
> "Every American household could save $1,200 a year. LifePilot makes the calls you dread, grounded in verified knowledge, with full audit trails. The era of being put on hold is over."

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Render cold start (free tier) | Pre-warm with health ping 5 min before demo |
| Vapi call fails | Pre-recorded backup video queued on second device |
| Neo4j AuraDB down | Pre-seeded graph still renders; demo works with cached data |
| Senso API slow/down | Cache grounded scripts; fallback to raw LLM generation |
| Airbyte connector auth issues | Pre-cache Stripe data; show cached detection in dashboard |
| Overshoot rate limit | Pre-capture analysis results; show them as "detected 2 min ago" |
| Venue Wi-Fi | Mobile hotspot as primary; venue Wi-Fi as backup |
| Groq latency spike | Vapi handles gracefully; keep maxTokens at 300 |
| Demo runs over 3 min | Practice 5x; have a hard-stop at 2:45 for closing |
