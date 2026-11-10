"""
SoloBiz AI - Langfuse Telemetry & Cost Engine
Tracks multi-agent execution traces, model latency, prompt cache hits, and USD / INR costs.
Follows Langfuse AI skill best practices for agent graphs, observation types, scores, and attributes.
"""
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Generator
from datetime import datetime

from config import (
    ENABLE_LANGFUSE,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_HOST
)

logger = logging.getLogger("solobiz.telemetry")

# Pricing per million tokens (Anthropic 2026 rates)
ANTHROPIC_PRICING = {
    "claude-3-5-haiku-20241022": {
        "input": 0.80,
        "output": 4.00,
        "cache_read": 0.08,
        "cache_creation": 1.00,
    },
    "claude-3-5-sonnet-20241022": {
        "input": 3.00,
        "output": 15.00,
        "cache_read": 0.30,
        "cache_creation": 3.75,
    }
}
DEFAULT_PRICING = ANTHROPIC_PRICING["claude-3-5-haiku-20241022"]
USD_TO_INR = 86.50


class NullObservation:
    """Safe fallback observation wrapper when Langfuse is disabled or in local-only mode."""
    def __init__(self, name: str = "", as_type: str = "span"):
        self.name = name
        self.as_type = as_type
        self.id = "local_obs"

    def update(self, **kwargs) -> "NullObservation":
        return self

    def end(self) -> None:
        pass


class TelemetryManager:
    _instance = None

    def __init__(self):
        self.langfuse_client = None
        self._propagate_func = None

        if ENABLE_LANGFUSE:
            try:
                from langfuse import Langfuse, propagate_attributes
                self.langfuse_client = Langfuse(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=LANGFUSE_HOST
                )
                self._propagate_func = propagate_attributes
                logger.info("Langfuse Telemetry initialized successfully with host: %s", LANGFUSE_HOST)
            except Exception as e:
                logger.warning("Could not initialize Langfuse client: %s. Telemetry running in local fallback mode.", e)
                self.langfuse_client = None
        else:
            logger.info("Langfuse keys not configured or disabled. Running in local console observability mode.")

    @classmethod
    def get_instance(cls) -> "TelemetryManager":
        if cls._instance is None:
            cls._instance = TelemetryManager()
        return cls._instance

    def calculate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0
    ) -> Dict[str, float]:
        """Calculates precise USD and INR cost for an Anthropic API call including prompt caching."""
        rates = ANTHROPIC_PRICING.get(model_name, DEFAULT_PRICING)

        cost_in = (input_tokens / 1_000_000.0) * rates["input"]
        cost_out = (output_tokens / 1_000_000.0) * rates["output"]
        cost_cache_read = (cache_read_tokens / 1_000_000.0) * rates["cache_read"]
        cost_cache_create = (cache_creation_tokens / 1_000_000.0) * rates["cache_creation"]

        total_usd = cost_in + cost_out + cost_cache_read + cost_cache_create
        total_inr = total_usd * USD_TO_INR

        return {
            "usd": round(total_usd, 6),
            "inr": round(total_inr, 4),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_creation_tokens": cache_creation_tokens
        }

    @contextmanager
    def start_observation(
        self,
        name: str,
        as_type: str = "span",
        input: Optional[Any] = None,
        output: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        usage_details: Optional[Dict[str, int]] = None,
        cost_details: Optional[Dict[str, float]] = None,
        level: Optional[str] = None,
        status_message: Optional[str] = None
    ) -> Generator[Any, None, None]:
        """
        Starts an active Langfuse observation (agent, generation, tool, guardrail, span).
        Yields the observation object so callers can call `.update(...)` during execution.
        Safely falls back to NullObservation if Langfuse is disabled or errors occur.
        """
        if self.langfuse_client:
            try:
                with self.langfuse_client.start_as_current_observation(
                    name=name,
                    as_type=as_type,
                    input=input,
                    output=output,
                    metadata=metadata,
                    model=model,
                    usage_details=usage_details,
                    cost_details=cost_details,
                    level=level,
                    status_message=status_message
                ) as obs:
                    yield obs
                    return
            except Exception as e:
                logger.debug("Langfuse start_as_current_observation failed for '%s': %s", name, e)

        # Fallback if disabled or failed
        null_obs = NullObservation(name=name, as_type=as_type)
        yield null_obs

    @contextmanager
    def propagate_attributes(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_name: Optional[str] = None,
        version: Optional[str] = None
    ) -> Generator[None, None, None]:
        """
        Propagates trace-level attributes (user_id, session_id, tags, metadata, trace_name)
        down to all child observations and LLM calls in this context.
        """
        if self._propagate_func:
            try:
                with self._propagate_func(
                    user_id=user_id,
                    session_id=session_id,
                    tags=tags,
                    metadata=metadata,
                    trace_name=trace_name,
                    version=version
                ):
                    yield
                    return
            except Exception as e:
                logger.debug("Langfuse propagate_attributes failed: %s", e)

        yield

    def score_current_trace(
        self,
        name: str,
        value: Any,
        data_type: Optional[str] = None,
        comment: Optional[str] = None
    ) -> None:
        """Records an evaluation score on the currently active trace."""
        if self.langfuse_client:
            try:
                self.langfuse_client.score_current_trace(
                    name=name,
                    value=value,
                    data_type=data_type,
                    comment=comment
                )
            except Exception as e:
                logger.debug("Langfuse score_current_trace failed for '%s': %s", name, e)

    def get_current_trace_id(self) -> Optional[str]:
        """Returns the current trace ID if within an active observation context."""
        if self.langfuse_client:
            try:
                return self.langfuse_client.get_current_trace_id()
            except Exception:
                pass
        return None

    def get_trace_url(self) -> Optional[str]:
        """Returns the web URL to inspect the active trace in Langfuse Cloud."""
        if self.langfuse_client:
            try:
                return self.langfuse_client.get_trace_url()
            except Exception:
                pass
        return None

    def flush(self) -> None:
        """Flushes queued observations to Langfuse backend."""
        if self.langfuse_client:
            try:
                self.langfuse_client.flush()
            except Exception as e:
                logger.debug("Langfuse flush failed: %s", e)

    def shutdown(self) -> None:
        """Gracefully shuts down Langfuse client."""
        if self.langfuse_client:
            try:
                self.langfuse_client.shutdown()
            except Exception as e:
                logger.debug("Langfuse shutdown failed: %s", e)
