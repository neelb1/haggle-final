# Haggle — Your AI Bill Negotiator That Actually Picks Up the Phone

## Inspiration

We've all been there: staring at a cable bill that silently crept up $30/month, knowing we *could* call and negotiate it down, but dreading the 45-minute hold time and awkward haggling. Americans overpay an estimated **$50 billion per year** on subscriptions and services they could renegotiate — but the friction of actually making those calls stops most people from ever trying.

We asked ourselves: **what if an AI agent could do the entire thing for you?** Not just find the savings — actually pick up the phone, talk to the retention department, cite competitor rates, and hang up with a confirmation number and a lower bill.

That's Haggle.

## What it does

Haggle is an autonomous AI agent that monitors your financial life, detects billing threats, and **makes real phone calls** to negotiate rates or cancel services on your behalf.

Here's the full pipeline:

1. **Detect** — Scans your billing data (Stripe via Airbyte), uploaded bills (Reka Vision), and the web (Yutori Scouts + Tavily) for price hikes, hidden fees, and better competitor offers
2. **Research** — Pulls competitor pricing, retention playbooks, and compliance context (Tavily + Senso) to build a negotiation strategy
3. **Call** — Places a real outbound voice call via Vapi to the service provider's retention department. The agent introduces itself, cites research, negotiates a lower rate, and extracts a confirmation number — all in natural conversation
4. **Verify** — Post-call analysis with Modulate Velma 2 (emotion detection, PII scanning, call safety scoring) and Fastino GLiNER2 (entity extraction of confirmation numbers, dollar amounts, contract terms)
5. **Record** — Stores results in Neo4j (knowledge graph of your subscription history) and Render Postgres (durable call audit log). Sends you an email summary with the new rate, savings, and confirmation number

The entire flow runs through a real-time dashboard that shows the live call transcript, AI reasoning chain, knowledge graph updates, voice analysis, and integration status — all streamed via Server-Sent Events.

## How we built it

### Architecture

Haggle is a full-stack application with five distinct layers:

**Data Ingestion Layer** — Multiple input sources feed billing threats into the system: Airbyte connector monitors Stripe for rate hikes and duplicate charges, Reka Vision analyzes uploaded bill images for hidden fees and price changes, Overshoot Vision AI watches financial news broadcasts, and Yutori Scouts + Tavily perform proactive web monitoring for competitor rates.

**Knowledge & Context Layer** — Neo4j AuraDB maintains a live knowledge graph of the user's subscription relationships (`Person → SUBSCRIBES_TO → Service → NEGOTIATED`). Senso Context OS stores verified compliance playbooks and retention strategies that ground the agent's responses in real policy.

**Task Engine** — A FastAPI backend on Render coordinates everything: webhook handling, tool-call routing, SSE event streaming, and task lifecycle management. Tasks flow through states: `pending → researching → calling → completed`. An asyncio event bus pushes 12 distinct event types to the dashboard in real-time.

**Voice Agent** — Vapi powers the outbound phone calls with a carefully tuned stack: Deepgram Nova-3 for speech-to-text (~90ms), Groq Llama 3.3 70B for reasoning (~200ms), and ElevenLabs Turbo v2.5 for text-to-speech (~75ms). The agent has 5 custom tool functions it can invoke mid-call: `search_task_context`, `tavily_search`, `extract_entities`, `update_neo4j`, and `end_task`.

**Dashboard** — A React + Vite + Tailwind SPA with a 3-column layout, tabbed panels, and zero-polling architecture. Every UI update is pushed from the backend via SSE. The dashboard includes a live transcript feed with chat bubbles, AI reasoning chain timeline, knowledge graph visualization, Modulate voice analysis display, call history from Postgres, and an integration status panel.

### Tech Stack

- **Backend:** Python, FastAPI, asyncpg, httpx, Pydantic v2
- **Frontend:** React 18, Vite, Tailwind CSS, custom SVG graph rendering
- **Databases:** Neo4j AuraDB (knowledge graph), Render Postgres (call audit log)
- **Voice:** Vapi (orchestration), Deepgram Nova-3 (STT), Groq Llama 3.3 70B (LLM), ElevenLabs Flash v2.5 (TTS)
- **Deployment:** Render (Web Service + Postgres)
- **~8,500 lines of code** across 43 source files

## Challenges we ran into

**Voice agent turn-taking** — The biggest challenge was making the agent sound natural in a phone conversation. Early versions constantly interrupted the other speaker or cut off mid-sentence. We spent significant time tuning Vapi's `startSpeakingPlan` and `stopSpeakingPlan` parameters — adjusting wait times, punctuation detection, word count thresholds, and backoff intervals until the conversation flowed naturally.

**Pronunciation issues** — The TTS engine kept pronouncing "AT&T" as "at and t" or even "inches." We had to experiment with phonetic spellings in the system prompt ("A T and T", "T Mobile", "five G") to get brand names right without breaking the natural tone of the conversation.

**Transcript streaming** — Our first implementation used Vapi's `conversation-update` events for the live transcript, which only sent complete turns. This meant the dashboard would show nothing until a full sentence was finished. We switched to `transcript` events filtered by `transcriptType: "final"` to get real-time sentence-by-sentence streaming without partial-word noise.

**Memory constraints on Render free tier** — Fastino's GLiNER2 model (205M parameters) requires PyTorch, which pulls ~2GB of dependencies — far exceeding the 512MB RAM limit on Render's free tier. We wrote the full integration and extraction pipeline but had to disable the pip install in production. The code exists and works locally; it just can't run on the free tier.

**Render billing for additional services** — We planned to deploy Render Postgres and a Cron Job for scheduled monitoring scans, but hit a billing wall during the hackathon. The Postgres service code is fully written and wired into the application (connection pool, table creation, insert/query functions), ready to activate when a paid tier is available.

## Accomplishments that we're proud of

- **It actually calls and negotiates.** This isn't a chatbot demo — Haggle places real phone calls and has real conversations with service providers. During our demo, it successfully negotiated a Comcast bill from $85/mo down to $65/mo and obtained a confirmation number.

- **10 sponsor integrations.** The hackathon required 3. We integrated all 10 available sponsors, with 7 actively demonstrated in the live demo flow.

- **Sub-500ms voice latency.** By combining Deepgram Nova-3, Groq (for fast LLM inference), and ElevenLabs Flash, we achieved a voice pipeline where the agent responds in under half a second — fast enough that the conversation feels natural.

- **Real-time everything.** The dashboard updates in real-time as the call happens — transcript bubbles appear as sentences are spoken, entity extraction chips pop up when the agent detects a confirmation number, the knowledge graph animates new connections, and the Modulate voice analysis panel lights up with emotion data post-call. All push-based via SSE, zero polling.

- **Zero agent framework.** We didn't use LangChain, CrewAI, or any agent framework. The entire system is pure FastAPI + asyncio — "a loop, some tools, and a prompt." This gave us full control over the call flow and let us optimize for voice-specific challenges that generic frameworks don't handle well.

## What we learned

- **Voice AI is a different beast than chat AI.** Turn-taking, pronunciation, latency, and conversational flow matter enormously in voice. A 2-second delay that's invisible in a chatbot feels like an eternity on a phone call. We learned to think in milliseconds, not tokens.

- **The "last mile" of integrations is brutal.** Having 10 API keys is easy. Making 10 APIs work together in a coherent pipeline — where Tavily research feeds into Vapi's system prompt, which triggers Neo4j updates, which stream to the dashboard via SSE — requires careful orchestration and a lot of error handling.

- **Demo-ability drives design.** Building for a live demo taught us to think about the user experience of *watching* an AI work. The AI reasoning chain, live transcript, and integration status panel weren't just features — they were the story of the demo.

## What's next for Haggle

- **Production Postgres** — Activate the Render Postgres service for persistent call history and bill scan storage across sessions
- **Cron-based monitoring** — Deploy the scheduled scan job to continuously watch for billing anomalies without user intervention
- **Multi-provider expansion** — Extend beyond Comcast to handle any service provider (insurance, utilities, gym memberships, streaming services)
- **User authentication** — Add login so multiple users can each have their own subscription graph and call history
- **Mobile app** — Push notifications when a price hike is detected, one-tap approval to let Haggle make the call
- **Savings leaderboard** — Community feature showing aggregate savings across all Haggle users

## Built With

- airbyte
- asyncpg
- deepgram
- elevenlabs
- fastapi
- fastino-gliner2
- groq
- modulate-velma2
- neo4j
- overshoot
- python
- react
- reka-vision
- render
- senso
- server-sent-events
- tailwindcss
- tavily
- vapi
- vite
- yutori

## Try it out

- [Live Demo](https://agenthackathon.onrender.com)
- [GitHub Repository](https://github.com/neelb1/agenthackathon)
