"""
SoloBiz AI - Customer Engagement Agent
Front-line conversational interface for Instagram DMs, WhatsApp, and Web Chat.
Handles FAQs, needs qualification, Hinglish, product quotes, and clarification.
"""
from typing import Dict, Any, List, Tuple
from core.agent_loop import AgentLoop
from config import MODEL_FAST
from services.inventory_service import search_catalog_by_query, get_stock_by_sku, reserve_stock_atomic
from services.order_service import calculate_quote

SYSTEM_PROMPT = """You are the Customer Engagement Specialist for SoloBiz AI, an artisan small business (craft candles, ceramics, hampers).
Your mission is to assist customers with warmth, professional accuracy, and commercial rigor.

Core Rules:
1. Always search catalog or check stock before quoting prices or confirming availability.
2. If the user's inquiry is ambiguous (e.g. asking for 'blue hamper' when there are multiple variants), ask polite clarification questions rather than guessing.
3. If the user writes in Hinglish (code-switched Hindi-English), respond politely in natural, polite Hinglish while keeping pricing accurate.
4. If an item is out of stock or low in stock, clearly state current availability and suggest backordering or alternative variants.
5. NEVER promise discounts exceeding 0% or unauthorized delivery dates without checking.
6. When giving a quote, break down item subtotal and delivery charge clearly.
"""

TOOLS = [
    {
        "name": "search_catalog",
        "description": "Searches products by keyword in name, description, or category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword or product name"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "check_stock",
        "description": "Checks available and reserved stock for a specific product SKU.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sku": {"type": "string", "description": "Product SKU code"}
            },
            "required": ["sku"]
        }
    },
    {
        "name": "calculate_quote",
        "description": "Computes deterministic price quote and delivery fee for specified items and destination.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string"},
                            "quantity": {"type": "integer"}
                        },
                        "required": ["sku", "quantity"]
                    }
                },
                "destination_hint": {"type": "string", "description": "City or pincode"}
            },
            "required": ["items"]
        }
    }
]


def create_engagement_agent() -> AgentLoop:
    def handle_search(query: str):
        return search_catalog_by_query(query)

    def handle_check_stock(sku: str):
        return get_stock_by_sku(sku)

    def handle_quote(items: List[Dict[str, Any]], destination_hint: str = "Bengaluru"):
        return calculate_quote(items, destination_hint)

    dispatch = {
        "search_catalog": handle_search,
        "check_stock": handle_check_stock,
        "calculate_quote": handle_quote
    }

    return AgentLoop(
        agent_name="CustomerEngagementAgent",
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        tool_dispatch=dispatch,
        model=MODEL_FAST
    )
