# LifePilot Integration Battle Plan v2

## The Prize Surface

**64 participants, ~16 teams, 9 sponsor prize tracks. Target: win 3-4.**

| # | Sponsor | Prize | Integration | Effort | Status |
|---|---------|-------|-------------|--------|--------|
| 1 | **Yutori** | $1,500 gift card + $1k credits | Proactive web monitoring Scouts | Medium | Not started |
| 2 | **Fastino (GLiNER2)** | $1k/$500/$250 cash | Entity extraction from call transcripts | Medium | Not started |
| 3 | **Reka Vision** | $1k/$500/$250 cash + job interview | Bill image/document analysis | Low-Medium | Not started |
| 4 | **Modulate (Velma 2)** | $1k/$500/$250 cash | Voice emotion + PII + diarization | Medium | Not started |
| 5 | **Neo4j** | Credits + Bose earbuds | Knowledge graph | Low | **Started** |
| 6 | **Render** | $1k/$600/$400 credits | Deployment platform | Low | **Deployed** |
| 7 | **Tavily** | 10k/5k/3k credits | Web research | Low | **Integrated** |
| 8 | **Senso** | 3k/2k/1k credits | Compliance knowledge context | Medium | Not started |
| 9 | **Airbyte** | $1k/$500 credits | Data pipeline connectors | Medium | Not started |

---

## Architecture Overview (All 10 Sponsors)

```
LAYER 1: MONITORING (eyes)
├── Yutori Scouts       → proactive web browsing for price changes / policy threats
├── Tavily Search       → research provider policies & competitor rates [DONE]
├── Reka Vision         → analyze bill images/screenshots for hidden fees
├── Airbyte Connectors  → pull Stripe/Gmail/financial data into pipeline
└── Webhooks            → fire to task engine when threat detected

LAYER 2: KNOWLEDGE & CONTEXT (brain)
├── Neo4j               → knowledge graph of user's financial life [DONE]
├── Senso Context OS    → verified compliance scripts & consumer rights
├── Fastino GLiNER2     → entity extraction from documents & transcripts
└── Task Engine         → creates structured call tasks with full context

LAYER 3: VOICE AGENT (mouth)
├── Vapi                → outbound phone calls [DONE]
├── Deepgram            → speech-to-text (~90ms)
├── Groq Llama 3.3 70B → real-time reasoning (~200ms)
├── ElevenLabs          → text-to-speech (~75ms)
├── Fastino GLiNER2     → real-time entity extraction from transcript
└── Modulate Velma 2    → emotion detection + PII tagging + speaker diarization

LAYER 4: DASHBOARD (face)
├── React + Vite + Tailwind [DONE]
├── react-force-graph-2d → live knowledge graph [DONE]
├── SSE streaming       → real-time transcript + entity extraction [DONE]
├── Emotion indicators  → Modulate-powered per-utterance sentiment
└── Task queue          → detected threats, pending/completed calls [DONE]

DEPLOYMENT: Render (web service + background worker) [DONE]
```

---

## Integration #1: MODULATE (Velma 2.0)

**Prize: $1,000 / $500 / $250 cash | 2 of 5 judges are from Modulate**

### What It Does
Modulate's Velma 2 API provides:
- **Batch STT** with emotion detection, speaker diarization, accent detection, PII/PHI tagging
- **Streaming STT** via WebSocket with real-time emotion signals
- **Fast English STT** for high-throughput batch processing (Opus only)

### API Details

**Batch endpoint:**
```
POST https://modulate-developer-apis.com/api/velma-2-stt-batch
Headers: X-API-Key: <key>
Body: multipart/form-data
  - upload_file: audio file (AAC, AIFF, FLAC, MP3, MP4, MOV, OGG, Opus, WAV, WebM, max 100MB)
  - speaker_diarization: true (default)
  - emotion_signal: true
  - accent_signal: true
  - pii_phi_tagging: true
```

**Batch response:**
```json
{
  "text": "Full transcript...",
  "duration_ms": 45000,
  "utterances": [
    {
      "utterance_uuid": "...",
      "text": "I can offer you a promotional rate.",
      "start_ms": 12000,
      "duration_ms": 3000,
      "speaker": 2,
      "language": "en",
      "emotion": "Confident",
      "accent": "American"
    }
  ]
}
```

**Emotion values (26):** Neutral, Calm, Happy, Amused, Excited, Proud, Affectionate, Interested, Hopeful, Frustrated, Angry, Contemptuous, Concerned, Afraid, Sad, Ashamed, Bored, Tired, Surprised, Anxious, Stressed, Disgusted, Disappointed, Confused, Relieved, Confident

**Accent values (13):** American, British, Australian, Southern, Indian, Irish, Scottish, Eastern_European, African, Asian, Latin_American, Middle_Eastern, Unknown

**Streaming endpoint:**
```
wss://modulate-developer-apis.com/api/velma-2-stt-streaming
  ?api_key=<key>
  &speaker_diarization=true
  &emotion_signal=true
  &accent_signal=true
  &pii_phi_tagging=true
```

**Streaming protocol:**
1. Connect WebSocket with query params
2. Send raw audio as binary frames (Opus recommended, 8KB chunks)
3. Receive JSON `{"type": "utterance", "utterance": {...}}` messages
4. Send empty text frame `""` to signal end of audio
5. Receive `{"type": "done", "duration_ms": 45000}`
6. WS close codes: 4001 (invalid key), 4003 (model disabled), 4029 (rate limit)

### Integration Plan

**File: `backend/services/modulate_service.py`**

```python
"""
Modulate Velma 2 Integration
- Batch: Post-call analysis with emotion + PII + diarization
- Streaming: Real-time emotion signals during live calls (stretch goal)
"""
import logging
import json
from typing import Optional
import httpx
import aiohttp
import config

logger = logging.getLogger(__name__)

BATCH_URL = "https://modulate-developer-apis.com/api/velma-2-stt-batch"
STREAMING_URL = "wss://modulate-developer-apis.com/api/velma-2-stt-streaming"


async def analyze_call_batch(audio_data: bytes, filename: str = "call.mp3") -> dict:
    """Post-call batch analysis: emotion + PII + speaker diarization."""
    if not config.MODULATE_API_KEY:
        return {"status": "modulate_unavailable"}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                BATCH_URL,
                headers={"X-API-Key": config.MODULATE_API_KEY},
                files={"upload_file": (filename, audio_data, "application/octet-stream")},
                data={
                    "speaker_diarization": "true",
                    "emotion_signal": "true",
                    "accent_signal": "true",
                    "pii_phi_tagging": "true",
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Modulate batch analysis failed: %s", e)
        return {"error": str(e)}


async def analyze_call_from_url(recording_url: str) -> dict:
    """Download Vapi recording and analyze with Modulate."""
    if not config.MODULATE_API_KEY:
        return {"status": "modulate_unavailable"}

    try:
        # Download recording from Vapi
        async with httpx.AsyncClient(timeout=60.0) as client:
            audio_resp = await client.get(recording_url)
            audio_resp.raise_for_status()
            audio_data = audio_resp.content

        # Send to Modulate batch API
        return await analyze_call_batch(audio_data)
    except Exception as e:
        logger.error("Modulate URL analysis failed: %s", e)
        return {"error": str(e)}


def extract_emotion_timeline(modulate_result: dict) -> list[dict]:
    """Extract emotion timeline from Modulate batch result for dashboard."""
    utterances = modulate_result.get("utterances", [])
    timeline = []
    for u in utterances:
        timeline.append({
            "speaker": u.get("speaker"),
            "text": u.get("text", ""),
            "emotion": u.get("emotion"),
            "accent": u.get("accent"),
            "start_ms": u.get("start_ms", 0),
            "duration_ms": u.get("duration_ms", 0),
            "language": u.get("language", "en"),
        })
    return timeline


def detect_pii_in_transcript(modulate_result: dict) -> list[dict]:
    """Extract PII/PHI tags found in the transcript."""
    # PII tags are embedded in utterance text when pii_phi_tagging=true
    # Format TBD from actual API response — look for tagged patterns
    pii_items = []
    for u in modulate_result.get("utterances", []):
        text = u.get("text", "")
        # Modulate wraps PII in tags — detect them
        if "<PII" in text or "<PHI" in text:
            pii_items.append({
                "utterance_id": u.get("utterance_uuid"),
                "speaker": u.get("speaker"),
                "text": text,
                "start_ms": u.get("start_ms", 0),
            })
    return pii_items


def generate_call_safety_report(modulate_result: dict) -> dict:
    """Generate a Modulate-powered safety report for the call."""
    utterances = modulate_result.get("utterances", [])
    if not utterances:
        return {"status": "no_data"}

    emotions = [u.get("emotion") for u in utterances if u.get("emotion")]
    speakers = set(u.get("speaker") for u in utterances)

    # Separate agent (speaker 1) vs rep (speaker 2) emotions
    agent_emotions = [u["emotion"] for u in utterances if u.get("speaker") == 1 and u.get("emotion")]
    rep_emotions = [u["emotion"] for u in utterances if u.get("speaker") == 2 and u.get("emotion")]

    # Flag hostile rep behavior
    hostile_emotions = {"Frustrated", "Angry", "Contemptuous", "Disgusted", "Stressed"}
    deceptive_signals = {"Anxious", "Ashamed", "Concerned"}  # potential deception markers
    rep_hostile_count = sum(1 for e in rep_emotions if e in hostile_emotions)
    rep_deceptive_count = sum(1 for e in rep_emotions if e in deceptive_signals)

    pii_detected = detect_pii_in_transcript(modulate_result)

    return {
        "total_utterances": len(utterances),
        "speakers_detected": len(speakers),
        "duration_ms": modulate_result.get("duration_ms", 0),
        "agent_emotion_summary": _emotion_summary(agent_emotions),
        "rep_emotion_summary": _emotion_summary(rep_emotions),
        "rep_hostile_utterances": rep_hostile_count,
        "rep_deceptive_signals": rep_deceptive_count,
        "pii_detected": len(pii_detected),
        "pii_items": pii_detected[:5],  # Top 5 for dashboard
        "safety_score": _calculate_safety_score(rep_hostile_count, rep_deceptive_count, len(pii_detected), len(utterances)),
    }


def _emotion_summary(emotions: list[str]) -> dict:
    """Count emotion frequencies."""
    from collections import Counter
    counts = Counter(emotions)
    return dict(counts.most_common(5))


def _calculate_safety_score(hostile: int, deceptive: int, pii: int, total: int) -> float:
    """Calculate 0-100 safety score. Higher = safer call."""
    if total == 0:
        return 100.0
    penalty = (hostile * 10 + deceptive * 5 + pii * 15)
    score = max(0, 100 - penalty)
    return round(score, 1)
```

### Webhook Integration Point

In `backend/routers/vapi_webhook.py`, after end-of-call-report:

```python
# After call ends, if recording URL available, run Modulate analysis
recording_url = message.get("recordingUrl") or call_obj.get("recordingUrl")
if recording_url and config.MODULATE_API_KEY:
    modulate_result = await modulate_service.analyze_call_from_url(recording_url)
    if "error" not in modulate_result:
        # Extract emotion timeline + safety report
        emotion_timeline = modulate_service.extract_emotion_timeline(modulate_result)
        safety_report = modulate_service.generate_call_safety_report(modulate_result)

        # Push to SSE for dashboard
        await store.push_event(SSEEvent(
            type=SSEEventType.EMOTION,
            data={
                "call_id": call_id,
                "source": "modulate_velma2",
                "emotion_timeline": emotion_timeline,
                "safety_report": safety_report,
            },
        ))
```

### Dashboard Changes

In `LiveCall.jsx`, add emotion indicators per utterance:
- Color-coded emotion badges next to each transcript line
- When PII detected: flash a lock icon with "Sensitive data detected"
- Post-call: show safety report card (score, hostile count, emotion breakdown)

### New SSE Event Types

Add to `schemas.py`:
```python
class SSEEventType(str, Enum):
    ...
    MODULATE_ANALYSIS = "modulate_analysis"
    PII_DETECTED = "pii_detected"
```

### Config Addition

```python
# Modulate Velma 2
MODULATE_API_KEY = os.getenv("MODULATE_API_KEY", "")
```

### Judge Pitch
> "We flipped Modulate's paradigm. Instead of protecting gamers from toxic players, we protect consumers from toxic customer service. Our agent detects when a rep is emotionally manipulative, flags PII exposure in real-time, and uses speaker diarization to build a full negotiation analysis. Every call produces a Modulate-powered safety report."

---

## Integration #2: FASTINO (GLiNER2)

**Prize: $1,000 / $500 / $250 cash | Judged on F1 score + creative usage of Pioneer fine-tuning**

### What It Does
GLiNER2 is a 205M parameter model that runs entity extraction on CPU. Zero external LLM dependencies. Perfect for replacing our current LLM-based `extract_entities` tool call.

### API Details (from Context7)

```python
from gliner2 import GLiNER2

extractor = GLiNER2.from_pretrained("fastino/gliner2-base-v1")

# Basic extraction
result = extractor.extract_entities(
    "My Comcast bill went from $55 to $85, confirmation number XR-7742.",
    ["dollar_amount", "confirmation_number", "company", "percentage"]
)
# → {'entities': {'dollar_amount': ['$55', '$85'], 'confirmation_number': ['XR-7742'], 'company': ['Comcast']}}

# With descriptions for better accuracy
result = extractor.extract_entities(
    transcript_text,
    {
        "confirmation_number": "Reference numbers, confirmation codes, ticket IDs",
        "dollar_amount": "Monetary values including monthly rates, fees, charges",
        "date": "Dates, billing cycles, contract expiration dates",
        "account_number": "Customer account numbers, member IDs",
        "company_name": "Service providers, companies mentioned",
        "phone_number": "Phone numbers for callbacks or transfers",
        "contract_term": "Contract durations like '12 months', '2 year agreement'",
        "promotional_rate": "Special offers, promotional pricing, limited-time deals",
        "penalty_fee": "Early termination fees, cancellation fees, late fees",
    },
    include_confidence=True,
    include_spans=True,
)

# Structured JSON extraction (financial transactions)
result = extractor.extract_json(
    transcript_text,
    {
        "negotiation_result": [
            "company::str::Service provider name",
            "original_rate::str::Original monthly rate",
            "new_rate::str::Negotiated rate",
            "confirmation::str::Confirmation number",
            "effective_date::str::When the change takes effect",
            "duration::str::How long the rate is locked",
            "outcome::[success|partial|failed]::str",
        ]
    }
)

# Batch extraction for multiple transcript chunks
results = extractor.batch_extract_entities(
    transcript_chunks,
    ["confirmation_number", "dollar_amount", "date", "account_number"],
    batch_size=8
)
```

### Integration Plan

**File: `backend/services/fastino_service.py`**

```python
"""
Fastino GLiNER2 Integration
- Zero-shot entity extraction from call transcripts
- Structured JSON extraction for negotiation results
- Replaces LLM-based extract_entities tool with faster, specialized model
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy load — model is 205M params, loads in ~2s on CPU
_extractor = None

FINANCIAL_ENTITY_SCHEMA = {
    "confirmation_number": "Reference numbers, confirmation codes, ticket IDs, case numbers",
    "dollar_amount": "Monetary values: monthly rates, fees, charges, savings amounts",
    "date": "Dates: billing cycles, contract expiration, effective dates",
    "account_number": "Customer account numbers, member IDs, subscriber IDs",
    "company_name": "Service providers, ISPs, gyms, companies mentioned",
    "phone_number": "Phone numbers for callbacks, transfers, departments",
    "contract_term": "Contract durations like '12 months', '2 year agreement'",
    "promotional_rate": "Special offers, promotional pricing, limited-time deals",
    "penalty_fee": "Early termination fees, cancellation fees, late payment fees",
    "person_name": "Names of reps, managers, supervisors spoken to",
}


def get_extractor():
    """Lazy-load GLiNER2 model (loads once, reuses)."""
    global _extractor
    if _extractor is None:
        try:
            from gliner2 import GLiNER2
            _extractor = GLiNER2.from_pretrained("fastino/gliner2-base-v1")
            logger.info("GLiNER2 model loaded successfully")
        except ImportError:
            logger.warning("gliner2 not installed — Fastino features disabled")
            return None
        except Exception as e:
            logger.error("GLiNER2 load failed: %s", e)
            return None
    return _extractor


def extract_financial_entities(text: str, include_confidence: bool = True) -> dict:
    """Extract financial entities from transcript text using GLiNER2."""
    extractor = get_extractor()
    if not extractor:
        return {"entities": {}, "source": "fallback"}

    try:
        result = extractor.extract_entities(
            text,
            FINANCIAL_ENTITY_SCHEMA,
            include_confidence=include_confidence,
            include_spans=True,
        )
        return {**result, "source": "gliner2"}
    except Exception as e:
        logger.error("GLiNER2 extraction failed: %s", e)
        return {"entities": {}, "source": "error", "error": str(e)}


def extract_negotiation_result(transcript: str) -> dict:
    """Extract structured negotiation outcome from full transcript."""
    extractor = get_extractor()
    if not extractor:
        return {}

    try:
        result = extractor.extract_json(
            transcript,
            {
                "negotiation_result": [
                    "company::str::Service provider name",
                    "original_rate::str::Original monthly rate before negotiation",
                    "new_rate::str::New negotiated monthly rate",
                    "confirmation::str::Confirmation or reference number",
                    "effective_date::str::When the new rate takes effect",
                    "duration::str::How long the promotional rate lasts",
                    "outcome::[success|partial|failed]::str",
                ]
            }
        )
        return result.get("negotiation_result", [{}])[0] if result.get("negotiation_result") else {}
    except Exception as e:
        logger.error("GLiNER2 JSON extraction failed: %s", e)
        return {}


def batch_extract_from_chunks(chunks: list[str]) -> list[dict]:
    """Batch entity extraction across multiple transcript chunks."""
    extractor = get_extractor()
    if not extractor:
        return [{"entities": {}} for _ in chunks]

    try:
        return extractor.batch_extract_entities(
            chunks,
            FINANCIAL_ENTITY_SCHEMA,
            batch_size=8,
        )
    except Exception as e:
        logger.error("GLiNER2 batch extraction failed: %s", e)
        return [{"entities": {}} for _ in chunks]
```

### Existing Tool Replacement

In `backend/routers/vapi_tools.py`, modify `_handle_extract_entities`:

```python
async def _handle_extract_entities(args: dict, call_id: str) -> str:
    """Extract entities using Fastino GLiNER2 (replaces LLM-based extraction)."""
    text = args.get("text", "") or args.get("context", "")
    entity_type = args.get("entity_type", "other")
    value = args.get("value", "")

    # If Vapi already extracted a specific value, store it directly
    if value:
        neo4j_service.add_entity(entity_type, value, text, call_id)
        # ALSO run GLiNER2 to find additional entities the LLM might have missed
        gliner_result = fastino_service.extract_financial_entities(text)
        extra_entities = []
        for etype, values in gliner_result.get("entities", {}).items():
            for v in values:
                v_text = v["text"] if isinstance(v, dict) else v
                if v_text != value:  # Don't duplicate
                    neo4j_service.add_entity(etype, v_text, text, call_id)
                    extra_entities.append(f"{etype}:{v_text}")

        # Push to SSE
        await store.push_event(SSEEvent(
            type=SSEEventType.ENTITY_EXTRACTED,
            data={
                "entity_type": entity_type,
                "value": value,
                "additional_entities": extra_entities,
                "extraction_source": "gliner2",
                "call_id": call_id,
            },
        ))
        return f"Logged {entity_type}: {value}. GLiNER2 also found: {', '.join(extra_entities) or 'none'}"

    # Pure GLiNER2 extraction (no pre-identified value)
    gliner_result = fastino_service.extract_financial_entities(text)
    entities_found = []
    for etype, values in gliner_result.get("entities", {}).items():
        for v in values:
            v_text = v["text"] if isinstance(v, dict) else v
            neo4j_service.add_entity(etype, v_text, text, call_id)
            entities_found.append(f"{etype}:{v_text}")

    return f"GLiNER2 extracted: {', '.join(entities_found) or 'no entities found'}"
```

### Post-Call Structured Extraction

In the end-of-call webhook handler, add:
```python
# After call ends, run GLiNER2 structured extraction on full transcript
if transcript:
    negotiation = fastino_service.extract_negotiation_result(transcript)
    if negotiation:
        # Update task with GLiNER2-extracted structured data
        store.update_task(task.id,
            outcome=negotiation.get("outcome", ""),
            savings=float(negotiation.get("new_rate", "0").replace("$", "")) - float(negotiation.get("original_rate", "0").replace("$", "")),
            confirmation_number=negotiation.get("confirmation", ""),
        )
```

### Pioneer Fine-Tuning (Demo Day)

1. Create 10-20 labeled examples of financial call transcripts with entity annotations
2. Upload to Pioneer at `gliner.pioneer.ai`
3. Fine-tune on financial domain entities
4. Show F1 improvement (base vs fine-tuned) in presentation
5. This is SPECIFICALLY what the prize criteria calls for

### Requirements Addition
```
gliner2>=0.1.0
```

---

## Integration #3: REKA VISION

**Prize: $1,000 / $500 / $250 cash + job interview | "Most Innovative Use"**

### What It Does
Reka's Vision API analyzes images, videos, PDFs with multimodal AI. Supports `image_url`, `video_url`, `audio_url`, `pdf_url` content types.

### API Details (from Context7)

```python
from reka import ChatMessage
from reka.client import Reka

client = Reka(api_key="YOUR_API_KEY")

# Analyze a bill image
response = client.chat.create(
    messages=[
        ChatMessage(
            content=[
                {"type": "image_url", "image_url": "https://example.com/comcast-bill.png"},
                {"type": "text", "text": "Extract all financial data: total amount, line items, fees, surcharges, and any price increases. Return as JSON."}
            ],
            role="user",
        )
    ],
    model="reka-flash",  # or "reka-core" for higher quality
)
result = response.responses[0].message.content

# Multiple images (compare bills month-over-month)
response = client.chat.create(
    messages=[
        ChatMessage(
            content=[
                {"type": "image_url", "image_url": "https://example.com/bill-january.png"},
                {"type": "image_url", "image_url": "https://example.com/bill-february.png"},
                {"type": "text", "text": "Compare these two bills. Identify any price increases, new fees, or removed discounts."}
            ],
            role="user",
        )
    ],
    model="reka-core",
)

# Analyze PDF statements
response = client.chat.create(
    messages=[
        ChatMessage(
            content=[
                {"type": "pdf_url", "pdf_url": "https://example.com/annual-statement.pdf"},
                {"type": "text", "text": "Summarize all charges, identify rate changes over time, and flag any unexpected fees."}
            ],
            role="user",
        )
    ],
    model="reka-core",
)
```

### Integration Plan

**File: `backend/services/reka_service.py`**

```python
"""
Reka Vision Integration
- Analyze bill images for hidden fees, rate increases
- Compare bills month-over-month
- Extract structured financial data from document screenshots
- Feed extracted data into Neo4j knowledge graph
"""
import json
import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

_client = None


def get_client():
    global _client
    if _client is None and config.REKA_API_KEY:
        try:
            from reka.client import Reka
            _client = Reka(api_key=config.REKA_API_KEY)
            logger.info("Reka client initialized")
        except ImportError:
            logger.warning("reka not installed — Vision features disabled")
        except Exception as e:
            logger.error("Reka init failed: %s", e)
    return _client


async def analyze_bill_image(image_url: str) -> dict:
    """Analyze a bill image and extract structured financial data."""
    client = get_client()
    if not client:
        return {"status": "reka_unavailable"}

    try:
        from reka import ChatMessage
        response = client.chat.create(
            messages=[
                ChatMessage(
                    content=[
                        {"type": "image_url", "image_url": image_url},
                        {"type": "text", "text": (
                            "Analyze this bill/statement image. Extract and return as JSON:\n"
                            "1. provider_name: The service provider\n"
                            "2. total_amount: Total amount due\n"
                            "3. line_items: Array of {description, amount} for each charge\n"
                            "4. fees: Array of any surcharges, regulatory fees, taxes\n"
                            "5. previous_amount: Previous bill amount if visible\n"
                            "6. price_change: Amount of increase/decrease if detectable\n"
                            "7. promotional_expiry: Any promo expiration dates\n"
                            "8. hidden_fees: Any fees that seem unusual or recently added\n"
                            "Return ONLY valid JSON, no markdown."
                        )}
                    ],
                    role="user",
                )
            ],
            model="reka-flash",
        )
        content = response.responses[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_analysis": content}
    except Exception as e:
        logger.error("Reka bill analysis failed: %s", e)
        return {"error": str(e)}


async def compare_bills(image_url_old: str, image_url_new: str) -> dict:
    """Compare two bill images to detect price changes."""
    client = get_client()
    if not client:
        return {"status": "reka_unavailable"}

    try:
        from reka import ChatMessage
        response = client.chat.create(
            messages=[
                ChatMessage(
                    content=[
                        {"type": "image_url", "image_url": image_url_old},
                        {"type": "image_url", "image_url": image_url_new},
                        {"type": "text", "text": (
                            "Compare these two bills from the same provider. Return as JSON:\n"
                            "1. provider_name: The service provider\n"
                            "2. old_total: Previous bill total\n"
                            "3. new_total: New bill total\n"
                            "4. price_change: Dollar amount of change\n"
                            "5. change_percentage: Percentage change\n"
                            "6. new_fees: Any new fees or charges added\n"
                            "7. removed_discounts: Any discounts that expired\n"
                            "8. action_recommended: What the consumer should do\n"
                            "Return ONLY valid JSON."
                        )}
                    ],
                    role="user",
                )
            ],
            model="reka-core",
        )
        content = response.responses[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_analysis": content}
    except Exception as e:
        logger.error("Reka bill comparison failed: %s", e)
        return {"error": str(e)}


async def analyze_document(document_url: str, doc_type: str = "pdf") -> dict:
    """Analyze a financial document (PDF statement, contract, etc)."""
    client = get_client()
    if not client:
        return {"status": "reka_unavailable"}

    content_type = "pdf_url" if doc_type == "pdf" else "image_url"
    try:
        from reka import ChatMessage
        response = client.chat.create(
            messages=[
                ChatMessage(
                    content=[
                        {"type": content_type, content_type: document_url},
                        {"type": "text", "text": (
                            "Analyze this financial document. Extract all relevant data:\n"
                            "- Monthly charges and their breakdown\n"
                            "- Contract terms and expiration dates\n"
                            "- Early termination fees\n"
                            "- Promotional rates and when they expire\n"
                            "- Any clauses that favor the consumer for negotiation\n"
                            "Return as structured JSON."
                        )}
                    ],
                    role="user",
                )
            ],
            model="reka-flash",
        )
        content = response.responses[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_analysis": content}
    except Exception as e:
        logger.error("Reka document analysis failed: %s", e)
        return {"error": str(e)}
```

### New Router Endpoint

**In `backend/routers/monitoring.py` or new `backend/routers/bills.py`:**

```python
@router.post("/api/bills/analyze")
async def analyze_bill(image_url: str):
    """Analyze a bill image with Reka Vision and auto-create task if threat detected."""
    result = await reka_service.analyze_bill_image(image_url)

    # If price increase detected, auto-create a negotiation task
    price_change = result.get("price_change")
    if price_change and float(str(price_change).replace("$", "").replace("+", "")) > 0:
        task = store.create_task(TaskCreate(
            company=result.get("provider_name", "Unknown"),
            action=TaskAction.NEGOTIATE_RATE,
            phone_number="",  # User fills in
            current_rate=float(str(result.get("total_amount", "0")).replace("$", "")),
            notes=f"Reka Vision detected price increase: {price_change}",
        ))
        result["auto_task_created"] = task.id

    # Store bill data in Neo4j
    if result.get("provider_name"):
        neo4j_service.add_entity("bill_analysis", json.dumps(result), f"Reka Vision analysis of {image_url}")

    return result
```

### Config Addition
```python
REKA_API_KEY = os.getenv("REKA_API_KEY", "")
```

### Requirements Addition
```
reka>=0.1.0
```

### Judge Pitch
> "We gave our agent eyes. When a user uploads a bill screenshot, Reka Vision extracts every line item, identifies hidden fees, detects price increases, and auto-creates a negotiation task. The agent then calls the provider armed with exact dollar amounts from the bill itself."

---

## Integration #4: SENSO CONTEXT OS

**Prize: 3k / 2k / 1k credits | Grounded knowledge + responsible AI angle**

### What It Does
Already partially implemented in `backend/services/senso_service.py`. Needs activation with API key and enhanced usage.

### Current State
- `ingest_content()` — works, needs API key
- `search_knowledge()` — works, needs API key
- `generate_script()` — works, needs API key
- `classify_threat()` — works, needs API key
- `seed_compliance_docs()` — pre-loads 3 docs on startup

### Enhancement Plan

1. **Get API key at hackathon** from Senso team
2. **Add to `.env`**: `SENSO_API_KEY=...`
3. **Enhance seed docs** with more financial compliance knowledge:
   - FCC consumer rights for cable/internet
   - FTC subscription cancellation rules (Click-to-Cancel)
   - State-specific consumer protection laws
   - Credit card dispute procedures
4. **Wire threat classification** into monitoring pipeline:
   ```python
   # In monitoring.py scan endpoint
   threat_class = await senso_service.classify_threat(detection["description"])
   # Use classification to prioritize tasks
   ```
5. **Use generate_script before each call**:
   ```python
   # In tasks.py trigger endpoint, before calling Vapi
   script = await senso_service.generate_script(task.company, task.action.value, research_context)
   # Pass script as additional context to Vapi call
   ```

### No new files needed — just activate + enhance existing service.

---

## Integration #5: AIRBYTE (PyAirbyte)

**Prize: $1,000 / $500 credits**

### What It Does
PyAirbyte lets you use Airbyte source connectors as standalone Python packages. No Airbyte platform needed. We already have `airbyte_service.py` with raw Stripe/Slack HTTP calls — enhance with PyAirbyte for credibility.

### Current State
- `check_stripe_charges()` — raw httpx to Stripe API
- `detect_billing_anomalies()` — anomaly detection logic
- `send_slack_alert()` — raw httpx to Slack API

### Enhancement Plan

The existing raw HTTP approach works fine, but adding PyAirbyte wrapping shows proper Airbyte usage:

**File: `backend/services/airbyte_service.py` (enhance existing)**

Add a PyAirbyte-powered alternative path:

```python
# At the top of existing file, add:
try:
    import airbyte
    PYAIRBYTE_AVAILABLE = True
except ImportError:
    PYAIRBYTE_AVAILABLE = False

async def check_stripe_via_pyairbyte() -> list[dict]:
    """Pull Stripe data via official PyAirbyte connector."""
    if not PYAIRBYTE_AVAILABLE or not config.STRIPE_API_KEY:
        return await check_stripe_charges()  # fallback to raw HTTP

    try:
        source = airbyte.get_source(
            "source-stripe",
            config={
                "client_secret": config.STRIPE_API_KEY,
                "account_id": "",
                "start_date": "2024-01-01T00:00:00Z",
            },
            streams=["charges"],
        )
        read_result = source.read()
        charges = []
        for record in read_result["charges"].records:
            charges.append(dict(record))
        return charges
    except Exception as e:
        logger.warning("PyAirbyte Stripe failed, using raw HTTP: %s", e)
        return await check_stripe_charges()
```

### Requirements Addition
```
airbyte>=0.17.0  # PyAirbyte
```

### Config — Already has `STRIPE_API_KEY`

---

## Integration #6: YUTORI

**Prize: $1,500 gift card + $1k credits (HIGHEST CASH VALUE)**

### What It Does
Yutori builds "Scouts" — proactive agents that monitor the web. Dhruv Batra's vision: agents that browse and detect changes.

### Integration Plan

**This is event-dependent — get API access from Dhruv at the hackathon.**

**File: `backend/services/yutori_service.py` (placeholder)**

```python
"""
Yutori Scouts Integration
- Proactive web monitoring for price changes, policy updates
- Fires webhooks to task engine when threats detected
- If Yutori API not available, falls back to Tavily + custom scraping
"""
import logging
import config

logger = logging.getLogger(__name__)


async def create_scout(provider: str, monitor_type: str = "price_change") -> dict:
    """Create a Yutori Scout to monitor a provider's website."""
    if not config.YUTORI_API_KEY:
        logger.info("Yutori not configured — using Tavily fallback for monitoring")
        return await _fallback_monitor(provider, monitor_type)

    # TODO: Wire to Yutori API once credentials obtained at hackathon
    # Expected pattern:
    # POST /api/scouts
    # {
    #   "name": f"LifePilot-{provider}-monitor",
    #   "url": provider_url,
    #   "schedule": "daily",
    #   "detect": ["price_changes", "policy_updates", "new_fees"],
    #   "webhook": f"{config.SERVER_URL}/api/monitor/yutori-webhook"
    # }
    return {"status": "yutori_placeholder"}


async def _fallback_monitor(provider: str, monitor_type: str) -> dict:
    """Fallback: use Tavily search to simulate Scout behavior."""
    from services import tavily_service
    query = f"{provider} price increase 2025 rate change"
    result = tavily_service.search(query)
    return {"source": "tavily_fallback", "result": result}
```

### Config Addition
```python
YUTORI_API_KEY = os.getenv("YUTORI_API_KEY", "")
```

---

## Config Updates Summary

**`backend/config.py` — add these:**
```python
# Modulate Velma 2
MODULATE_API_KEY = os.getenv("MODULATE_API_KEY", "")

# Fastino GLiNER2 (no API key needed — runs locally)
# Just needs gliner2 pip package

# Reka Vision
REKA_API_KEY = os.getenv("REKA_API_KEY", "")

# Yutori Scouts
YUTORI_API_KEY = os.getenv("YUTORI_API_KEY", "")
```

**`backend/.env` — add:**
```
MODULATE_API_KEY=
REKA_API_KEY=
YUTORI_API_KEY=
```

## Requirements.txt Update

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
neo4j>=5.25.0
tavily-python>=0.5.0
httpx>=0.27.0
python-dotenv>=1.0.1
pydantic>=2.9.0
# New sponsor integrations
gliner2>=0.1.0
reka>=0.1.0
aiohttp>=3.9.0
```

Note: `airbyte` and `aiohttp` are optional — `aiohttp` needed for Modulate streaming WebSocket, `airbyte` for PyAirbyte connector wrapper.

---

## Schema Updates

**`backend/models/schemas.py` — additions:**

```python
class SSEEventType(str, Enum):
    TRANSCRIPT = "transcript"
    CALL_STATUS = "call_status"
    ENTITY_EXTRACTED = "entity_extracted"
    GRAPH_UPDATED = "graph_updated"
    TASK_UPDATED = "task_updated"
    EMOTION = "emotion"
    # New
    MODULATE_ANALYSIS = "modulate_analysis"
    PII_DETECTED = "pii_detected"
    BILL_ANALYZED = "bill_analyzed"

class EntityType(str, Enum):
    CONFIRMATION_NUMBER = "confirmation_number"
    PRICE = "price"
    DATE = "date"
    ACCOUNT_NUMBER = "account_number"
    PERSON_NAME = "person_name"
    PHONE_NUMBER = "phone_number"
    OTHER = "other"
    # New (from GLiNER2)
    COMPANY_NAME = "company_name"
    CONTRACT_TERM = "contract_term"
    PROMOTIONAL_RATE = "promotional_rate"
    PENALTY_FEE = "penalty_fee"
    DOLLAR_AMOUNT = "dollar_amount"
```

---

## main.py Updates

```python
# In lifespan startup, add:
from services import modulate_service, fastino_service, reka_service

# Pre-load GLiNER2 model on startup (takes ~2s)
fastino_service.get_extractor()

# In /api/status, add:
"modulate": "configured" if config.MODULATE_API_KEY else "not configured",
"reka": "configured" if config.REKA_API_KEY else "not configured",
"fastino_gliner2": "loaded" if fastino_service.get_extractor() else "not loaded",
"yutori": "configured" if config.YUTORI_API_KEY else "not configured",
```

---

## Dashboard Frontend Updates

### LiveCall.jsx — Emotion Indicators

Add to the `formatEvent` function:
```javascript
case "modulate_analysis":
  return {
    type: "modulate",
    timeline: d.emotion_timeline,
    safetyReport: d.safety_report,
  };

case "pii_detected":
  return {
    type: "pii_alert",
    icon: "lock",
    text: `PII detected: ${d.type}`,
    color: "text-accent-red"
  };
```

Add emotion badges to transcript lines:
```jsx
// Next to each transcript message, if emotion data available:
{item.emotion && (
  <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${emotionColor(item.emotion)}`}>
    {item.emotion}
  </span>
)}
```

### New: SafetyReport component
Post-call card showing:
- Safety score (0-100 with color gradient)
- Rep emotional breakdown (pie chart or bar)
- PII detections count with redaction status
- Speaker diarization summary

### New: BillAnalyzer component
- Upload button for bill images
- Reka Vision analysis results display
- Auto-task creation when price increase detected
- Before/after bill comparison view

---

## Sprint Schedule

### TODAY (Thursday) — Core New Services

**Priority 1: `services/modulate_service.py`** (2-3 hours)
- [ ] Create service file with batch analysis function
- [ ] Add recording URL download from Vapi webhook
- [ ] Wire into end-of-call webhook handler
- [ ] Add emotion timeline extraction
- [ ] Add safety report generation
- [ ] Add config + env vars
- [ ] Test with sample audio file

**Priority 2: `services/fastino_service.py`** (1-2 hours)
- [ ] Create service file with GLiNER2 entity extraction
- [ ] Wire into `_handle_extract_entities` in vapi_tools.py
- [ ] Add structured negotiation extraction for end-of-call
- [ ] Add to requirements.txt
- [ ] Test with sample transcript text

**Priority 3: `services/reka_service.py`** (1-2 hours)
- [ ] Create service file with bill analysis functions
- [ ] Add `/api/bills/analyze` endpoint
- [ ] Wire bill analysis results into Neo4j
- [ ] Auto-task creation on price increase detection
- [ ] Add config + env vars + requirements

### TOMORROW (Friday) — Wiring + Dashboard + Polish

**Priority 4: Dashboard emotion indicators** (2 hours)
- [ ] Add emotion badges to LiveCall transcript lines
- [ ] Add SafetyReport post-call card component
- [ ] Add PII detection alert in LiveCall
- [ ] Add BillAnalyzer upload component

**Priority 5: Activate existing services** (1 hour)
- [ ] Get Senso API key, test seed_compliance_docs
- [ ] Enhance Senso with more compliance docs
- [ ] Wire threat classification into monitoring scan
- [ ] Test end-to-end flow

**Priority 6: Event-day integrations** (at hackathon)
- [ ] Get Yutori API access from Dhruv, wire Scout integration
- [ ] Get Modulate API key from Carter, test batch analysis
- [ ] Fine-tune GLiNER2 via Pioneer (need 10-20 labeled examples)
- [ ] Test Airbyte PyAirbyte wrapper if time allows

**Priority 7: Demo preparation** (last 2 hours)
- [ ] Record 3-min demo video
- [ ] Update demo.py simulation to include Modulate + GLiNER2 events
- [ ] Ensure all sponsor logos/mentions in dashboard
- [ ] Push fresh GitHub repo
- [ ] Prepare judge-specific pitches for each sponsor track

---

## Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `backend/services/modulate_service.py` | Velma 2 batch + streaming analysis | P1 |
| `backend/services/fastino_service.py` | GLiNER2 entity extraction | P2 |
| `backend/services/reka_service.py` | Vision API bill analysis | P3 |
| `backend/services/yutori_service.py` | Scout monitoring (placeholder) | P6 |

## Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `backend/config.py` | Add MODULATE, REKA, YUTORI keys | P1 |
| `backend/.env` | Add new API keys | P1 |
| `backend/.env.example` | Add new key placeholders | P1 |
| `backend/requirements.txt` | Add gliner2, reka, aiohttp | P1 |
| `backend/main.py` | Import new services, update /api/status | P1 |
| `backend/routers/vapi_tools.py` | Wire GLiNER2 into extract_entities | P2 |
| `backend/routers/vapi_webhook.py` | Wire Modulate into end-of-call | P1 |
| `backend/models/schemas.py` | Add new SSE types + entity types | P1 |
| `backend/services/airbyte_service.py` | Add PyAirbyte wrapper | P5 |
| `backend/routers/monitoring.py` | Add /api/bills/analyze endpoint | P3 |
| `dashboard/src/components/LiveCall.jsx` | Add emotion badges + PII alerts | P4 |
| `dashboard/src/hooks/useSSE.js` | Handle new event types | P4 |
| `backend/routers/demo.py` | Add Modulate + GLiNER2 demo events | P7 |

---

## Key Risk Mitigations

1. **GLiNER2 model size on Render**: 205M params loads in ~2s on CPU, should be fine on Render's starter plan. If memory issues, lazy-load only when first extraction requested.

2. **Modulate API availability**: 1,000 free credits should be enough for demo. Use batch endpoint first (simpler), streaming only if time permits.

3. **Reka API key**: Need to get from sponsor. Have fallback to return `reka_unavailable` gracefully.

4. **Yutori API not available**: Fallback to Tavily-powered monitoring already implemented. Present as "designed for Yutori Scout integration" with working Tavily prototype.

5. **Demo reliability**: Keep demo.py simulation updated — if live APIs fail during demo, the simulation path still shows the full flow with realistic data.
