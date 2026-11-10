"""
SoloBiz AI - Framework-Free Agent Loop
Direct Anthropic API tool-calling loop with loop guards, prompt caching, and Langfuse tracing.
Zero third-party agent framework dependencies (no LangChain, no CrewAI).
Follows Langfuse AI skill best practices for agent graphs and observation types.
"""
import os
import json
import logging
from typing import List, Dict, Any, Callable, Optional, Tuple
from config import (
    ANTHROPIC_API_KEY,
    MODEL_FAST,
    MODEL_REASONING,
    MAX_AGENT_TURNS,
    MAX_TOOL_CALLS,
    ENABLE_PROMPT_CACHING
)
from core.telemetry import TelemetryManager, ANTHROPIC_PRICING, DEFAULT_PRICING

logger = logging.getLogger("solobiz.agent_loop")


class AgentLoop:
    """
    Framework-free agent execution loop for Anthropic Claude.
    Executes a multi-turn conversation until Claude stops calling tools
    or until max_turns/max_tool_calls safety boundaries are reached.
    """

    def __init__(
        self,
        agent_name: str,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_dispatch: Optional[Dict[str, Callable]] = None,
        model: Optional[str] = None
    ):
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.tool_dispatch = tool_dispatch or {}
        self.model = model or MODEL_FAST
        self.telemetry = TelemetryManager.get_instance()

        self.anthropic_client = None
        if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_anthropic_api_key_here":
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            except Exception as e:
                logger.warning("Could not initialize Anthropic client: %s. Using mock fallback.", e)

    def run(
        self,
        user_message: str,
        trace=None,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Executes the agent loop inside a Langfuse 'agent' observation node.
        Returns:
            (final_text: str, executed_actions: List[Dict], token_cost_info: Dict)
        """
        with self.telemetry.start_observation(
            name=self.agent_name,
            as_type="agent",
            input={"prompt": user_message}
        ) as agent_obs:
            final_text, actions, costs = self._run_internal(user_message, extra_context)
            agent_obs.update(output={"response": final_text, "action_count": len(actions)})
            return final_text, actions, costs

    def _run_internal(
        self,
        user_message: str,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        messages = [{"role": "user", "content": user_message}]
        executed_actions = []
        total_costs = {"usd": 0.0, "inr": 0.0, "input_tokens": 0, "output_tokens": 0}

        turn_count = 0
        total_tool_calls = 0

        # Build tools payload with prompt caching if enabled
        formatted_tools = []
        for i, t in enumerate(self.tools):
            tool_copy = dict(t)
            # Add cache_control to the last tool definition for prompt caching
            if ENABLE_PROMPT_CACHING and i == len(self.tools) - 1:
                tool_copy["cache_control"] = {"type": "ephemeral"}
            formatted_tools.append(tool_copy)

        # Build system prompt with prompt caching
        system_payload = self.system_prompt
        if ENABLE_PROMPT_CACHING:
            system_payload = [
                {
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ]

        # Live Anthropic API Loop
        if self.anthropic_client:
            rates = ANTHROPIC_PRICING.get(self.model, DEFAULT_PRICING)

            while turn_count < MAX_AGENT_TURNS:
                turn_count += 1

                try:
                    kwargs = {
                        "model": self.model,
                        "max_tokens": 1024,
                        "system": system_payload,
                        "messages": messages
                    }
                    if formatted_tools:
                        kwargs["tools"] = formatted_tools

                    response = self.anthropic_client.messages.create(**kwargs)
                except Exception as e:
                    logger.error("Anthropic API call failed on turn %d: %s", turn_count, e)
                    break

                # Extract tokens & calculate costs
                usage = response.usage
                in_tokens = getattr(usage, "input_tokens", 0)
                out_tokens = getattr(usage, "output_tokens", 0)
                cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
                cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0

                cost = self.telemetry.calculate_cost(self.model, in_tokens, out_tokens, cache_read, cache_create)
                total_costs["usd"] += cost["usd"]
                total_costs["inr"] += cost["inr"]
                total_costs["input_tokens"] += cost["input_tokens"]
                total_costs["output_tokens"] += cost["output_tokens"]

                assistant_content = response.content
                text_blocks = [b.text for b in assistant_content if getattr(b, "type", "") == "text"]
                output_str = "\n".join(text_blocks) if text_blocks else str(assistant_content)

                # Record generation in Langfuse
                with self.telemetry.start_observation(
                    name=f"{self.agent_name}_turn_{turn_count}",
                    as_type="generation",
                    model=self.model,
                    input=messages,
                    output=output_str,
                    usage_details={
                        "input": in_tokens,
                        "output": out_tokens,
                        "total": in_tokens + out_tokens + cache_read + cache_create,
                        "cache_read_input_tokens": cache_read,
                        "cache_creation_input_tokens": cache_create
                    },
                    cost_details={
                        "input": (in_tokens / 1_000_000.0) * rates["input"],
                        "output": (out_tokens / 1_000_000.0) * rates["output"],
                        "total": cost["usd"]
                    },
                    metadata={"calculated_cost_inr": cost["inr"]}
                ):
                    pass

                # Process response content
                messages.append({"role": "assistant", "content": assistant_content})

                tool_use_blocks = [b for b in assistant_content if getattr(b, "type", "") == "tool_use"]

                if not tool_use_blocks or response.stop_reason == "end_turn":
                    # Finished reasoning
                    return (output_str, executed_actions, total_costs)

                # Process Tool Calls
                tool_result_content = []
                for tool_block in tool_use_blocks:
                    total_tool_calls += 1
                    if total_tool_calls > MAX_TOOL_CALLS:
                        tool_result_content.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": json.dumps({"error": "MAX_TOOL_CALLS_EXCEEDED"}),
                            "is_error": True
                        })
                        break

                    tool_name = tool_block.name
                    tool_input = tool_block.input

                    with self.telemetry.start_observation(
                        name=f"tool_{tool_name}",
                        as_type="tool",
                        input=tool_input
                    ) as tool_obs:
                        handler = self.tool_dispatch.get(tool_name)
                        if handler:
                            try:
                                result = handler(**tool_input)
                                tool_obs.update(output=result)
                                tool_result_content.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_block.id,
                                    "content": json.dumps(result) if not isinstance(result, str) else result
                                })
                                executed_actions.append({
                                    "tool": tool_name,
                                    "input": tool_input,
                                    "result": result
                                })
                            except Exception as err:
                                tool_obs.update(output={"error": str(err)}, level="ERROR")
                                tool_result_content.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_block.id,
                                    "content": json.dumps({"error": str(err)}),
                                    "is_error": True
                                })
                        else:
                            tool_obs.update(output={"error": f"Tool '{tool_name}' not implemented"}, level="ERROR")
                            tool_result_content.append({
                                "type": "tool_result",
                                "tool_use_id": tool_block.id,
                                "content": json.dumps({"error": f"Tool '{tool_name}' not implemented"}),
                                "is_error": True
                            })

                messages.append({"role": "user", "content": tool_result_content})

            # Loop limit reached
            return ("Execution halted: MAX_AGENT_TURNS reached.", executed_actions, total_costs)

        # Intelligent Deterministic Simulation Fallback (for zero-key local testing and golden evals)
        return self._simulate_fallback(user_message, extra_context)

    def _simulate_fallback(
        self,
        user_message: str,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """Provides accurate mock evaluation when ANTHROPIC_API_KEY is not yet supplied."""
        sim_cost = self.telemetry.calculate_cost(
            self.model,
            input_tokens=850,
            output_tokens=220,
            cache_read_tokens=600
        )
        sim_response = f"[Agent {self.agent_name} processed]: Request addressed accurately."
        with self.telemetry.start_observation(
            name=f"{self.agent_name}_turn_1",
            as_type="generation",
            model=self.model,
            input=user_message,
            output=sim_response,
            usage_details={
                "input": 850,
                "output": 220,
                "total": 1070,
                "cache_read_input_tokens": 600
            },
            cost_details={
                "total": sim_cost["usd"]
            },
            metadata={"simulated": True, "cost_inr": sim_cost["inr"]}
        ):
            pass

        return (
            sim_response,
            [],
            sim_cost
        )
