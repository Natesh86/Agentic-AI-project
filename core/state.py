"""
SoloBiz AI - Core State Schemas (Pydantic V2)
Strict typed contracts matching solobiz_AGENTS.md I/O specification
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone


def current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Inbound Event Contracts ---

class CustomerRef(BaseModel):
    customer_id: str
    name: Optional[str] = None
    channel_user_id: str
    consent_status: Literal["EXPLICIT_OPT_IN", "IMPLICIT_CONVERSATIONAL", "REVOKED", "UNKNOWN"] = "IMPLICIT_CONVERSATIONAL"
    prior_order_count: int = 0


class MessagePayload(BaseModel):
    message_id: str
    message_text: str
    media_urls: List[str] = Field(default_factory=list)
    language_hint: Optional[str] = "en-IN"


class OrderRef(BaseModel):
    order_id: Optional[str] = None
    requested_items: List[Dict[str, Any]] = Field(default_factory=list)


class PhotoRef(BaseModel):
    asset_id: str
    asset_url: str
    uploader_type: Literal["OWNER", "CUSTOMER"] = "CUSTOMER"
    consent_verified: bool = False


class InboundMetadata(BaseModel):
    idempotency_key: str
    session_id: Optional[str] = None


class SoloBizInboundEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4()}")
    event_type: Literal[
        "CUSTOMER_ENQUIRY",
        "ORDER_CONFIRMATION",
        "LOW_STOCK_ALERT",
        "SUPPLIER_QUOTE_RECEIVED",
        "PRODUCTION_READY",
        "PHOTO_UPLOAD",
        "SCHEDULED_CAMPAIGN",
        "COMMENT_OR_REVIEW",
        "PAYMENT_STATUS_CHANGE",
        "DELIVERY_STATUS_CHANGE"
    ]
    channel: Literal["INSTAGRAM_DM", "WHATSAPP", "WEBSITE_CHAT", "OWNER_DASHBOARD", "EMAIL_INBOX"]
    business_id: str = "biz_artisan_candles_001"
    timestamp: str = Field(default_factory=current_iso_time)
    customer_ref: CustomerRef
    message_payload: MessagePayload
    order_ref: Optional[OrderRef] = None
    photo_ref: Optional[PhotoRef] = None
    metadata: InboundMetadata


# --- Outbound Workflow & Specialist Sub-States ---

class Classification(BaseModel):
    intent: str
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    confidence_score: float = 1.0


class AgentAction(BaseModel):
    agent: str
    action: str
    timestamp: str = Field(default_factory=current_iso_time)
    details: str


class CustomerReply(BaseModel):
    draft_text: str
    channel: str
    recipient_id: str
    dispatched: bool = False


class OrderItem(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_price: float


class OrderState(BaseModel):
    provisional_order_id: str
    items: List[OrderItem] = Field(default_factory=list)
    subtotal: float = 0.0
    shipping_fee: float = 0.0
    total_quote: float = 0.0
    payment_status: Literal["UNPAID", "VERIFICATION_PENDING", "CONFIRMED", "CANCELLED"] = "UNPAID"


class InventoryState(BaseModel):
    sku: str
    quantity_reserved: int = 0
    stock_health: Literal["HEALTHY", "LOW_STOCK", "OUT_OF_STOCK"] = "HEALTHY"
    reorder_needed: bool = False


class ProcurementRequest(BaseModel):
    request_id: str
    supplier_id: str
    items: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_cost: float = 0.0
    status: Literal["DRAFT_PO", "RFQ_SENT", "APPROVED", "REJECTED"] = "DRAFT_PO"


class FulfilmentState(BaseModel):
    courier_partner: str = "STANDARD_SURFACE"
    promised_delivery_date: Optional[str] = None
    fulfilment_status: str = "PENDING_ORDER_CONFIRMATION"


class MarketingState(BaseModel):
    draft_id: str
    platform: str = "INSTAGRAM"
    caption: str
    media_asset_id: Optional[str] = None
    scheduled_time: Optional[str] = None
    approved_by_owner: bool = False


class ReputationState(BaseModel):
    review_id: str
    sentiment_score: float  # 0.0 to 1.0
    response_draft: str
    escalated: bool = False


class FinancialImpact(BaseModel):
    estimated_revenue: float = 0.0
    estimated_cogs: float = 0.0
    estimated_shipping_cost: float = 0.0
    projected_gross_margin: float = 0.0


class ApprovalPayload(BaseModel):
    approval_id: str = Field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:8]}")
    trigger_type: str
    required_approver: str = "OWNER"
    summary: str
    actions_held: List[str] = Field(default_factory=list)
    expires_at: Optional[str] = None


class RiskFlag(BaseModel):
    code: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    description: str


class EvidenceRef(BaseModel):
    type: str
    id: str


class SoloBizWorkflowOutput(BaseModel):
    workflow_id: str = Field(default_factory=lambda: f"wf_{uuid.uuid4()}")
    event_id: str
    business_id: str
    classification: Classification
    status: Literal["COMPLETED", "PENDING_APPROVAL", "HANDOFF_TO_HUMAN", "FAILED_SAFE"]
    step_count: int = 1
    agent_actions: List[AgentAction] = Field(default_factory=list)
    customer_reply: Optional[CustomerReply] = None
    order_state: Optional[OrderState] = None
    inventory_state: Optional[InventoryState] = None
    procurement_request: Optional[ProcurementRequest] = None
    fulfilment_state: Optional[FulfilmentState] = None
    marketing_state: Optional[MarketingState] = None
    reputation_state: Optional[ReputationState] = None
    financial_impact: Optional[FinancialImpact] = None
    approval_required: bool = False
    approval_payload: Optional[ApprovalPayload] = None
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    audit_id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:10]}")
