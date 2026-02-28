Here's the full architecture top to bottom:

---

**LifePilot — System Architecture v2**

**Layer 1: Data Ingestion (the "eyes")**

Three input channels feed the threat detection system:

- **Airbyte Agent Connectors** (`airbyte-agent-stripe`, `airbyte-agent-slack`) — standalone pip packages that pull financial data directly. Stripe connector checks recent charges for billing anomalies (rate hikes, new fees, duplicate charges). Slack connector sends alerts back to the user. No Airbyte platform needed — just `pip install` and `connector.execute(entity, action, params)`.

- **Overshoot Vision AI** — points at live financial news broadcasts (CNBC, Bloomberg) via screen capture. The VLM reads visual financial data in real-time at sub-200ms latency, extracting structured rate changes and billing announcements *before* they hit text-based news feeds. Creative differentiator nobody else will build.

- **Tavily Search** — discovers relevant URLs and pulls clean content. Pre-call research finds competitor rates, cancellation policies, retention scripts. Mid-call search gives the agent real-time leverage during negotiations.

**Layer 2: Knowledge & Context (the "brain")**

Two complementary knowledge systems:

- **Neo4j AuraDB** — the knowledge graph of the user's entire financial life. Every entity the agent encounters becomes a visible node: You -> subscribes_to -> Comcast, Comcast -> charges -> $85/month, Call_001 -> resulted_in -> Rate_Reduction. Bi-temporal tracking records when facts were true AND when the agent learned them. Neovis.js renders force-directed graphs in the browser — judges watch the graph expand in real-time while hearing the agent talk.

- **Senso Context OS** — the verified knowledge layer. Compliance playbooks, resolution procedures, and negotiation scripts are ingested via `/content/raw`. When the agent needs to make a call, it queries Senso's `/search` for verified procedures and `/generate` for grounded call scripts. The `/triggers` endpoint classifies threats (BILLING_INCREASE, FRAUD_ALERT, SUBSCRIPTION_EXPIRING). This gives the agent citation-backed knowledge rather than pure LLM hallucination — responsible AI that impresses judges.

**Layer 3: Task Engine (the "coordinator")**

FastAPI backend on Render. Two components:

- **Web Service** — receives Vapi webhooks, handles tool calls, serves the dashboard API, streams SSE events. Endpoints: `/api/vapi/webhook`, `/api/vapi/tool-call`, `/api/tasks`, `/api/events`.

- **Background Worker** — persistent monitoring loop running on a Render Background Worker (no execution time limit, unlike Lambda/Vercel). Cycles through: check Airbyte sources for anomalies -> check Overshoot for broadcast alerts -> check Tavily for web mentions -> create tasks for detected threats -> optionally auto-trigger calls.

Both defined in a single `render.yaml` — infrastructure-as-code that impresses Render judges.

**Layer 4: Voice Agent (the "mouth")**

Vapi outbound call with optimized latency stack:
- Deepgram Nova-3 for ears (~90ms STT)
- Groq Llama 3.3 70B for thinking (~200ms inference)
- ElevenLabs Flash v2.5 for speaking (~75ms TTFB)
- Total: ~465ms end-to-end perceived response time

During the call, the agent makes tool calls back to the backend:
1. `search_task_context` — gets task objectives + Senso-grounded context
2. `tavily_search` — real-time web research for leverage
3. `extract_entities` — logs confirmation numbers, prices, names
4. `update_neo4j` — writes outcomes to knowledge graph
5. `end_task` — marks task complete

**Layer 5: Dashboard (the "face")**

React frontend with three panels:

- **Left**: Task queue. Detected threats from Airbyte/Overshoot/Tavily, pending calls, completed tasks with outcomes and savings counter.
- **Center**: Live call view. Real-time transcript via SSE, Senso-grounded context shown alongside, negotiation status indicators.
- **Right**: Neo4j graph via Neovis.js. Nodes and edges grow in real-time as the agent extracts entities. You literally watch the agent's brain building connections.

---

**Data flow for the demo moment:**

Airbyte Stripe connector detects Comcast bill increased $55 -> $85 -> Senso classifies as BILLING_INCREASE -> Task created with Senso-generated negotiation script grounded in Comcast retention policies -> Tavily researches competitor rates ($45/mo at T-Mobile) -> You click "Handle It" -> Vapi makes outbound call -> Phone rings on speaker in front of judges -> Agent uses grounded script to negotiate -> Entities extracted in real-time -> Graph grows on screen -> Agent secures discount -> Task marked complete -> Dashboard shows "$240/year saved"

---

**Sponsor integration map:**

- **Airbyte** -> Layer 1 (Stripe + Slack agent connectors for data ingestion)
- **Overshoot** -> Layer 1 (vision AI monitoring financial broadcasts)
- **Tavily** -> Layer 1 + Layer 3 (search + pre-call research)
- **Senso** -> Layer 2 (Context OS for verified knowledge + threat classification)
- **Neo4j** -> Layer 2 (knowledge graph + live visualization)
- **Vapi** -> Layer 4 (voice calling with 5 custom tools)
- **Render** -> All layers (web service + background worker + static site)

Seven sponsors, each one essential to the architecture, not just checked-as-a-box. Architecture presented as "a loop, some tools, and a prompt" — no frameworks — exactly what Vladimir wants to hear.
