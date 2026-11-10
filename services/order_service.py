"""
SoloBiz AI - Order Service
Deterministic pricing calculations, delivery fee rules, and order lifecycle management.
"""
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from core.database import get_db_connection
from services.inventory_service import get_stock_by_sku

logger = logging.getLogger("solobiz.services.order")


def calculate_shipping_fee(destination_hint: str) -> float:
    """Deterministic delivery fee calculator based on destination."""
    dest = destination_hint.lower()
    if any(k in dest for k in ["bengaluru", "bangalore", "indiranagar", "koramangala", "whitefield"]):
        return 50.0  # Local express Bengaluru
    elif any(k in dest for k in ["pune", "mumbai", "chennai", "hyderabad"]):
        return 120.0  # Regional express
    return 150.0  # Pan-India surface


def calculate_quote(
    line_items: List[Dict[str, Any]],
    destination_hint: str = "Bengaluru"
) -> Dict[str, Any]:
    """
    Computes exact subtotal, shipping fee, and total quote.
    line_items format: [{"sku": "SKU-JAS-200G", "quantity": 1}]
    """
    subtotal = 0.0
    detailed_items = []

    for item in line_items:
        sku = item.get("sku", "")
        qty = item.get("quantity", 1)

        product = get_stock_by_sku(sku)
        if product:
            unit_price = product["unit_price"]
            item_total = unit_price * qty
            subtotal += item_total
            detailed_items.append({
                "sku": sku,
                "name": product["name"],
                "quantity": qty,
                "unit_price": unit_price,
                "item_total": item_total
            })
        else:
            # Handle ad-hoc services (e.g. SERVICE-CUSTOM-TAG)
            if "custom" in sku.lower() or "tag" in sku.lower():
                detailed_items.append({
                    "sku": sku,
                    "name": "Custom Personalization Tag",
                    "quantity": qty,
                    "unit_price": 50.0,
                    "item_total": 50.0 * qty
                })
                subtotal += 50.0 * qty

    shipping_fee = calculate_shipping_fee(destination_hint)
    total_quote = subtotal + shipping_fee

    return {
        "items": detailed_items,
        "subtotal": subtotal,
        "shipping_fee": shipping_fee,
        "total_quote": total_quote
    }


def create_order_draft(
    business_id: str,
    customer_id: str,
    customer_name: Optional[str],
    channel: str,
    items: List[Dict[str, Any]],
    subtotal: float,
    shipping_fee: float,
    total_quote: float
) -> str:
    """Inserts a new provisional order record in SQLite."""
    order_id = f"ord_{uuid.uuid4().hex[:8]}"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO orders (order_id, business_id, customer_id, customer_name, channel, items_json, subtotal, shipping_fee, total_quote, payment_status, fulfilment_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNPAID', 'PENDING');
    """, (
        order_id, business_id, customer_id, customer_name, channel,
        json.dumps(items), subtotal, shipping_fee, total_quote
    ))
    conn.commit()
    conn.close()
    return order_id


def update_order_status(order_id: str, payment_status: str, fulfilment_status: Optional[str] = None) -> bool:
    """Updates the state of an existing order."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if fulfilment_status:
        cursor.execute("""
        UPDATE orders
        SET payment_status = ?, fulfilment_status = ?
        WHERE order_id = ?;
        """, (payment_status, fulfilment_status, order_id))
    else:
        cursor.execute("""
        UPDATE orders
        SET payment_status = ?
        WHERE order_id = ?;
        """, (payment_status, order_id))
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected
