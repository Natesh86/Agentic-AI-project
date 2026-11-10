"""
SoloBiz AI - Product & Marketing Creative Agent
Handles multimodal photo understanding, visual taxonomy, and draft social copy with hashtags.
Zero autonomous social publishing - 100% pre-publication owner approval.
"""
from typing import Dict, Any, List
import uuid
from core.agent_loop import AgentLoop
from config import MODEL_REASONING

SYSTEM_PROMPT = """You are the Product & Marketing Creative Specialist for SoloBiz AI.
Your mission is to craft high-conversion, aesthetically tailored social media captions (Instagram/WhatsApp)
for handcrafted artisan goods.

Core Rules:
1. Every social post draft MUST include: an arresting hook, clean visual spacing, evocative sensory descriptions, relevant hashtags (#handmadegifts #soycandles #artisanhome), and a clear call-to-action.
2. If customer photos feature identifiable third-party faces, flag that explicit written model consent is required before publication.
3. Every drafted post is saved in the review queue. You have ZERO authority to publish live without owner sign-off.
"""

TOOLS = [
    {
        "name": "draft_social_caption",
        "description": "Generates platform-specific caption, hashtags, and call-to-action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_theme": {"type": "string"},
                "platform": {"type": "string", "enum": ["INSTAGRAM", "WHATSAPP_BROADCAST"]},
                "target_audience": {"type": "string"}
            },
            "required": ["product_theme"]
        }
    },
    {
        "name": "queue_post_for_review",
        "description": "Stores a draft post for mandatory owner review and approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "caption": {"type": "string"},
                "platform": {"type": "string"},
                "media_asset_id": {"type": "string"}
            },
            "required": ["caption"]
        }
    }
]


def create_marketing_agent() -> AgentLoop:
    def handle_caption(product_theme: str, platform: str = "INSTAGRAM", target_audience: str = "gift buyers"):
        caption = (
            f"✨ The warmth of slow craftsmanship. ✨\n\n"
            f"Our {product_theme} is individually hand-poured in small batches using 100% pure soy wax "
            f"and therapeutic botanical oils. Designed to bring calm and luxury to your evenings.\n\n"
            f"📦 Express delivery available across India.\n"
            f"💬 Send us a DM to customize your gift box or tap the link in bio!\n\n"
            f"#handcrafted #artisanhome #soycandles #luxuryliving #slowcraft #giftideas"
        )
        return {"caption": caption, "platform": platform}

    def handle_queue(caption: str, platform: str = "INSTAGRAM", media_asset_id: str = ""):
        draft_id = f"mkt_draft_{uuid.uuid4().hex[:8]}"
        return {
            "draft_id": draft_id,
            "status": "QUEUED_FOR_APPROVAL",
            "caption": caption,
            "message": "Draft queued in owner dashboard. Awaiting approval before live publishing."
        }

    dispatch = {
        "draft_social_caption": handle_caption,
        "queue_post_for_review": handle_queue
    }

    return AgentLoop(
        agent_name="ProductMarketingAgent",
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        tool_dispatch=dispatch,
        model=MODEL_REASONING
    )
