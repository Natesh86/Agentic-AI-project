"""
SoloBiz AI - Inventory Service
Deterministic stock management with ACID SQLite transaction locks and BOM resolution.
"""
import sqlite3
import json
import logging
from typing import Optional, Dict, Any, List
from core.database import get_db_connection

logger = logging.getLogger("solobiz.services.inventory")


def search_catalog_by_query(query: str) -> List[Dict[str, Any]]:
    """Searches catalog for products matching name, description, or category."""
    conn = get_db_connection()
    cursor = conn.cursor()
    pattern = f"%{query.strip().lower()}%"
    cursor.execute("""
    SELECT sku, name, description, category, available_qty, unit_price, cost_price
    FROM inventory
    WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ? OR LOWER(sku) LIKE ?;
    """, (pattern, pattern, pattern, pattern))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stock_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    """Returns current live stock status for a given SKU."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT sku, name, available_qty, reserved_qty, reorder_level, unit_price, cost_price, bom_components_json
    FROM inventory
    WHERE sku = ?;
    """, (sku,))
    row = cursor.fetchone()
    conn.close()
    if row:
        res = dict(row)
        res["bom_components"] = json.loads(res.get("bom_components_json", "[]"))
        return res
    return None


def reserve_stock_atomic(sku: str, qty_to_reserve: int) -> Dict[str, Any]:
    """
    Places an ACID transaction lock on the inventory row.
    Guarantees no race conditions or overselling.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE;")
        cursor.execute("""
        SELECT sku, name, available_qty, reserved_qty, reorder_level
        FROM inventory
        WHERE sku = ?;
        """, (sku,))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return {"success": False, "reason": f"SKU '{sku}' not found in catalog."}

        available = row["available_qty"]
        reserved = row["reserved_qty"]
        reorder_lvl = row["reorder_level"]

        if available < qty_to_reserve:
            conn.rollback()
            return {
                "success": False,
                "reason": f"Insufficient stock for {row['name']}. Available: {available}, Requested: {qty_to_reserve}.",
                "available": available,
                "requested": qty_to_reserve,
                "stockout": True
            }

        new_available = available - qty_to_reserve
        new_reserved = reserved + qty_to_reserve

        cursor.execute("""
        UPDATE inventory
        SET available_qty = ?, reserved_qty = ?, updated_at = CURRENT_TIMESTAMP
        WHERE sku = ?;
        """, (new_available, new_reserved, sku))
        conn.commit()

        reorder_triggered = new_available <= reorder_lvl

        return {
            "success": True,
            "sku": sku,
            "name": row["name"],
            "quantity_reserved": qty_to_reserve,
            "remaining_available": new_available,
            "reorder_needed": reorder_triggered
        }
    except Exception as e:
        conn.rollback()
        logger.error("Error in atomic stock reservation for %s: %s", sku, e)
        return {"success": False, "reason": str(e)}
    finally:
        conn.close()


def release_stock_reservation(sku: str, qty_to_release: int) -> bool:
    """Reverts a temporary reservation back into available stock."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE;")
        cursor.execute("SELECT reserved_qty, available_qty FROM inventory WHERE sku = ?;", (sku,))
        row = cursor.fetchone()
        if row:
            rev = min(row["reserved_qty"], qty_to_release)
            cursor.execute("""
            UPDATE inventory
            SET available_qty = available_qty + ?, reserved_qty = reserved_qty - ?
            WHERE sku = ?;
            """, (rev, rev, sku))
            conn.commit()
            return True
        conn.rollback()
        return False
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def list_low_stock_items() -> List[Dict[str, Any]]:
    """Returns all items whose available quantity has fallen below or equal to reorder level."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT sku, name, available_qty, reserved_qty, reorder_level, unit_price, cost_price
    FROM inventory
    WHERE available_qty <= reorder_level;
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
