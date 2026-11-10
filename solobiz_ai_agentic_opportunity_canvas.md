# SoloBiz AI – Multi-Agent Business Operations Platform
**Opportunity Canvas for SoloBiz AI**  
**Prepared by:** Shobana and Guru Natesh - North Star AI

---

## Canvas Overview Matrix

| A · WHY: the opportunity | B · WHAT: the agent | C · HOW SAFE: trust | D · HOW WE KNOW: proof and cost |
| :--- | :--- | :--- | :--- |
| **1. Agent name, owner, posture:** SoloBiz AI; product owner and small-business operator; a supervised multi-agent business assistant that automates daily operations while keeping critical decisions with the owner | **7. Triggers and channels:** Customer enquiries, new orders, low-stock alerts, order completion, photo uploads, social media comments and reviews; Instagram, WhatsApp and website integrations | **12. Human-in-the-loop:** Mandatory approval for supplier purchases, refunds, exceptional orders, paid campaigns and social media publishing; conditional approval for discounts and custom commitments | **14. Evaluation and quality bar:** ≥95% enquiry response accuracy, ≥98% order accuracy, ≥95% inventory accuracy, ≥90% successful agent handoffs, zero unauthorized purchases or publications |
| **2. Users and context:** Solo entrepreneurs, home-based sellers, Instagram businesses and small teams; personalize by product catalog, stock, suppliers, customer preferences, operating capacity and business rules | **8. Inputs, knowledge and data:** Customer messages, product catalog, pricing, inventory, orders, supplier details, product photos, social media comments, reviews, payment status and business policies | **13. Risks and guardrails:** Incorrect orders, overselling, unauthorized procurement, misleading promotions, privacy breaches and inappropriate customer responses; validate data, enforce approval and maintain audit trails | **15. Cost and feasibility:** Illustrative target ₹1,000–₹3,000 monthly AI inference cost per small business at modest usage, excluding channel/API, messaging, hosting and integration fees; validate during pilot |
| **3. Problem, reframed:** Small-business owners manually manage customer conversations, orders, stock, suppliers, marketing and reviews across disconnected tools, causing delays, missed sales and operational overload | **9. Tools and actions:** Read/respond to enquiries, check and reserve stock, create orders, prepare supplier purchase requests, coordinate fulfilment, draft social posts and manage routine reviews; protected actions require approval | | **16. Rollout and kill criteria:** Pilot with 10 small businesses for 6 weeks; start with enquiry-to-order automation, inventory alerts and marketing drafts; roll back for unauthorized purchases, incorrect financial commitments, critical privacy incidents or repeated order errors |
| **4. Job to be done:** Help small-business owners manage the complete customer-to-fulfilment lifecycle through coordinated AI agents, reducing manual work without losing business control | **10. Decision loop and architecture:** Receive → Understand → Delegate → Respond → Check stock → Accept order → Replenish if needed → Fulfil → Create content → Approve → Publish → Engage → Learn; Master Orchestrator coordinates specialist agents | | |
| **5. Outcomes, value and non-goals:** Target ≥50% reduction in routine administrative effort, faster customer responses, fewer missed enquiries and improved order conversion; no unauthorized payments, supplier purchases, refunds or social posts | **11. Outputs and I/O contract:** Structured customer enquiry, order details, stock status, procurement request, fulfilment status, marketing draft, review response, approval flags, action history and audit record | | |
| **6. Why agentic?:** Multiple specialized agents must coordinate dependent tasks, share business context, react to events, use external tools and adapt decisions; a traditional chatbot cannot manage the complete business workflow | | | |

---

## A · WHY: the opportunity

### 1. Agent name, owner and posture
* **Agent name:** SoloBiz AI – Multi-Agent Business Operations Platform
* **Business owner (accountable for outcomes):** Participating small-business owner (accountable for customer promises, pricing, purchasing and published content); SoloBiz venture lead for platform outcomes
* **Product owner (owns the spec and the quality bar):** SoloBiz Product Manager – owns specification, evaluation quality bar, agent permissions, rollout and rollback
* **Posture, in one line:** A supervised virtual operations team, not an autonomous business owner. Agents handle routine work, coordinate handoffs and prepare consequential actions for explicit approval.

### 2. Users and context
* **Primary user (who the agent serves):** Solo entrepreneurs, Instagram-first sellers, home businesses, makers and micro-retailers handling customer messages and orders with little or no staff
* **Secondary users (who works alongside it, receives handoffs, or is affected):** Customers, suppliers, delivery partners, occasional staff, accountant/bookkeeper and platform administrator
* **Context signals (what's true about their situation when the agent shows up):** Messages arrive outside business hours; products may be made-to-order; stock and production capacity fluctuate; finished-product photos drive social demand; owners switch between chat, sheets and social apps
* **Key reality (the one fact about these users that the design must respect):** The same person sells, produces, purchases, delivers and markets. Automation must reduce context switching without making commitments the owner cannot fulfil.

### 3. The problem, reframed
* **Surface framing:** “I need an Instagram chatbot and a tool to schedule posts.”
* **Actual problem:** Customer conversations, stock availability, order promises, supplier replenishment, fulfilment, marketing and reviews are disconnected. A new order does not reliably trigger the next operational step.
* **Today's process:** Owner reads each DM, answers FAQs, checks spreadsheet or memory for stock, negotiates order, manually messages supplier, tracks preparation, takes photos, writes posts and replies to comments. Actual time and volume must be measured in discovery.
* **What breaks today:** Slow replies, missed enquiries, overselling, late procurement, incomplete order details, inconsistent posting, unattended complaints and owner burnout. Frequency and loss estimates are unvalidated.

### 4. Job to be done
As a small-business owner managing sales and operations alone, I need customer enquiries to trigger a coordinated, accurate order-to-fulfilment workflow so that I can grow sales without manually coordinating every task or losing control of high-stakes decisions.

**The agent’s job, in one sentence:**  
> “Given a customer enquiry or business event, SoloBiz AI coordinates specialist agents to respond, validate stock, prepare and fulfil orders, replenish supplies, create marketing content and manage feedback—without spending money, making exceptional promises or publishing publicly without required approval.”

### 5. Outcomes, value and non-goals
| Metric | Baseline today | Target | Measured how |
| :--- | :--- | :--- | :--- |
| **Primary: manual handling time per completed order** | Measure in pilot week 0 | $\ge 50\%$ reduction | Owner time logs; median minutes/order |
| **First enquiry response time** | Measure in pilot week 0 | $\le 5$ minutes for eligible automated replies | Message timestamps; p50/p90 |
| **Inventory availability accuracy** | Measure in pilot week 0 | $\ge 95\%$ | Physical count vs system; stockout errors |
| **Order detail accuracy** | Measure in pilot week 0 | $\ge 98\%$ | Audited order records vs customer confirmation |
| **Successful workflow handoffs** | Measure in pilot week 0 | $\ge 90\%$ | Event trace with completed next-step |
| **Owner satisfaction** | Measure in pilot week 0 | $\ge 4.2/5$ | Weekly owner pulse survey |

* **Explicit non-goals:** Unsupervised supplier payments, automated refunds, unverified financial commitments, unvetted custom commitments, autonomous social media publishing without approval, legal or safety dispute resolution.

### 6. Why agentic? (and why not)
| Needs | Status | Evidence |
| :--- | :--- | :--- |
| **Multi-step reasoning:** the path depends on what it finds | $\checkmark$ | An enquiry may need catalog lookup, stock reservation, customisation questions, production scheduling and procurement |
| **Tool use:** it must read or change real systems | $\checkmark$ | Read/write order and stock records; messaging, supplier and publishing integrations |
| **Persistent context:** memory across steps, sessions or days | $\checkmark$ | Customer preferences, order history, inventory, approval state and pending supplier replies persist for days |
| **Variable inputs:** unstructured, messy, multilingual | $\checkmark$ | Informal DMs, voice-to-text, mixed languages, photos, incomplete order details and comments |
| **Volume:** enough repetitions to justify the build | $\checkmark$ (Validate) | Repetitive daily enquiries, order updates and review replies; pilot will quantify |
| **Bounded autonomy:** it can act alone within a playbook | $\checkmark$ | Routine responses and drafts autonomous; money, public posts and exceptions gated |

* **Why not a simpler solution?** A chatbot can answer FAQs but cannot consistently coordinate inventory reservation, procurement, fulfilment and marketing. Fixed automation alone struggles with unstructured customer intent and changing conditions. Deterministic services should still own stock arithmetic, payments, state transitions and approval enforcement.
* **Where autonomy must stop:** Supplier commitments/purchases, payments, refunds, discounts outside policy, acceptance of high-risk/custom orders, new delivery promises, customer-identifiable marketing content, social publication, legal/safety complaints and changes to approval rules.

---

## B · WHAT: the agent

### 7. Triggers and channels
* **Triggers:** New DM/WhatsApp/web enquiry; customer confirms order; stock falls below threshold; supplier quote arrives; production marked ready; product photo uploaded; scheduled campaign; new comment/review; payment or delivery status change.
* **Channels:** Instagram business messaging where permitted; WhatsApp Business Platform; website chat; owner dashboard; email to suppliers; social publishing through eligible official APIs.
* **Channel constraints:** Channel API permissions, conversation windows and rate limits vary; customer consent and platform policies apply; short mobile-first responses; multilingual support is phased; failed integrations require manual handoff.

### 8. Inputs, knowledge and data
| Source | What the agent uses it for | Owner | Freshness | Sensitivity (PII / regulated?) |
| :--- | :--- | :--- | :--- | :--- |
| **Customer enquiries and comments** | Intent, details, reply and sentiment | Business/channel | Real time | PII and potentially sensitive free text |
| **Catalog, pricing and policy** | Quotes, FAQs, product eligibility | Business owner | On change | Internal/commercial |
| **Stock, BOM and capacity** | Availability, reservations, material needs | Business owner | Event-driven | Internal/commercial |
| **Orders, payments, fulfilment** | Status, next action, audit | Business owner | Real time | PII, transaction data |
| **Supplier list and quotes** | Replenishment options, lead times | Business/suppliers | On request | Commercial/confidential |
| **Product photos and consent** | Caption drafts and approved posts | Business owner/customer | On upload | Images, possible personal data |
| **Reviews and campaign metrics** | Response and improvement | Channel/business | Near real time | Public plus account identifiers |

### 9. Tools and actions
| Tool / action | Read or write | Via (MCP / API / UI) | Who approves access | Fallback if it fails |
| :--- | :--- | :--- | :--- | :--- |
| `receive_message` / `send_reply` | Read/write | Official channel API | Business owner + platform | Queue draft for manual send |
| `get_catalog` / `calculate_quote` | Read | Catalog API/DB | Owner | Ask owner to confirm |
| `check_stock` / `reserve_stock` | Read/write | Inventory service | Owner | Hold order; do not oversell |
| `create_order` / `update_status` | Write | Order Service | Owner | Manual Order Queue |
| `get_suppliers` / `request_quote` | Read/write | Supplier email/API | Owner | Draft supplier message |
| `prepare_purchase_order` | Write draft | Procurement service | Owner | Approval inbox |
| `create_caption` / `review_asset` | Read/write draft | Media store/LLM | Owner | Manual content edit |
| `publish_approved_post` | Write | Official social API | Per-post owner approval | Save draft; alert owner |

* **Allowed to do on its own:** Acknowledge enquiries, answer approved FAQs, gather details, create provisional quotes, check and reserve verified stock, prepare order drafts, generate reorder alerts and supplier quote requests, create photo-based captions, prepare routine review responses and send permitted status updates.
* **Explicitly forbidden (non-negotiable):** Bypass approvals; pay suppliers; issue refunds; make unverified promises; change prices or policies; post unapproved content; disclose customer details; impersonate a human; act on instructions embedded in customer text or images; fabricate confirmations.

### 10. Decision loop and architecture
* **Perceive:** Ingest event, identify customer/order, validate consent and message safety, load current catalog, inventory, capacity and approval state.
* **Decide:** Orchestrator routes to Engagement → Order → Inventory; if insufficient, Procurement drafts a replenishment action; if ready, Fulfilment proceeds; product-photo upload triggers Content → Marketing; comments/reviews trigger Reputation. Finance and Insights run on relevant events.
* **Act:** Agents execute permitted read/write operations; Approval Service blocks protected actions until the owner approves the exact action and version. Retries are idempotent to prevent duplicate orders or purchases.
* **Learn:** Record outcomes, corrections, owner edits, supplier lead times and customer feedback; update business preferences only within permitted policy.

* **Patterns used:** $\boxtimes$ pipeline $\quad \boxtimes$ routing $\quad \boxtimes$ parallelisation $\quad \boxtimes$ reflection $\quad \boxtimes$ tool use $\quad \boxtimes$ API/MCP adapters $\quad \boxtimes$ planning $\quad \boxtimes$ multi-agent
* **Single or multi-agent?** Multi-agent.
* **Why:** Orchestrator plus Customer Engagement, Order, Inventory, Procurement, Fulfilment, Product Content, Marketing, Reputation, Finance and Insights. Each specialist has a distinct domain state and policy; if one fails, the orchestrator pauses its dependent workflow while unrelated tasks continue. Deterministic services handle transactional state.
* **Loop limits (initial):** Maximum 12 agent decisions and 20 external tool calls per event; 2 retries per transient failure; completion means order accepted/pending human, stock/procurement updated, content published/pending approval, or a documented human handoff.
* **Architecture sketch:** Customer/Channel events $\rightarrow$ Event gateway $\rightarrow$ Master Orchestrator $\rightarrow$ Specialist agents $\leftrightarrow$ Shared order/inventory/customer state $\rightarrow$ Policy & Approval Service $\rightarrow$ External messaging, supplier and social APIs $\rightarrow$ Audit/monitoring. Event triggers allow parallel procurement, fulfilment and review monitoring where independent.

### 11. Outputs and the I/O contract
* **Input schema:**  
  `{event_id, event_type, channel, customer_ref, message_text, product_ref?, quantity?, photo_ref?, business_id, timestamp, consent_status}`
* **Output schema:**  
  `{workflow_id, classification, agent_actions[], order_id?, order_status, inventory_status, procurement_request_id?, fulfilment_status?, content_draft_id?, publish_status?, customer_reply?, approval_required, approval_id?, risk_flags[], evidence_refs[], audit_id}`
* **Governance fields:** `event_id`, action permissions, `approval_required`, `approval_id`, `consent_status`, `risk_flags`, `evidence_refs` and `audit_id` are mandatory. Do not store unrestricted internal chain-of-thought; log concise action rationales and evidence.

---

## C · HOW SAFE: trust

### 12. Human-in-the-loop design
* **Pattern:** Auto-execute low-risk actions; pre-action review for purchases, refunds, exceptional orders and every public post in MVP; exception review for uncertain cases; retrospective QA sample of automated replies.
* **Triggers that bring in a human:** Supplier PO/payment, refund, high-value or customised order, capacity conflict, policy-exceeding discount, unusual delivery promise, customer photo usage, marketing publication, paid ad spend, serious negative review, low confidence or missing consent.
* **What the human sees:** Proposed action, agent, customer/order context, stock and capacity evidence, supplier price/quantity, financial impact, proposed caption/photo preview, policy flags, alternatives, Approve/Edit/Reject controls.
* **Human SLA, and what happens if it's missed:** Configurable pilot targets: urgent customer exceptions 2 hours; procurement 4 business hours; marketing before planned posting time. If missed, keep action pending, send truthful holding message where appropriate and notify owner.
* **How human decisions feed back into the agent:** Record decision, approver, timestamp, action/version, reason and outcome; feed owner edits into evaluation cases; materially changed actions require new approval.

### 13. Risks, failure modes and guardrails
| Risk / failure | Likelihood | Impact | Guardrail / fallback |
| :--- | :--- | :--- | :--- |
| **Overselling or duplicate orders** | Medium | High | Atomic stock reservation, idempotency keys, order-state validation |
| **Unapproved purchase or payment** | Medium | High | Central approval service, least-privilege tokens, deny-by-default |
| **Wrong customer promise or quote** | Medium | High | Catalog-backed pricing, capacity checks, approval on exceptions |
| **Unauthorized social post / photo use** | Medium | High | Per-asset consent, post preview and version-bound approval |
| **Incorrect review response** | Medium | Medium/High | Approved templates; sensitive reviews escalated |
| **PII exposure or prompt injection** | Medium | High | Redaction, access control, untrusted-input isolation, output scanning |
| **Supplier API/channel outage** | Medium | Medium | Retry queue, status visibility and manual handoff |
| **Agent loops / runaway costs** | Medium | Medium | Call budgets, circuit breakers and workflow timeouts |

---

## D · HOW WE KNOW: proof and cost

### 14. Evaluation and quality bar
| Quality criterion | Pilot threshold | Why |
| :--- | :--- | :--- |
| **Customer response factual accuracy** | $\ge 95\%$ | Wrong price/product replies harm trust |
| **Order field accuracy** | $\ge 98\%$ | Incorrect customisation/quantity causes rework |
| **Inventory state accuracy** | $\ge 95\%$ | Stock errors lead to cancellations; aim higher as integration matures |
| **Required approval enforcement** | $100\%$ | Any bypass is unacceptable |
| **Unauthorized purchases / posts / refunds** | $0$ | Financial and reputational exposure |
| **Correct cross-agent handoffs** | $\ge 90\%$ | Workflow must progress beyond isolated chat replies |
| **Sensitive complaint escalation recall** | $\ge 95\%$ | Missing a serious issue is worse than extra review |
| **Owner-rated usefulness** | $\ge 4.2/5$ | Owner must trust the system to continue |

* **Golden dataset:** Start with 150 synthetic/consented cases labeled by pilot owners and PM: standard enquiries, out-of-stock, custom orders, mixed-language DMs, duplicate events, supplier delays, photo consent, negative reviews, prompt injection; grow to 500+.
* **LLM-as-judge criteria:** Intent correctness, grounded answer, business-policy adherence, appropriate escalation, caption accuracy and tone; compare judge to human labels; deterministic assertions for stock and approval.
* **Eval cadence:** Every prompt/tool/model change; full regression before release; weekly review of sampled conversations and agent traces; daily safety monitoring.
* **Production monitoring and alerts:** Order mismatch, stock reservation failures, approval bypass, duplicate PO, publishing errors, response latency, human override rate, cost per completed workflow; immediate stop on protected-action violation.

### 15. Cost and feasibility
* **Volume:** Pilot assumption per business: 30 enquiries/day, 10 order workflows/day, 2 content drafts/day, 10 review/comment events/day; overlaps expected; validate by instrumenting channels.
* **Tokens per run:** Illustrative: 1,500–4,000 tokens per simple enquiry; 6,000–12,000 for multi-agent order/procurement workflow, depending on tool results and context.
* **Model per step:** Low-cost fast model for intent/FAQ and captions; stronger reasoning model for ambiguous custom orders and planning; deterministic services for stock, payment and approval; no model required for routine status transitions.
* **Monthly cost:** Working budget hypothesis: ₹1,000–₹3,000 AI inference per business/month at modest usage, including ~3× contingency for retries/QA; excludes WhatsApp/Meta messaging, API charges, hosting, storage, human review and integration fees. Reprice against actual model rates and traces.
* **Cost today without the agent:** Unknown; measure owner minutes per order, enquiry, post and review; value saved time using owner-supplied hourly opportunity cost, plus lost-enquiry estimates.
* **Feasibility:** Prototype feasible with synthetic catalog/orders, dashboard, simulated supplier email and draft-only publishing. Production risks: official channel permissions, accurate inventory synchronization, supplier connectivity, reliable transaction/approval semantics.

### 16. Rollout, kill criteria and open questions
* **Pilot scope:** 10 small businesses over 6 weeks; start with one supported messaging channel, catalog/stock, enquiry-to-order, procurement draft + owner approval, photo-to-caption + approval, review triage; simulate purchases and publishing until integration is verified.
* **Scale-up criteria:** For 2 consecutive weeks: $\ge 95\%$ factual reply accuracy, $\ge 98\%$ order accuracy, $\ge 90\%$ handoff completion, $\ge 4.2/5$ owner usefulness, no unauthorized protected actions; owner time saved demonstrated.
* **Kill / rollback criteria:** Any unauthorized purchase, refund or social publication; critical privacy incident; repeated overselling; material misinformation or unsafe complaint handling. Disable affected write integrations and revert to owner-operated queue.
* **Biggest assumption to test first:** Owners will trust an agent to move an enquiry into a correctly validated order, and will find approvals less burdensome than manually doing the entire workflow.
* **Open questions:** Which channel first? How do owners currently record stock and BOM? Which suppliers support digital quotes? How are payment confirmations verified? What photo/consent policy is acceptable? What approval thresholds are configurable? Which languages matter in the pilot?