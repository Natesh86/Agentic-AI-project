"""
SoloBiz AI - Fulfilment Service
Deterministic courier rate calculations, delivery SLAs, and dispatch tracking.
"""
from datetime import datetime, timedelta
from typing import Dict, Any


def evaluate_fulfilment_sla(destination_hint: str, is_custom_order: bool = False) -> Dict[str, Any]:
    """Computes realistic courier SLAs and promised delivery dates."""
    now = datetime.now()
    dest = destination_hint.lower()

    if any(k in dest for k in ["bengaluru", "bangalore", "indiranagar", "whitefield"]):
        transit_days = 1 if not is_custom_order else 2
        courier = "BLUEDART_LOCAL_EXPRESS"
    elif any(k in dest for k in ["pune", "mumbai", "chennai"]):
        transit_days = 2 if not is_custom_order else 3
        courier = "DELHIVERY_AIR"
    else:
        transit_days = 4 if not is_custom_order else 5
        courier = "BLUEDART_SURFACE"

    promised_date = (now + timedelta(days=transit_days)).strftime("%Y-%m-%d")

    return {
        "courier_partner": courier,
        "transit_days": transit_days,
        "promised_delivery_date": promised_date,
        "fulfilment_status": "READY_FOR_PACKAGING"
    }
