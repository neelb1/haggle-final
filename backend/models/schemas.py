from pydantic import BaseModel
from typing import Optional
from enum import Enum


# ── Task Models ──────────────────────────────────────────────

class TaskAction(str, Enum):
    CANCEL_SERVICE = "cancel_service"
    NEGOTIATE_RATE = "negotiate_rate"
    CONSULT_USER = "consult_user"
    UPDATE_STATUS = "update_status"
    ADD_QUOTE = "add_quote"
    ADD_CONTACT = "add_contact"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RESEARCHING = "researching"
    CALLING = "calling"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_FOLLOWUP = "needs_followup"


class TaskCreate(BaseModel):
    company: str
    action: TaskAction
    phone_number: str
    service_type: Optional[str] = None
    current_rate: Optional[float] = None
    target_rate: Optional[float] = None
    user_name: str = "Neel"
    notes: Optional[str] = None


class Task(BaseModel):
    id: str
    company: str
    action: TaskAction
    phone_number: str
    service_type: Optional[str] = None
    current_rate: Optional[float] = None
    target_rate: Optional[float] = None
    user_name: str = "Neel"
    notes: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    research_context: Optional[str] = None
    research_sources: list[str] = []
    call_id: Optional[str] = None
    outcome: Optional[str] = None
    savings: Optional[float] = None
    confirmation_number: Optional[str] = None


# ── Vapi Tool Call Models ────────────────────────────────────

class VapiToolCallFunction(BaseModel):
    name: str
    arguments: str  # JSON string


class VapiToolCall(BaseModel):
    id: str
    type: str = "function"
    function: VapiToolCallFunction


class VapiToolCallResult(BaseModel):
    toolCallId: str
    result: str  # Must be single-line string


# ── Entity Extraction ────────────────────────────────────────

class EntityType(str, Enum):
    CONFIRMATION_NUMBER = "confirmation_number"
    PRICE = "price"
    DATE = "date"
    ACCOUNT_NUMBER = "account_number"
    PERSON_NAME = "person_name"
    PHONE_NUMBER = "phone_number"
    OTHER = "other"
    # GLiNER2 financial entity types
    COMPANY_NAME = "company_name"
    CONTRACT_TERM = "contract_term"
    PROMOTIONAL_RATE = "promotional_rate"
    PENALTY_FEE = "penalty_fee"
    DOLLAR_AMOUNT = "dollar_amount"


class ExtractedEntity(BaseModel):
    entity_type: EntityType
    value: str
    context: str
    call_id: Optional[str] = None


# ── SSE Event Models ─────────────────────────────────────────

class SSEEventType(str, Enum):
    TRANSCRIPT = "transcript"
    CALL_STATUS = "call_status"
    ENTITY_EXTRACTED = "entity_extracted"
    GRAPH_UPDATED = "graph_updated"
    TASK_UPDATED = "task_updated"
    EMOTION = "emotion"
    CALL_SUMMARY = "call_summary"
    VOICE_ANALYSIS = "voice_analysis"
    TOOL_CALL = "tool_call"
    MODULATE_ANALYSIS = "modulate_analysis"
    PII_DETECTED = "pii_detected"
    BILL_ANALYZED = "bill_analyzed"


class SSEEvent(BaseModel):
    type: SSEEventType
    data: dict


# ── User Consult Models ──────────────────────────────────────

class ConfirmedAction(BaseModel):
    """An action confirmed by the user during a consult call."""
    service: str
    action: str          # "cancel_service" | "negotiate_rate"
    reason: str
    monthly_savings: float
    phone_number: str = "+18005551234"
