"""
SoloBiz AI - Reputation & Reviews Agent
Monitors public comments and customer reviews, scores sentiment, detects hostility/sarcasm,
and drafts empathetic de-escalating responses.
"""
from typing import Dict, Any
from core.agent_loop import AgentLoop
from config import MODEL_FAST

SYSTEM_PROMPT = """You are the Reputation & Customer Grievance Specialist for SoloBiz AI.
Your mission is to protect brand reputation, listen to public customer feedback, and respond empathetically.

Core Rules:
1. Classify sentiment polarity from 0.0 (hostile/angry) to 1.0 (ecstatic/delighted).
2. For 5-star or highly positive comments (>0.80), post warm, appreciative template replies.
3. For negative sentiment (<0.35) or angry grievances, craft an empathetic, de-escalating holding reply WITHOUT admitting legal liability or promising unauthorized refunds.
4. If legal threats, consumer court notices, or police allegations are present, immediately flag the ticket for urgent human takeover.
"""

TOOLS = [
    {
        "name": "classify_sentiment",
        "description": "Calculates sentiment score and checks for hostility or legal risk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "draft_reputation_reply",
        "description": "Prepares an empathetic reply to a customer review or public grievance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sentiment_score": {"type": "number"},
                "review_text": {"type": "string"}
            },
            "required": ["sentiment_score", "review_text"]
        }
    }
]


def create_reputation_agent() -> AgentLoop:
    def handle_sentiment(text: str):
        t_low = text.lower()
        if any(w in t_low for w in ["fraud", "cheating", "lawyer", "court", "police", "scam"]):
            return {"sentiment_score": 0.15, "category": "LEGAL_THREAT_HOSTILE"}
        elif any(w in t_low for w in ["delay", "disappointed", "bad", "broken", "worst"]):
            return {"sentiment_score": 0.30, "category": "NEGATIVE_COMPLAINT"}
        elif any(w in t_low for w in ["love", "amazing", "beautiful", "gorgeous", "best"]):
            return {"sentiment_score": 0.95, "category": "POSITIVE_ADVOCATE"}
        return {"sentiment_score": 0.60, "category": "NEUTRAL"}

    def handle_reply(sentiment_score: float, review_text: str):
        if sentiment_score < 0.35:
            reply = (
                "Hi, we sincerely apologize for the distress and frustration caused. "
                "We treat our customer commitments with the highest seriousness. Our founder is personally "
                "investigating this matter right now, and we will contact you directly within 2 business hours "
                "to ensure this is resolved for you."
            )
        elif sentiment_score > 0.80:
            reply = (
                "Thank you so much for your kind words! We pour immense love into our handcrafted collections, "
                "and knowing they brought you joy means the world to our workshop team. ✨"
            )
        else:
            reply = "Thank you for sharing your feedback with us! Please let us know if we can assist you with anything further."

        return {"response_draft": reply, "sentiment_score": sentiment_score}

    dispatch = {
        "classify_sentiment": handle_sentiment,
        "draft_reputation_reply": handle_reply
    }

    return AgentLoop(
        agent_name="ReputationAgent",
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        tool_dispatch=dispatch,
        model=MODEL_FAST
    )
