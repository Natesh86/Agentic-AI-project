"""
SoloBiz AI - Finance & Insights Service
Computes order gross margins, COGS, and daily executive rollups.
"""
from typing import Dict, Any, List
from core.database import get_db_connection
from services.inventory_service import get_stock_by_sku


def calculate_order_financials(line_items: List[Dict[str, Any]], shipping_fee: float) -> Dict[str, float]:
    """Computes gross revenue, estimated COGS, and net gross margin for an order."""
    revenue = 0.0
    cogs = 0.0

    for item in line_items:
        sku = item.get("sku", "")
        qty = item.get("quantity", 1)
        price = item.get("unit_price", 0.0)

        revenue += price * qty
        product = get_stock_by_sku(sku)
        if product:
            cogs += product["cost_price"] * qty
        else:
            cogs += (price * 0.40) * qty  # Default 40% COGS estimate for custom work

    total_revenue = revenue + shipping_fee
    shipping_cost = shipping_fee * 0.75  # Courier takes 75% of shipping fee
    gross_margin = total_revenue - (cogs + shipping_cost)

    return {
        "estimated_revenue": round(total_revenue, 2),
        "estimated_cogs": round(cogs, 2),
        "estimated_shipping_cost": round(shipping_cost, 2),
        "projected_gross_margin": round(gross_margin, 2)
    }


def get_daily_operational_rollup(business_id: str) -> Dict[str, Any]:
    """Rolls up daily orders, total revenue, pending approvals, and inventory alerts."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*), COALESCE(SUM(total_quote), 0.0)
    FROM orders
    WHERE business_id = ? AND DATE(created_at) = DATE('now');
    """, (business_id,))
    order_count, total_sales = cursor.fetchone()

    cursor.execute("""
    SELECT COUNT(*) FROM approval_queue
    WHERE business_id = ? AND status = 'PENDING_APPROVAL';
    """, (business_id,))
    pending_approvals = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM inventory WHERE available_qty <= reorder_level;")
    low_stock_count = cursor.fetchone()[0]

    conn.close()

    return {
        "today_order_count": order_count,
        "today_gross_sales": total_sales,
        "pending_approvals_count": pending_approvals,
        "low_stock_alerts_count": low_stock_count
    }
