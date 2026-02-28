<p align="center">
  <img src="backend/static/logo.png" alt="Haggle Logo" width="120" />
</p>

<h1 align="center">Haggle</h1>
<p align="center"><strong>Your AI Bill Negotiator That Actually Picks Up the Phone</strong></p>

<p align="center">
  <a href="https://agenthackathon.onrender.com">Live Demo</a>
</p>

---

Haggle is an autonomous AI agent that monitors your bills, detects overcharges, and **makes real phone calls** to negotiate lower rates on your behalf. No hold music. No awkward haggling. Just savings.

## How It Works

```
Detect → Research → Call → Verify → Record
```

1. **Detect** -- Scans billing data (Stripe via Airbyte), uploaded bills (Reka Vision), and the web (Yutori + Tavily) for price hikes, hidden fees, and competitor offers
2. **Research** -- Pulls competitor pricing, retention playbooks, and compliance context to build a negotiation strategy
3. **Call** -- Places a real outbound voice call via Vapi to the provider's retention department. The agent cites research, negotiates a lower rate, and extracts a confirmation number
4. **Verify** -- Post-call analysis with Modulate Velma 2 (emotion/safety scoring) and Fastino GLiNER2 (entity extraction)
5. **Record** -- Stores results in Neo4j (knowledge graph) and Postgres (audit log), then emails you a summary with the new rate and confirmation number

Everything streams to a real-time dashboard via SSE -- live transcript, AI reasoning chain, knowledge graph updates, and voice analysis.

## Architecture

```
                         ┌─────────────┐
                         │  React SPA  │  ← SSE stream
                         └──────┬──────┘
                                │
                         ┌──────┴──────┐
                         │   FastAPI   │
                         │  (Render)   │
                         └──┬───┬───┬──┘
                            │   │   │
              ┌─────────────┤   │   ├─────────────┐
              │             │   │   │             │
        ┌─────┴─────┐ ┌────┴───┴┐ ┌┴──────┐ ┌────┴────┐
        │   Vapi    │ │ Neo4j   │ │Postgres│ │ Tavily  │
        │  (Voice)  │ │ AuraDB  │ │(Render)│ │ Search  │
        └───────────┘ └─────────┘ └────────┘ └─────────┘
```

**Voice Pipeline** (sub-500ms latency):
- Deepgram Nova-3 (STT ~90ms)
- Groq Llama 3.3 70B (LLM ~200ms)
- ElevenLabs Flash v2.5 (TTS ~75ms)

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python, FastAPI, asyncpg, httpx, Pydantic v2 |
| Frontend | React 18, Vite, Tailwind CSS |
| Voice | Vapi, Deepgram, Groq, ElevenLabs |
| Databases | Neo4j AuraDB, Render Postgres |
| Integrations | Airbyte, Reka Vision, Tavily, Senso, Modulate, Fastino, Yutori, Overshoot |
| Deployment | Render |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
cp .env.example .env        # fill in your API keys
pip install -r requirements.txt
uvicorn main:app --reload
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

The dashboard connects to the backend at `http://localhost:8000` by default.

## Project Structure

```
backend/
  main.py              # FastAPI app + SSE event bus
  config.py            # Environment config
  routers/             # API routes (tasks, vapi webhook, demo, monitoring)
  services/            # Integration clients (vapi, neo4j, tavily, reka, etc.)
  worker/              # Background monitoring
  static/              # Built dashboard + assets
dashboard/
  src/
    components/        # React UI panels
    hooks/             # SSE hook
    App.jsx            # Main layout
```

## Sponsor Integrations

| Sponsor | Usage |
|---------|-------|
| **Vapi** | Outbound voice calls + tool-call orchestration |
| **Tavily** | Web search for competitor pricing |
| **Neo4j** | Knowledge graph of subscription relationships |
| **Render** | Deployment (web service + Postgres) |
| **Airbyte** | Stripe billing data ingestion |
| **Reka** | Vision AI for bill image analysis |
| **Senso** | Compliance context + retention playbooks |
| **Modulate** | Voice emotion detection + call safety scoring |
| **Fastino** | GLiNER2 entity extraction (confirmation numbers, amounts) |
| **Yutori + Overshoot** | Web monitoring + financial news scanning |

## License

MIT
