"""
HaonerAgentLoop -- Reusable Multi-Turn Agent Engine

Runs the tool-calling loop using standard OpenAI-spec tool calling or Anthropic.
Supports both OpenAI and Anthropic APIs with tool_use as termination signal.
"""

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ToolError:
    """Record of a tool execution error during the agent loop."""
    turn: int
    tool_name: str
    arguments: str
    error: str
    tool_result: str


@dataclass
class AgentResult:
    """Result of running the agent loop."""
    messages: List[Dict[str, Any]]
    managed_state: Optional[Dict[str, Any]] = None
    turns_used: int = 0
    finished_naturally: bool = False
    reasoning_per_turn: List[Optional[str]] = field(default_factory=list)
    tool_errors: List[ToolError] = field(default_factory=list)


def get_provider() -> str:
    """Get the LLM provider from environment."""
    from .env_utils import get_provider as _get_provider
    return _get_provider()


class HaonerAgentLoop:
    """
    Runs the tool-calling loop with support for both OpenAI and Anthropic.

    For OpenAI:
    - Check response.choices[0].message.tool_calls
    - Finished when no tool_calls

    For Anthropic:
    - Check response.stop_reason
    - tool_use means more tools to call, end_turn means finished
    """

    def __init__(
        self,
        client,
        tool_schemas: List[Dict[str, Any]],
        valid_tool_names: Set[str],
        max_turns: int = 30,
        task_id: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        provider: str = "openai",
    ):
        self.client = client
        self.tool_schemas = tool_schemas
        self.valid_tool_names = valid_tool_names
        self.max_turns = max_turns
        self.task_id = task_id or str(uuid.uuid4())
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider

    async def run(self, messages: List[Dict[str, Any]]) -> AgentResult:
        """Execute the full agent loop."""
        reasoning_per_turn = []
        tool_errors: List[ToolError] = []

        for turn in range(self.max_turns):
            # Apply context compression before each API call (skip first turn)
            if turn > 0:
                try:
                    from .context_compression import apply_all_compressions

                    compression_result = await apply_all_compressions(
                        messages,
                        client=self.client,
                        config={
                            'max_tool_result_chars': 4000,
                            'max_messages': 50,
                            'keep_recent': 20,
                            'enable_context_collapse': True,
                            'similarity_threshold': 0.7,
                            'enable_autocompact': True,
                            'max_total_chars': 16000,
                        }
                    )
                    messages = compression_result['messages']
                    logger.debug(f"Turn {turn+1}: Compression applied")
                except Exception as e:
                    logger.warning(f"Compression failed: {e}")

            # Build the chat completion request
            chat_kwargs = {
                "messages": messages,
                "n": 1,
                "temperature": self.temperature,
            }

            if self.tool_schemas:
                chat_kwargs["tools"] = self.tool_schemas

            if self.max_tokens is not None:
                chat_kwargs["max_tokens"] = self.max_tokens

            # Make the API call
            try:
                response = await self.client.chat_completion(**chat_kwargs)
            except Exception as e:
                logger.error("API call failed on turn %d: %s", turn + 1, e)
                return AgentResult(
                    messages=messages,
                    turns_used=turn + 1,
                    finished_naturally=False,
                    reasoning_per_turn=reasoning_per_turn,
                    tool_errors=tool_errors,
                )

            # Check for empty response
            if not response:
                logger.warning("Empty response on turn %d", turn + 1)
                return AgentResult(
                    messages=messages,
                    turns_used=turn + 1,
                    finished_naturally=False,
                    reasoning_per_turn=reasoning_per_turn,
                    tool_errors=tool_errors,
                )

            # Extract response info based on provider
            if self.provider == "anthropic":
                stop_reason, assistant_msg, tool_calls = self._parse_anthropic_response(response)
            else:
                stop_reason, assistant_msg, tool_calls = self._parse_openai_response(response)

            # Extract reasoning
            reasoning = self._extract_reasoning(assistant_msg)
            reasoning_per_turn.append(reasoning)

            # Add assistant message to history
            msg_dict = {
                "role": "assistant",
                "content": self._get_message_content(assistant_msg),
            }
            if reasoning:
                msg_dict["reasoning_content"] = reasoning
            if tool_calls:
                msg_dict["tool_calls"] = [self._tool_call_to_dict(tc) for tc in tool_calls]
            messages.append(msg_dict)

            if tool_calls:
                # Execute each tool call
                for tc in tool_calls:
                    tool_name = self._get_tool_name(tc)
                    tool_args_raw = self._get_tool_arguments(tc)
                    tc_id = self._get_tool_call_id(tc)

                    # Validate tool name
                    if tool_name not in self.valid_tool_names:
                        tool_result = json.dumps({
                            "error": f"Unknown tool '{tool_name}'. "
                            f"Available tools: {sorted(self.valid_tool_names)}"
                        })
                        tool_errors.append(ToolError(
                            turn=turn + 1, tool_name=tool_name,
                            arguments=tool_args_raw[:200],
                            error=f"Unknown tool '{tool_name}'",
                            tool_result=tool_result,
                        ))
                        logger.warning("Model called unknown tool '%s' on turn %d", tool_name, turn + 1)
                    else:
                        # Parse arguments
                        try:
                            args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw
                        except json.JSONDecodeError as e:
                            tool_result = json.dumps({
                                "error": f"Invalid JSON in tool arguments: {e}"
                            })
                            tool_errors.append(ToolError(
                                turn=turn + 1, tool_name=tool_name,
                                arguments=tool_args_raw[:200] if isinstance(tool_args_raw, str) else str(tool_args_raw)[:200],
                                error=f"Invalid JSON: {e}",
                                tool_result=tool_result,
                            ))
                            args = None

                        # Execute tool
                        if args is not None:
                            try:
                                from tools.model_tools import handle_function_call
                                tool_result = handle_function_call(
                                    tool_name, args, task_id=self.task_id
                                )
                            except Exception as e:
                                tool_result = json.dumps({
                                    "error": f"Tool execution failed: {type(e).__name__}: {str(e)}"
                                })
                                tool_errors.append(ToolError(
                                    turn=turn + 1, tool_name=tool_name,
                                    arguments=str(tool_args_raw)[:200],
                                    error=f"{type(e).__name__}: {str(e)}",
                                    tool_result=tool_result,
                                ))
                                logger.error("Tool '%s' execution failed on turn %d: %s", tool_name, turn + 1, e)

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": tool_result,
                    })

                logger.info("[%s] turn %d: %d tools executed",
                           self.task_id[:8], turn + 1, len(tool_calls))

            else:
                # No tool calls - model is done
                logger.info("[%s] turn %d: no tools (finished)", self.task_id[:8], turn + 1)

                return AgentResult(
                    messages=messages,
                    turns_used=turn + 1,
                    finished_naturally=True,
                    reasoning_per_turn=reasoning_per_turn,
                    tool_errors=tool_errors,
                )

        # Hit max turns
        logger.info("Agent hit max_turns (%d) without finishing", self.max_turns)
        return AgentResult(
            messages=messages,
            turns_used=self.max_turns,
            finished_naturally=False,
            reasoning_per_turn=reasoning_per_turn,
            tool_errors=tool_errors,
        )

    def _parse_anthropic_response(self, response):
        """Parse Anthropic API response."""
        stop_reason = getattr(response, 'stop_reason', 'end_turn')

        tool_calls = []
        content_text = ""

        for block in response.content:
            # Support both dict and object formats
            if isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "text":
                    content_text = block.get("text", '') or ''
                elif block_type == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ''),
                            "arguments": json.dumps(block.get("input", {}))
                        }
                    })
            elif hasattr(block, 'type'):
                if block.type == "text":
                    content_text = getattr(block, 'text', '') or ''
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": getattr(block, 'id', f"call_{uuid.uuid4().hex[:8]}"),
                        "type": "function",
                        "function": {
                            "name": getattr(block, 'name', ''),
                            "arguments": json.dumps(getattr(block, 'input', {}))
                        }
                    })

        class AssistantMsg:
            def __init__(self, content, reasoning=None):
                self.content = content
                self.reasoning_content = reasoning

        return stop_reason, AssistantMsg(content_text), tool_calls

    def _parse_openai_response(self, response):
        """Parse OpenAI API response."""
        if not hasattr(response, 'choices') or not response.choices:
            return "end_turn", None, []

        assistant_msg = response.choices[0].message

        tool_calls = []
        if hasattr(assistant_msg, 'tool_calls') and assistant_msg.tool_calls:
            for tc in assistant_msg.tool_calls:
                if hasattr(tc, 'function'):
                    tool_calls.append({
                        "id": tc.id if hasattr(tc, 'id') else f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments if hasattr(tc.function, 'arguments') else "{}"
                        }
                    })

        return "end_turn", assistant_msg, tool_calls

    def _extract_reasoning(self, message) -> Optional[str]:
        """Extract reasoning content from a ChatCompletion message."""
        if message is None:
            return None
        if hasattr(message, "reasoning") and message.reasoning:
            return message.reasoning
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            return message.reasoning_content
        if isinstance(message, dict) and message.get("reasoning_content"):
            return message.get("reasoning_content")
        return None

    def _get_message_content(self, message) -> str:
        """Get content from message (handles both object and dict formats)."""
        if message is None:
            return ""
        if hasattr(message, 'content'):
            return message.content or ""
        if isinstance(message, dict):
            return message.get('content', "")
        return ""

    def _get_tool_name(self, tool_call) -> str:
        """Get tool name from tool call (handles both object and dict formats)."""
        if hasattr(tool_call, 'function'):
            return tool_call.function.name
        if isinstance(tool_call, dict):
            return tool_call.get('function', {}).get('name', "")
        return ""

    def _get_tool_arguments(self, tool_call) -> str:
        """Get tool arguments from tool call (handles both object and dict formats)."""
        if hasattr(tool_call, 'function'):
            args = tool_call.function.arguments
            if isinstance(args, str):
                return args
            return json.dumps(args)
        if isinstance(tool_call, dict):
            args = tool_call.get('function', {}).get('arguments', "{}")
            if isinstance(args, str):
                return args
            return json.dumps(args)
        return "{}"

    def _get_tool_call_id(self, tool_call) -> str:
        """Get tool call ID (handles both object and dict formats)."""
        if hasattr(tool_call, 'id'):
            return tool_call.id
        if isinstance(tool_call, dict):
            return tool_call.get('id', f"call_{uuid.uuid4().hex[:8]}")
        return f"call_{uuid.uuid4().hex[:8]}"

    def _tool_call_to_dict(self, tc) -> Dict[str, Any]:
        """Convert tool call to dict format."""
        if isinstance(tc, dict):
            return {
                "id": tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                "type": tc.get("type", "function"),
                "function": {
                    "name": tc.get("function", {}).get("name", ""),
                    "arguments": tc.get("function", {}).get("arguments", "{}"),
                },
            }
        return {
            "id": tc.id if hasattr(tc, 'id') else f"call_{uuid.uuid4().hex[:8]}",
            "type": "function",
            "function": {
                "name": tc.function.name if hasattr(tc, 'function') else "",
                "arguments": tc.function.arguments if hasattr(tc, 'function') else "{}",
            },
        }


def create_agent_loop(toolsets: Optional[List[str]] = None) -> HaonerAgentLoop:
    """Create an Agent Loop with the specified toolsets."""
    from agent.llm_factory import UnifiedLLMClient
    from tools.model_tools import get_tool_definitions

    provider = get_provider()

    if provider == "anthropic":
        from agent.anthropic_client import AnthropicClient
        client = AnthropicClient()
    else:
        from agent.llm_client import LLMClient
        client = LLMClient()

    tool_definitions = get_tool_definitions(toolsets)
    valid_tool_names = {tool['function']['name'] for tool in tool_definitions}

    return HaonerAgentLoop(
        client=client,
        tool_schemas=tool_definitions,
        valid_tool_names=valid_tool_names,
        max_turns=30,
        provider=provider,
    )
