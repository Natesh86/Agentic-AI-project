"""
SoloBiz AI - Procurement Agent
Handles supplier trade-off evaluation (unit price vs lead time vs MOQ) and prepares draft POs.
Zero automated payment or disbursement capability.
"""
from typing import Dict, Any, List
import json
import uuid
from core.agent_loop import AgentLoop
from config import MODEL_REASONING
from core.database import get_db_connection
from services.inventory_service import list_low_stock_items

SYSTEM_PROMPT = """You are the Procurement Specialist for SoloBiz AI.
Your mission is to evaluate supplier options when stock is low, recommend optimal replenishment quantities,
and draft Purchase Orders for the owner's review.

Core Rules:
1. Always evaluate trade-offs between unit cost discounts, minimum order quantities (MOQs), and delivery lead times.
2. Every Purchase Order you prepare MUST be marked as DRAFT_PO. You have ZERO authority to disburse funds.
3. Recommend realistic batch sizes that protect cash flow while preventing stockouts.
"""

TOOLS = [
    {
        "name": "check_low_stock",
        "description": "Lists all inventory items that have fallen below safety reorder levels.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_supplier_catalog",
        "description": "Fetches registered suppliers and their wholesale pricing and lead times.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "e.g., CERAMICS, PACKAGING_AND_RAW"}
            }
        }
    },
    {
        "name": "prepare_purchase_order_draft",
        "description": "Creates a draft PO record held for mandatory owner approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "supplier_id": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "unit_cost": {"type": "number"}
                        },
                        "required": ["item", "quantity", "unit_cost"]
                    }
                },
                "total_cost": {"type": "number"}
            },
            "required": ["supplier_id", "items", "total_cost"]
        }
    }
]


def create_procurement_agent() -> AgentLoop:
    def handle_low_stock():
        return list_low_stock_items()

    def handle_suppliers(category: str = ""):
        conn = get_db_connection()
        cursor = conn.cursor()
        if category:
            cursor.execute("SELECT * FROM suppliers WHERE category = ?;", (category,))
        else:
            cursor.execute("SELECT * FROM suppliers;")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        for r in rows:
            r["price_catalog"] = json.loads(r.get("price_catalog_json", "{}"))
        return rows

    def handle_draft_po(supplier_id: str, items: List[Dict[str, Any]], total_cost: float):
        po_id = f"po_{uuid.uuid4().hex[:8]}"
        conn = get_db_connection()
        conn.execute("""
        INSERT INTO purchase_orders (po_id, business_id, supplier_id, items_json, total_cost, status)
        VALUES (?, 'biz_artisan_candles_001', ?, ?, ?, 'DRAFT_PO');
        """, (po_id, supplier_id, json.dumps(items), total_cost))
        conn.commit()
        conn.close()
        return {"po_id": po_id, "status": "DRAFT_PO", "message": "PO saved in draft queue for owner approval."}

    dispatch = {
        "check_low_stock": handle_low_stock,
        "get_supplier_catalog": handle_suppliers,
        "prepare_purchase_order_draft": handle_draft_po
    }

    return AgentLoop(
        agent_name="ProcurementAgent",
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        tool_dispatch=dispatch,
        model=MODEL_REASONING
    )
