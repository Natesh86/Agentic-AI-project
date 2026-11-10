"""
SoloBiz AI - Configuration & Constants
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# --- Anthropic LLM Settings ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Model Tiering:
# Claude 3.5 Haiku: High speed, low cost for triage, FAQs, classification
MODEL_FAST = os.environ.get("SOLOBIZ_MODEL_FAST", "claude-3-5-haiku-20241022")
# Claude 3.5 Sonnet: High reasoning for Supervisor, procurement optimization, vision, creative copy
MODEL_REASONING = os.environ.get("SOLOBIZ_MODEL_REASONING", "claude-3-5-sonnet-20241022")

# Anthropic Prompt Caching toggle
ENABLE_PROMPT_CACHING = os.environ.get("ENABLE_PROMPT_CACHING", "true").lower() == "true"

# --- Langfuse Observability Settings ---
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip("\"'")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "").strip("\"'")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")).strip("\"'")
ENABLE_LANGFUSE = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY and not LANGFUSE_PUBLIC_KEY.startswith("pk-lf-..."))

# --- Database & Storage ---
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = os.environ.get("SOLOBIZ_DB_PATH", str(STORAGE_DIR / "solobiz.db"))

# --- Execution Budget & Safety Limits ---
MAX_AGENT_TURNS = int(os.environ.get("MAX_AGENT_TURNS", "12"))
MAX_TOOL_CALLS = int(os.environ.get("MAX_TOOL_CALLS", "20"))
IDEMPOTENCY_WINDOW_SECONDS = int(os.environ.get("IDEMPOTENCY_WINDOW_SECONDS", "600"))

# --- Human-in-the-Loop Quantitative Thresholds ---
MAX_AUTONOMOUS_ORDER_VALUE = float(os.environ.get("MAX_AUTONOMOUS_ORDER_VALUE", "5000.0"))  # INR
SENTIMENT_CRITICAL_THRESHOLD = float(os.environ.get("SENTIMENT_CRITICAL_THRESHOLD", "0.35"))
MIN_CONFIDENCE_THRESHOLD = float(os.environ.get("MIN_CONFIDENCE_THRESHOLD", "0.85"))

# Mandatory approval triggers
HITL_LEGAL_KEYWORDS = [
    "lawyer", "court", "police", "consumer forum", "fraud",
    "cheating", "legal notice", "allergy", "poison", "hazard"
]

HITL_PROMPT_INJECTION_PATTERNS = [
    r"system\s*override",
    r"ignore\s+(all\s+)?prior\s+instructions",
    r"maintenance\s+diagnostic\s+mode",
    r"apply\s+coupon\s+code_zero_free",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"reveal\s+(system\s+)?prompt",
]
