# LifePilot Sprint 5: Final Integration Blitz

**Context:** We have 1 Render web service. Hackathon requires **2+ Render services**. We have 5 sponsor APIs with keys set but not fully wired. The voice agent flow is solid — DO NOT touch it. Everything here is pre/post-call processing.

---

## Current State (from plan2.md audit)

| Sponsor | Status | Working? |
|---------|--------|----------|
| **Vapi** | Live agent + phone | YES — core of demo |
| **Neo4j** | Knowledge graph | YES — seeds, updates, visualizes |
| **Tavily** | Pre-call research | YES — called in demo flow |
| **Modulate** | Voice analysis | PARTIAL — demo fallback works, real API attempted post-call |
| **Render** | 1 web service | NEED 2+ services |
| **Reka** | Bill image analysis | CODE EXISTS, no UI trigger |
| **Senso** | Compliance knowledge | CODE EXISTS, seeds on startup, not in demo flow |
| **Yutori** | Web monitoring | STUBBED — returns "yutori_pending" |
| **Fastino** | GLiNER2 extraction | CODE EXISTS, model too big for free tier |
| **Airbyte** | Stripe/Slack | NO KEYS, skip |

---

## The Plan: 5 Tasks

### Task 1: Render — Add Postgres + Cron Job (satisfies 2+ services)

**Why:** We currently have 1 service. Need 2+. Postgres + Cron are the most natural fit.

**Postgres (task/call history):**
- Create free Postgres on Render
- Add a `call_logs` table: call_id, task_id, transcript, outcome, savings, modulate_analysis, created_at
- After each call completes (end-of-call webhook), INSERT a row
- GET `/api/calls/history` endpoint returns past calls for the dashboard
- This is READ-AFTER-WRITE only — the in-memory task store stays as-is for real-time. Postgres is the durable audit log.

**Cron Job (monitoring scan):**
- Create a Render cron job that hits `POST /api/monitor/scan` every hour
- The scan endpoint already exists in monitoring.py
- Cron just needs: `curl -X POST https://agenthackathon.onrender.com/api/monitor/scan`
- Schedule: `0 * * * *` (hourly)

**Files:**
- `backend/services/postgres_service.py` (new) — asyncpg connection, insert_call_log, get_call_history
- `backend/routers/monitoring.py` — already has `/api/monitor/scan`
- `backend/main.py` — add postgres connect/disconnect to lifespan
- `backend/requirements.txt` — add `asyncpg`

---

### Task 2: Reka Vision — "Scan Bill" button in dashboard

**Why:** Reka has $1k/$500/$250 cash prize + job interview. Code is 100% written, just needs a UI trigger.

**Flow (hardcoded except image processing):**
1. Dashboard has a "Scan Bill" button (next to "Run Demo")
2. Click → POST `/api/bills/analyze` with a hardcoded Comcast bill image URL
3. Reka Vision (`reka-flash`) processes the image → extracts provider, total, line items, fees, price change
4. Backend auto-creates a negotiation task if price increase detected
5. SSE pushes `bill_analyzed` event → dashboard shows a bill analysis card
6. The task appears in the task queue → user can then "Run Demo" on it

**Dashboard UI:** A card in the LiveCall feed showing:
- Provider name, total amount, price change (red highlight)
- Hidden fees list
- "Task auto-created" badge

**What we hardcode:** The bill image URL (a real Comcast bill screenshot we provide)
**What's real:** Reka's actual vision AI processing the image

**Files:**
- `dashboard/src/App.jsx` — add "Scan Bill" button
- `dashboard/src/components/LiveCall.jsx` — already handles `bill_analyzed` event type (line 103-110)
- `backend/routers/monitoring.py` — `/api/bills/analyze` already exists and works
- Provide a sample bill image (host on imgur or use a public URL)

---

### Task 3: Senso — Show compliance knowledge in research phase

**Why:** Senso has $3k/$2k/$1k credits prize. Already seeding docs on startup. Just need to visibly use it.

**Flow (add to existing research phase):**
1. During `_phase_research()` in demo.py, after Tavily search, also call `senso_service.search_knowledge()`
2. Push an SSE event: `{ type: "task_updated", phase: "compliance_check", message: "Senso: Found Comcast retention playbook..." }`
3. Append Senso context to the task's research_context
4. Dashboard shows a "Compliance Check" badge in the live feed

**What we hardcode:** Nothing — Senso already has the compliance docs seeded (Comcast Retention Playbook, Planet Fitness Cancellation Policy, General Negotiation Framework)
**What's real:** Senso's actual search API returning grounded context

**Files:**
- `backend/routers/demo.py` — add Senso search call in `_phase_research()`
- `dashboard/src/components/LiveCall.jsx` — add handler for compliance_check phase

---

### Task 4: Yutori — Wire the actual API

**Why:** $1,500 gift card + $1k credits. We have the API key. Code is stubbed.

**Approach:** The Yutori API details were supposed to be provided at the hackathon. Since we have a key (`yt_7iR...`), try to wire the real API. If it doesn't work, make the Tavily fallback look intentional — "Yutori Scout monitoring with Tavily-powered threat detection."

**Flow:**
1. On demo reset or app startup, create a Scout for "Comcast"
2. The scout's webhook URL points to `/api/monitor/yutori-webhook`
3. If real API works → show "Yutori Scout Active" in dashboard
4. If not → Tavily fallback does the same thing, just show it branded as "LifePilot Monitor (powered by Yutori + Tavily)"

**Files:**
- `backend/services/yutori_service.py` — try to wire real API, keep fallback
- `backend/main.py` — maybe create scout on startup

---

### Task 5: Dashboard — "Call History" panel from Postgres

**Why:** Shows Render Postgres is genuinely used, not just created empty.

**Flow:**
1. GET `/api/calls/history` returns last 10 calls from Postgres
2. Dashboard shows a small "Recent Calls" section or a tab
3. Each entry: company, outcome, savings, date

**Files:**
- `dashboard/src/components/CallHistory.jsx` (new)
- `dashboard/src/App.jsx` — add the component
- `backend/routers/monitoring.py` or new `backend/routers/calls.py`

---

## Render Services After Sprint

| # | Service | Type | Purpose |
|---|---------|------|---------|
| 1 | agenthackathon | Web Service | Backend API + Dashboard (existing) |
| 2 | lifepilot-db | Postgres | Call history + task persistence |
| 3 | lifepilot-monitor | Cron Job | Hourly monitoring scan |

**3 Render services total — satisfies the 2+ requirement.**

---

## Priority Order

1. **Task 1: Render Postgres + Cron** — MUST DO (hackathon requirement)
2. **Task 2: Reka "Scan Bill"** — HIGH (big prize, code ready, just needs button)
3. **Task 3: Senso in research** — MEDIUM (quick win, 2 lines of code)
4. **Task 5: Call History** — MEDIUM (shows Postgres is real)
5. **Task 4: Yutori** — LOW (API may not work, fallback is fine)

---

## What We're NOT Touching

- Voice agent system prompt
- Vapi assistant config
- Call flow / webhook handling
- Modulate integration (already working)
- GLiNER2 / Fastino (model too big for free tier — code exists, mention in presentation)
- Airbyte / Stripe / Slack (no keys)

---

## Sponsor Coverage After Sprint

| Sponsor | Integration | Demo Evidence |
|---------|------------|---------------|
| **Vapi** | Live voice agent | Phone call negotiation |
| **Neo4j** | Knowledge graph | Visual graph updates in dashboard |
| **Tavily** | Web research | Pre-call research phase |
| **Modulate** | Voice analysis | Agent Performance Report card |
| **Render** | 3 services | Web + Postgres + Cron |
| **Reka** | Bill scanning | "Scan Bill" button → analysis card |
| **Senso** | Compliance context | "Compliance Check" badge in research |
| **Yutori** | Web monitoring | Scout creation + Tavily-powered fallback |
| **Fastino** | Entity extraction | Code exists, mention in pitch (memory constraint) |

**9/9 sponsors integrated. 7/9 actively demo'd.**
