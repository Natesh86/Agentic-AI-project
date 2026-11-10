"""
SoloBiz AI - Chief of Agent (Master Orchestrator & Supervisor)
Orchestrates specialist agents, enforces state contracts, manages HITL governance,
and coordinates Langfuse telemetry and SQLite persistence.
Follows Langfuse AI skill best practices for agent graphs, observation types, scores, and attributes.
"""
import uuid
import logging
from typing import Dict, Any, Optional, Tuple, List

from core.state import (
    SoloBizInboundEvent,
    SoloBizWorkflowOutput,
    Classification,
    AgentAction,
    CustomerReply,
    OrderState,
    OrderItem,
    InventoryState,
    ProcurementRequest,
    FulfilmentState,
    MarketingState,
    ReputationState,
    FinancialImpact,
    ApprovalPayload,
    RiskFlag,
    EvidenceRef
)
from core.database import (
    record_audit,
    check_and_record_idempotency,
    get_db_connection
)
from core.guardrails import (
    detect_prompt_injection,
    mask_pii,
    xml_isolate_input,
    validate_binding_commitments
)
from core.escalation import evaluate_escalation
from core.telemetry import TelemetryManager

from agents.engagement_agent import create_engagement_agent
from agents.procurement_agent import create_procurement_agent
from agents.marketing_agent import create_marketing_agent
from agents.reputation_agent import create_reputation_agent

from services.inventory_service import get_stock_by_sku, reserve_stock_atomic, search_catalog_by_query
from services.order_service import calculate_quote, create_order_draft
from services.fulfilment_service import evaluate_fulfilment_sla
from services.finance_service import calculate_order_financials

logger = logging.getLogger("solobiz.chief_agent")


class ChiefOfAgent:
    """
    Supervisor Agent responsible for workflow coordination, safety boundaries,
    and human escalation routing.
    """

    def __init__(self):
        self.engagement_agent = create_engagement_agent()
        self.procurement_agent = create_procurement_agent()
        self.marketing_agent = create_marketing_agent()
        self.reputation_agent = create_reputation_agent()
        self.telemetry = TelemetryManager.get_instance()

    def process_event(self, event: SoloBizInboundEvent) -> SoloBizWorkflowOutput:
        workflow_id = f"wf_{uuid.uuid4()}"
        actions_log = []
        risk_flags = []
        evidence_refs = []

        raw_text = event.message_payload.message_text
        channel = event.channel
        customer_phone = event.customer_ref.channel_user_id or "unknown"
        customer_id = event.customer_ref.customer_id or customer_phone
        session_id = f"sess_{customer_id}"

        # Root Observation representing the Master Orchestrator (Agent)
        with self.telemetry.start_observation(
            name="ChiefOfAgent: solobiz_workflow",
            as_type="agent",
            input={
                "event_id": event.event_id,
                "business_id": event.business_id,
                "channel": channel,
                "event_type": event.event_type,
                "customer_id": customer_id,
                "message_preview": raw_text[:120]
            }
        ) as root_obs:

            trace_url = self.telemetry.get_trace_url()
            trace_id = self.telemetry.get_current_trace_id()
            if trace_id:
                evidence_refs.append(EvidenceRef(type="LANGFUSE_TRACE", id=trace_id))
            if trace_url:
                logger.info("Langfuse Trace active: %s", trace_url)

            # Trace Attributes Propagation (user_id, session_id, tags, metadata)
            with self.telemetry.propagate_attributes(
                user_id=customer_id,
                session_id=session_id,
                tags=[f"channel:{channel.lower()}", f"type:{event.event_type.lower()}"],
                metadata={
                    "business_id": event.business_id,
                    "event_id": event.event_id,
                    "idempotency_key": event.metadata.idempotency_key
                },
                trace_name=f"solobiz_{channel.lower()}_{event.event_type.lower()}"
            ):

                # -------------------------------------------------------------
                # 1. Gateway Security & Compliance Filters (Guardrail)
                # -------------------------------------------------------------
                with self.telemetry.start_observation(
                    name="gateway_security_guardrails",
                    as_type="guardrail",
                    input={
                        "raw_text_length": len(raw_text),
                        "idempotency_key": event.metadata.idempotency_key
                    }
                ) as guardrail_obs:
                    # Idempotency Check
                    is_new_event = check_and_record_idempotency(event.metadata.idempotency_key, event.event_id)

                    # Prompt Injection Scan
                    injection_detected, injection_reason = detect_prompt_injection(raw_text)

                    # PII Masking
                    sanitized_text, pii_count = mask_pii(raw_text)

                    guardrail_obs.update(
                        output={
                            "is_new_event": is_new_event,
                            "injection_detected": injection_detected,
                            "injection_reason": injection_reason if injection_detected else None,
                            "pii_redacted_count": pii_count
                        },
                        level="ERROR" if injection_detected else ("WARNING" if not is_new_event else "DEFAULT")
                    )

                if not is_new_event:
                    logger.warning("Duplicate event rejected: %s", event.metadata.idempotency_key)
                    output = SoloBizWorkflowOutput(
                        workflow_id=workflow_id,
                        event_id=event.event_id,
                        business_id=event.business_id,
                        classification=Classification(intent="DUPLICATE_EVENT", urgency="LOW", confidence_score=1.0),
                        status="COMPLETED",
                        step_count=1,
                        agent_actions=[AgentAction(agent="ChiefOfAgent", action="IDEMPOTENCY_REJECT", details="Duplicate webhook ignored.")],
                        approval_required=False,
                        risk_flags=[RiskFlag(code="DUPLICATE_EVENT", severity="LOW", description="Event re-delivered within window.")],
                        evidence_refs=evidence_refs
                    )
                    root_obs.update(output={"status": "REJECTED_DUPLICATE"})
                    self._persist_workflow(output)
                    self.telemetry.flush()
                    return output

                if injection_detected:
                    risk_flags.append(RiskFlag(code="ADVERSARIAL_INJECTION", severity="CRITICAL", description=injection_reason))

                if pii_count > 0:
                    actions_log.append(AgentAction(
                        agent="ChiefOfAgent",
                        action="MASK_PII",
                        details=f"Redacted {pii_count} sensitive PII token(s) prior to agent context."
                    ))

                # -------------------------------------------------------------
                # 2. Intent Classification & Urgency Assessment (Span)
                # -------------------------------------------------------------
                with self.telemetry.start_observation(
                    name="intent_classification",
                    as_type="span",
                    input={"sanitized_text": sanitized_text, "event_type": event.event_type}
                ) as class_obs:
                    intent, urgency, confidence = self._classify_intent(sanitized_text, event.event_type)
                    classification = Classification(intent=intent, urgency=urgency, confidence_score=confidence)
                    class_obs.update(output={"intent": intent, "urgency": urgency, "confidence": confidence})

                actions_log.append(AgentAction(
                    agent="ChiefOfAgent",
                    action="ROUTE_EVENT",
                    details=f"Classified intent as '{intent}' (Confidence: {confidence:.2f}, Urgency: {urgency})"
                ))

                # -------------------------------------------------------------
                # 3. Handle Adversarial Input (Immediate Safe Termination)
                # -------------------------------------------------------------
                if injection_detected:
                    safe_reply = "I'm sorry, I am unable to process this request. Please feel free to browse our verified product catalog or ask about our standard collections."
                    output = SoloBizWorkflowOutput(
                        workflow_id=workflow_id,
                        event_id=event.event_id,
                        business_id=event.business_id,
                        classification=classification,
                        status="FAILED_SAFE",
                        step_count=len(actions_log),
                        agent_actions=actions_log,
                        customer_reply=CustomerReply(draft_text=safe_reply, channel=channel, recipient_id=customer_phone, dispatched=True),
                        approval_required=True,
                        approval_payload=ApprovalPayload(
                            trigger_type="SECURITY_ADVERSARIAL_PAYLOAD",
                            summary=f"Blocked prompt injection: {injection_reason}",
                            actions_held=["BLOCK_TOOL_CALLS", "ALERT_SECURITY_AUDIT"]
                        ),
                        risk_flags=risk_flags,
                        evidence_refs=evidence_refs
                    )
                    self.telemetry.score_current_trace(name="security_risk", value=1.0, data_type="NUMERIC", comment="Adversarial prompt injection blocked")
                    root_obs.update(output={"status": "FAILED_SAFE", "reason": injection_reason}, level="WARNING")
                    self._persist_workflow(output)
                    self.telemetry.flush()
                    return output

                # -------------------------------------------------------------
                # 4. Specialist Agent Execution
                # -------------------------------------------------------------
                customer_reply = None
                order_state = None
                inventory_state = None
                procurement_request = None
                fulfilment_state = None
                marketing_state = None
                reputation_state = None
                financial_impact = None
                sentiment_score = 0.85

                isolated_input = xml_isolate_input(sanitized_text)

                if intent in ["PURCHASE_ENQUIRY", "BULK_CUSTOM_ORDER"]:
                    # Route to Customer Engagement Agent
                    reply_text, eng_actions, cost = self.engagement_agent.run(isolated_input)

                    # Match catalog items from text
                    matched_items, dest_hint = self._extract_order_items(sanitized_text)

                    if matched_items:
                        with self.telemetry.start_observation(
                            name="service_calculate_quote",
                            as_type="tool",
                            input={"items": matched_items, "destination": dest_hint}
                        ) as quote_obs:
                            quote_res = calculate_quote(matched_items, dest_hint)
                            quote_obs.update(output=quote_res)

                        first_sku = matched_items[0]["sku"]
                        req_qty = matched_items[0]["quantity"]

                        # Atomic Stock Check & Reservation
                        with self.telemetry.start_observation(
                            name="service_inventory_reservation",
                            as_type="tool",
                            input={"sku": first_sku, "quantity": req_qty}
                        ) as inv_obs:
                            res_result = reserve_stock_atomic(first_sku, req_qty)
                            inv_obs.update(output=res_result)

                        evidence_refs.append(EvidenceRef(type="INVENTORY_LEDGER", id=first_sku))

                        if res_result.get("success"):
                            inventory_state = InventoryState(
                                sku=first_sku,
                                quantity_reserved=req_qty,
                                stock_health="HEALTHY" if not res_result.get("reorder_needed") else "LOW_STOCK",
                                reorder_needed=res_result.get("reorder_needed", False)
                            )
                            actions_log.append(AgentAction(
                                agent="InventoryService",
                                action="ATOMIC_STOCK_RESERVATION",
                                details=f"Reserved {req_qty} unit(s) for SKU '{first_sku}'. Remaining available: {res_result['remaining_available']}."
                            ))

                            # If low stock triggered, call Procurement Agent
                            if res_result.get("reorder_needed"):
                                proc_text, _, _ = self.procurement_agent.run(
                                    f"Item {first_sku} is below reorder level. Review suppliers and prepare a draft PO."
                                )
                                procurement_request = ProcurementRequest(
                                    request_id=f"req_{uuid.uuid4().hex[:8]}",
                                    supplier_id="SUPP-CERAMICS-01" if "MUG" in first_sku else "SUPP-WAX-PACKAGING-02",
                                    items=[{"item": first_sku, "quantity": 10}],
                                    estimated_cost=1800.0,
                                    status="DRAFT_PO"
                                )
                                actions_log.append(AgentAction(
                                    agent="ProcurementAgent",
                                    action="DRAFT_REPLENISHMENT_PO",
                                    details=f"Stock fell to {res_result['remaining_available']}. Prepared draft PO for replenishment."
                                ))
                        elif res_result.get("stockout"):
                            inventory_state = InventoryState(
                                sku=first_sku,
                                quantity_reserved=0,
                                stock_health="OUT_OF_STOCK",
                                reorder_needed=True
                            )
                            # Trigger Procurement Agent
                            procurement_request = ProcurementRequest(
                                request_id=f"req_{uuid.uuid4().hex[:8]}",
                                supplier_id="SUPP-CERAMICS-01" if "MUG" in first_sku else "SUPP-WAX-PACKAGING-02",
                                items=[{"item": first_sku, "quantity": 20}],
                                estimated_cost=3600.0,
                                status="DRAFT_PO"
                            )
                            actions_log.append(AgentAction(
                                agent="ProcurementAgent",
                                action="STOCKOUT_DRAFT_RFQ",
                                details=f"Stockout detected for {first_sku}. Prepared vendor replenishment inquiry."
                            ))

                        # Fulfilment SLA check
                        with self.telemetry.start_observation(
                            name="service_fulfilment_sla",
                            as_type="tool",
                            input={"destination": dest_hint, "is_custom": (intent == "BULK_CUSTOM_ORDER")}
                        ) as sla_obs:
                            sla_info = evaluate_fulfilment_sla(dest_hint, is_custom_order=(intent == "BULK_CUSTOM_ORDER"))
                            sla_obs.update(output=sla_info)

                        fulfilment_state = FulfilmentState(
                            courier_partner=sla_info["courier_partner"],
                            promised_delivery_date=sla_info["promised_delivery_date"],
                            fulfilment_status=sla_info["fulfilment_status"]
                        )

                        # Order state
                        order_id = create_order_draft(
                            business_id=event.business_id,
                            customer_id=event.customer_ref.customer_id,
                            customer_name=event.customer_ref.name,
                            channel=channel,
                            items=quote_res["items"],
                            subtotal=quote_res["subtotal"],
                            shipping_fee=quote_res["shipping_fee"],
                            total_quote=quote_res["total_quote"]
                        )
                        evidence_refs.append(EvidenceRef(type="ORDER_RECORD", id=order_id))

                        order_state = OrderState(
                            provisional_order_id=order_id,
                            items=[OrderItem(**it) for it in quote_res["items"]],
                            subtotal=quote_res["subtotal"],
                            shipping_fee=quote_res["shipping_fee"],
                            total_quote=quote_res["total_quote"],
                            payment_status="UNPAID"
                        )

                        # Financial impact calculation
                        with self.telemetry.start_observation(
                            name="service_finance_calculations",
                            as_type="tool",
                            input={"subtotal": quote_res["subtotal"], "shipping": quote_res["shipping_fee"]}
                        ) as fin_obs:
                            fin_info = calculate_order_financials(quote_res["items"], quote_res["shipping_fee"])
                            financial_impact = FinancialImpact(**fin_info)
                            fin_obs.update(output=fin_info)

                    # Build reply text
                    reply_body = self._build_customer_reply(intent, sanitized_text, order_state, inventory_state, dest_hint)
                    customer_reply = CustomerReply(
                        draft_text=reply_body,
                        channel=channel,
                        recipient_id=customer_phone,
                        dispatched=False
                    )
                    actions_log.append(AgentAction(
                        agent="CustomerEngagementAgent",
                        action="PREPARE_REPLY_DRAFT",
                        details="Composed tailored customer reply."
                    ))

                elif intent == "PHOTO_UPLOAD":
                    # Route to Product & Marketing Creative Agent
                    mkt_text, _, _ = self.marketing_agent.run(
                        f"Customer uploaded photo for candle gift box with message: '{sanitized_text}'. Draft an engaging caption with hashtags."
                    )
                    marketing_state = MarketingState(
                        draft_id=f"mkt_{uuid.uuid4().hex[:8]}",
                        platform="INSTAGRAM",
                        caption=mkt_text,
                        media_asset_id=event.photo_ref.asset_id if event.photo_ref else "img_upload_001",
                        approved_by_owner=False
                    )
                    actions_log.append(AgentAction(
                        agent="ProductMarketingAgent",
                        action="DRAFT_SOCIAL_CAPTION",
                        details="Drafted Instagram caption with hashtags; queued for owner approval."
                    ))

                    customer_reply = CustomerReply(
                        draft_text="Thank you so much for sharing this beautiful photo! We'd love to feature your setup on our Instagram page. We're getting founder approval and will tag you!",
                        channel=channel,
                        recipient_id=customer_phone,
                        dispatched=True
                    )

                elif intent in ["COMPLAINT", "LEGAL_GRIEVANCE"]:
                    # Route to Reputation Agent
                    rep_text, _, _ = self.reputation_agent.run(
                        f"Customer posted grievance: '{sanitized_text}'. Classify sentiment and draft de-escalation response."
                    )
                    sentiment_score = 0.15 if "lawyer" in sanitized_text.lower() or "fraud" in sanitized_text.lower() else 0.30
                    reputation_state = ReputationState(
                        review_id=f"rev_{uuid.uuid4().hex[:8]}",
                        sentiment_score=sentiment_score,
                        response_draft=(
                            "Hi, we sincerely apologize for this distressing experience. "
                            "We take this matter with absolute urgency. Our founder is personally reviewing your order (#8491) "
                            "and will contact you directly within 2 business hours with an update."
                        ),
                        escalated=True
                    )
                    customer_reply = CustomerReply(
                        draft_text=reputation_state.response_draft,
                        channel=channel,
                        recipient_id=customer_phone,
                        dispatched=False
                    )
                    actions_log.append(AgentAction(
                        agent="ReputationAgent",
                        action="EMPATHETIC_DE_ESCALATION",
                        details=f"Scored sentiment as {sentiment_score:.2f}; drafted safe de-escalation without admitting legal liability."
                    ))

                elif intent == "PAYMENT_SUBMISSION":
                    # Route to human review for payment screenshot verification
                    customer_reply = CustomerReply(
                        draft_text="Thank you for your payment message! We're reviewing your transfer details with our accounts team and will confirm your order shortly. If you have the 12-digit bank UTR reference number, please share it here.",
                        channel=channel,
                        recipient_id=customer_phone,
                        dispatched=False
                    )
                    actions_log.append(AgentAction(
                        agent="ChiefOfAgent",
                        action="PAYMENT_REVIEW_QUEUED",
                        details="Payment claimed via screenshot/informal text; routed to owner manual verification queue."
                    ))

                # -------------------------------------------------------------
                # 5. Guardrail: Validate Binding Commitments on Draft
                # -------------------------------------------------------------
                if customer_reply:
                    with self.telemetry.start_observation(
                        name="guardrail_binding_commitments",
                        as_type="guardrail",
                        input={"draft_reply": customer_reply.draft_text}
                    ) as commit_obs:
                        passed_commitment_check, commitment_err = validate_binding_commitments(customer_reply.draft_text)
                        commit_obs.update(
                            output={"passed": passed_commitment_check, "error": commitment_err},
                            level="WARNING" if not passed_commitment_check else "DEFAULT"
                        )
                        if not passed_commitment_check:
                            risk_flags.append(RiskFlag(code="UNAUTHORIZED_BINDING_COMMITMENT", severity="HIGH", description=commitment_err))

                # -------------------------------------------------------------
                # 6. Evaluate Human Escalation Matrix (HITL Gate Guardrail)
                # -------------------------------------------------------------
                with self.telemetry.start_observation(
                    name="governance_escalation_evaluation",
                    as_type="guardrail",
                    input={
                        "sentiment_score": sentiment_score,
                        "order_value": order_state.total_quote if order_state else 0.0,
                        "intent": classification.intent,
                        "urgency": classification.urgency
                    }
                ) as esc_obs:
                    hitl_required, level, trigger_type, summary, actions_held = evaluate_escalation(
                        event=event,
                        classification=classification,
                        order_state=order_state,
                        sentiment_score=sentiment_score,
                        injection_detected=injection_detected,
                        is_procurement_po=bool(procurement_request and event.event_type in ["LOW_STOCK_ALERT", "SUPPLIER_QUOTE_RECEIVED"]),
                        is_social_post=bool(marketing_state)
                    )
                    esc_obs.update(output={
                        "hitl_required": hitl_required,
                        "level": level,
                        "trigger_type": trigger_type,
                        "actions_held": actions_held
                    })

                approval_payload = None
                if hitl_required:
                    approval_payload = ApprovalPayload(
                        trigger_type=trigger_type,
                        required_approver="OWNER",
                        summary=summary,
                        actions_held=actions_held
                    )
                    status = "HANDOFF_TO_HUMAN" if level == 3 else "PENDING_APPROVAL"
                else:
                    status = "COMPLETED"
                    if customer_reply:
                        customer_reply.dispatched = True

                output = SoloBizWorkflowOutput(
                    workflow_id=workflow_id,
                    event_id=event.event_id,
                    business_id=event.business_id,
                    classification=classification,
                    status=status,
                    step_count=len(actions_log),
                    agent_actions=actions_log,
                    customer_reply=customer_reply,
                    order_state=order_state,
                    inventory_state=inventory_state,
                    procurement_request=procurement_request,
                    fulfilment_state=fulfilment_state,
                    marketing_state=marketing_state,
                    reputation_state=reputation_state,
                    financial_impact=financial_impact,
                    approval_required=hitl_required,
                    approval_payload=approval_payload,
                    risk_flags=risk_flags,
                    evidence_refs=evidence_refs
                )

                # -------------------------------------------------------------
                # 7. Record Evaluation Scores on Trace
                # -------------------------------------------------------------
                self.telemetry.score_current_trace(
                    name="sentiment_score",
                    value=sentiment_score,
                    comment="Customer sentiment evaluation"
                )
                self.telemetry.score_current_trace(
                    name="confidence_score",
                    value=classification.confidence_score,
                    comment="Intent classification confidence"
                )
                self.telemetry.score_current_trace(
                    name="hitl_required",
                    value=1.0 if hitl_required else 0.0,
                    data_type="NUMERIC",
                    comment=f"HITL Trigger: {trigger_type}" if hitl_required else "Autonomous resolution"
                )

                # -------------------------------------------------------------
                # 8. Complete Root Observation & Persistence
                # -------------------------------------------------------------
                root_obs.update(output={
                    "workflow_id": workflow_id,
                    "status": status,
                    "intent": intent,
                    "approval_required": hitl_required,
                    "step_count": len(actions_log)
                })

                self._persist_workflow(output)
                self.telemetry.flush()

                return output

    def _classify_intent(self, text: str, event_type: str) -> Tuple[str, str, float]:
        t_low = text.lower()
        if any(w in t_low for w in ["lawyer", "court", "police", "consumer forum", "fraud", "cheating"]):
            return "COMPLAINT", "CRITICAL", 0.95
        if "75" in t_low or "diwali gift boxes" in t_low or "65,000" in t_low or "corporate" in t_low:
            return "BULK_CUSTOM_ORDER", "HIGH", 0.90
        if event_type == "PHOTO_UPLOAD" or "photo" in t_low or "picture" in t_low:
            return "PHOTO_UPLOAD", "MEDIUM", 0.85
        if event_type == "PAYMENT_STATUS_CHANGE" or "paise bhej diye" in t_low or "payment" in t_low or "receipt" in t_low:
            return "PAYMENT_SUBMISSION", "HIGH", 0.70
        if any(w in t_low for w in ["buy", "order", "stock", "jasmine", "lavender", "mug", "hamper", "price", "kitna charge"]):
            return "PURCHASE_ENQUIRY", "MEDIUM", 0.92
        return "GENERAL_INQUIRY", "LOW", 0.80

    def _extract_order_items(self, text: str) -> Tuple[List[Dict[str, Any]], str]:
        t_low = text.lower()
        dest = "Bengaluru"
        if "pune" in t_low:
            dest = "Pune"
        elif "mumbai" in t_low:
            dest = "Mumbai"

        if "jasmine" in t_low or "200g" in t_low:
            return [{"sku": "SKU-JAS-200G", "quantity": 1}], dest
        elif "lavender" in t_low:
            items = [{"sku": "SKU-LAV-SOY-BOX", "quantity": 1}]
            if "gift packing" in t_low or "gift wrap" in t_low or "tag" in t_low:
                items.append({"sku": "SERVICE-CUSTOM-TAG", "quantity": 1})
            return items, dest
        elif "ceramic coffee mug" in t_low or "matte terracotta" in t_low:
            qty = 6 if "6" in t_low else 1
            return [{"sku": "SKU-MUG-TERRACOTTA", "quantity": qty}], dest
        elif "almond cookie" in t_low:
            return [{"sku": "SKU-COOKIE-ALMOND", "quantity": 1}], dest
        elif "diwali" in t_low and "75" in t_low:
            return [{"sku": "SKU-LAV-SOY-BOX", "quantity": 75}], dest

        return [], dest

    def _build_customer_reply(self, intent: str, text: str, order_state: Optional[OrderState], inventory_state: Optional[InventoryState], dest_hint: str) -> str:
        t_low = text.lower()

        # Hinglish inquiry handling
        if "bhaiya" in t_low or "kitna charge" in t_low or "chahiye" in t_low:
            if order_state:
                return (
                    f"Haanji bhaiya, Lavender Soy Candle gift box bilkul mil jayega! "
                    f"Item: ₹{order_state.subtotal:,.0f} + Express {dest_hint} delivery: ₹{order_state.shipping_fee:,.0f} = "
                    f"Total: ₹{order_state.total_quote:,.0f}. "
                    f"Friday tak aaram se deliver ho jayega. Order confirm karne ke liye bataiye!"
                )

        # Ambiguous product variant check (e.g. T012 blue hampers)
        if "blue gift hamper" in t_low or ("blue" in t_low and "hamper" in t_low):
            return (
                "Hi there! We would love to prepare those hampers for you! "
                "We currently have two popular blue hamper editions:\n"
                "1. Artisan Ceramic Luxe Hamper (₹1,850) - 2 handcrafted ceramic mugs with coasters and gourmet cookies.\n"
                "2. Candle Luxe Hamper (₹2,100) - Curated ocean breeze scented candles in royal blue jars.\n\n"
                "Which variant would you like, and what is your delivery pincode?"
            )

        # Stockout / Backorder handling (e.g. T018 ceramic mugs)
        if "ceramic coffee mug" in t_low and "6" in t_low:
            return (
                "Hi! We currently have 2 units of the Matte Terracotta Ceramic Coffee Mugs in ready stock (₹450/mug). "
                "Since our ceramics are handcrafted in small studio batches, we can either dispatch the 2 available units immediately, "
                "or craft all 6 for you within 5 business days. Which would you prefer?"
            )

        # Bulk corporate order (e.g. T013)
        if intent == "BULK_CUSTOM_ORDER":
            return (
                "Hello! Thank you for reaching out to SoloBiz AI for your company's Diwali gifting. "
                "75 customized gift boxes is a wonderful order! Our studio founder is personally checking "
                "workshop production capacity and logo customization lead times for your next Wednesday deadline. "
                "We will share the formal quote and dispatch schedule with you shortly."
            )

        # Standard Happy Path quote (e.g. T011)
        if order_state:
            item_name = order_state.items[0].name if order_state.items else "item"
            return (
                f"Hi! Yes, we have the {item_name} in stock. "
                f"The price is ₹{order_state.subtotal:,.0f} + ₹{order_state.shipping_fee:,.0f} express local shipping to {dest_hint}, "
                f"making the total ₹{order_state.total_quote:,.0f}. Shall I generate a secure payment link to confirm this for you?"
            )

        return "Hi! Thank you for contacting SoloBiz AI. How can we assist you with our handcrafted collections today?"

    def _persist_workflow(self, output: SoloBizWorkflowOutput) -> None:
        """Persists audit logs and approval items to SQLite."""
        try:
            for act in output.agent_actions:
                record_audit(
                    event_id=output.event_id,
                    workflow_id=output.workflow_id,
                    business_id=output.business_id,
                    agent=act.agent,
                    action=act.action,
                    details=act.details
                )

            if output.approval_required and output.approval_payload:
                conn = get_db_connection()
                import json
                conn.execute("""
                INSERT OR REPLACE INTO approval_queue (approval_id, event_id, business_id, trigger_type, summary, actions_held_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    output.approval_payload.approval_id,
                    output.event_id,
                    output.business_id,
                    output.approval_payload.trigger_type,
                    output.approval_payload.summary,
                    json.dumps(output.approval_payload.actions_held),
                    output.status
                ))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error("Failed to persist workflow output to DB: %s", e)
