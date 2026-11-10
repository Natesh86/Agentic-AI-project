"""
SoloBiz AI - SQLite Database Layer
Thread-safe ACID operations for inventory, orders, suppliers, approval queue, and audit logs.
"""
import sqlite3
import json
import logging
from typing import Optional, Dict, Any, List
from config import DB_PATH

logger = logging.getLogger("solobiz.database")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for concurrent read/write and foreign keys
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_database() -> None:
    """Initialize database tables and seed baseline small-business catalog."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Inventory & Catalog
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        sku TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        available_qty INTEGER NOT NULL DEFAULT 0,
        reserved_qty INTEGER NOT NULL DEFAULT 0,
        reorder_level INTEGER NOT NULL DEFAULT 5,
        unit_price REAL NOT NULL,
        cost_price REAL NOT NULL,
        bom_components_json TEXT DEFAULT '[]',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        business_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        customer_name TEXT,
        channel TEXT NOT NULL,
        items_json TEXT NOT NULL,
        subtotal REAL NOT NULL,
        shipping_fee REAL NOT NULL DEFAULT 0.0,
        total_quote REAL NOT NULL,
        payment_status TEXT NOT NULL DEFAULT 'UNPAID',
        fulfilment_status TEXT NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Suppliers & Procurement
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        contact_email TEXT,
        lead_time_days INTEGER NOT NULL DEFAULT 3,
        moq INTEGER NOT NULL DEFAULT 10,
        price_catalog_json TEXT NOT NULL DEFAULT '{}'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_orders (
        po_id TEXT PRIMARY KEY,
        business_id TEXT NOT NULL,
        supplier_id TEXT NOT NULL,
        items_json TEXT NOT NULL,
        total_cost REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'DRAFT_PO',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    );
    """)

    # 4. Human Approval Queue (HITL)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS approval_queue (
        approval_id TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        business_id TEXT NOT NULL,
        trigger_type TEXT NOT NULL,
        summary TEXT NOT NULL,
        actions_held_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        resolution_notes TEXT
    );
    """)

    # 5. Tamper-evident Audit Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        audit_id TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        workflow_id TEXT NOT NULL,
        business_id TEXT NOT NULL,
        agent TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. Idempotency Filter
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS idempotency_keys (
        idempotency_key TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()

    # Seed catalog if empty
    cursor.execute("SELECT COUNT(*) FROM inventory;")
    if cursor.fetchone()[0] == 0:
        _seed_catalog_and_suppliers(conn)

    conn.close()
    logger.info("Database initialized successfully at %s", DB_PATH)


def _seed_catalog_and_suppliers(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    # Seed products matching SoloBiz opportunity canvas & golden mine
    sample_inventory = [
        (
            "SKU-JAS-200G",
            "Jasmine Scented Soy Candle (200g)",
            "Hand-poured 100% natural soy wax candle in glass jar with jasmine essential oils.",
            "CANDLES",
            15, 0, 5, 650.0, 240.0,
            json.dumps([{"item": "RAW-SOY-WAX", "qty_g": 200}, {"item": "RAW-JAR-200G", "qty": 1}, {"item": "RAW-WICK", "qty": 1}])
        ),
        (
            "SKU-LAV-SOY-BOX",
            "Lavender Soy Candle Gift Box",
            "Luxury gift hamper with 2 lavender candles, matches, and dried botanical sprigs.",
            "GIFT_BOXES",
            8, 0, 3, 1250.0, 520.0,
            json.dumps([{"item": "RAW-SOY-WAX", "qty_g": 400}, {"item": "RAW-GIFT-BOX", "qty": 1}, {"item": "RAW-WICK", "qty": 2}])
        ),
        (
            "SKU-HAMPER-CERAMIC",
            "Artisan Ceramic Luxe Hamper (Blue)",
            "Set of 2 handcrafted ceramic mugs with coasters and gourmet cookies.",
            "GIFT_BOXES",
            10, 0, 4, 1850.0, 800.0,
            json.dumps([])
        ),
        (
            "SKU-HAMPER-CANDLE-LUXE",
            "Candle Luxe Gift Hamper (Blue Edition)",
            "Curated candle set with ocean breeze scents in artisan royal blue jars.",
            "GIFT_BOXES",
            6, 0, 2, 2100.0, 950.0,
            json.dumps([])
        ),
        (
            "SKU-MUG-TERRACOTTA",
            "Ceramic Coffee Mug (Matte Terracotta)",
            "Minimalist handcrafted ceramic mug in rustic matte terracotta finish.",
            "CERAMICS",
            2, 0, 5, 450.0, 180.0,  # Note: 2 in stock (matches test case T018 stockout)
            json.dumps([])
        ),
        (
            "SKU-COOKIE-ALMOND",
            "Artisan Almond Cookies Box",
            "Freshly baked gourmet almond flour butter cookies (250g).",
            "BAKERY",
            20, 0, 5, 450.0, 150.0,
            json.dumps([])
        )
    ]

    cursor.executemany("""
    INSERT INTO inventory (sku, name, description, category, available_qty, reserved_qty, reorder_level, unit_price, cost_price, bom_components_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, sample_inventory)

    # Seed Suppliers
    sample_suppliers = [
        (
            "SUPP-CERAMICS-01",
            "Bengaluru Clayworks & Pottery",
            "CERAMICS",
            "orders@bengaluruclayworks.example.com",
            5, 10,
            json.dumps({
                "SKU-MUG-TERRACOTTA": {"unit_price": 180.0, "bulk_price_50": 150.0, "lead_time_days": 4}
            })
        ),
        (
            "SUPP-WAX-PACKAGING-02",
            "GreenLeaf Eco-Packaging & Waxes",
            "PACKAGING_AND_RAW",
            "sales@greenleafpack.example.com",
            3, 20,
            json.dumps({
                "RAW-SOY-WAX": {"unit_price": 0.60, "unit": "gram"},
                "RAW-GIFT-BOX": {"unit_price": 85.0, "unit": "piece"}
            })
        )
    ]

    cursor.executemany("""
    INSERT INTO suppliers (supplier_id, name, category, contact_email, lead_time_days, moq, price_catalog_json)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, sample_suppliers)

    conn.commit()


# --- Database Access Helper Functions ---

def record_audit(event_id: str, workflow_id: str, business_id: str, agent: str, action: str, details: str) -> None:
    import uuid
    conn = get_db_connection()
    conn.execute("""
    INSERT INTO audit_log (audit_id, event_id, workflow_id, business_id, agent, action, details)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (f"aud_{uuid.uuid4().hex[:10]}", event_id, workflow_id, business_id, agent, action, details))
    conn.commit()
    conn.close()


def check_and_record_idempotency(idempotency_key: str, event_id: str) -> bool:
    """Returns True if event is NEW (recorded). Returns False if duplicate within sliding window."""
    conn = get_db_connection()
    try:
        conn.execute("""
        INSERT INTO idempotency_keys (idempotency_key, event_id)
        VALUES (?, ?);
        """, (idempotency_key, event_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
