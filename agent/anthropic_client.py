"""
Anthropic LLM Client - Client for interacting with Anthropic Claude API.

Supports tool use with tool_use as termination signal.
Configuration via .env:
- ANTHROPIC_API_KEY: Anthropic API key
- ANTHROPIC_API_BASE: API base URL (default: https://api.anthropic.com)
- MODEL: Model name (default: claude-sonnet-4-20250514)
- MAX_TOKENS: Max tokens (default: 8192)
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnthropicMessage:
    """Represents a message in Anthropic format."""
    def __init__(self, role: str, content: Any):
        self.role = role
        self.content = content


class AnthropicToolUse:
    """Represents a tool use block in Anthropic response."""
    def __init__(self, name: str, input_json: str, id: str):
        self.name = name
        self.input = input_json
        self.id = id
        self.type = "tool_use"


class AnthropicToolResult:
    """Represents a tool result block."""
    def __init__(self, tool_use_id: str, content: str):
        self.tool_use_id = tool_use_id
        self.content = content
        self.type = "tool_result"


class AnthropicResponse:
    """Wrapper for Anthropic API response to match expected interface."""
    def __init__(self, response_data: Dict[str, Any]):
        self.response = response_data
        self.content = response_data.get("content", [])
        self.stop_reason = response_data.get("stop_reason", "")
        self.usage = response_data.get("usage", {})

    @property
    def choices(self):
        """Return choices in OpenAI-like format for compatibility."""
        content_text = ""
        tool_calls = []

        for block in self.content:
            if block.get("type") == "text":
                content_text = block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {}))
                    }
                })

        class Choice:
            def __init__(self, msg):
                self.message = msg

        class Message:
            def __init__(self, text, calls):
                self.content = text
                self.tool_calls = calls

        return [Choice(Message(content_text, tool_calls))]


class AnthropicClient:
    """Client for Anthropic Claude API with tool use support."""

    def __init__(self):
        self._load_env()
        self._init_client()

    def _load_env(self):
        """Load configuration from .env file."""
        from .env_utils import load_env
        load_env()

        self.api_key = os.environ.get('ANTHROPIC_API_KEY', os.environ.get('API_KEY', ''))
        self.api_base = os.environ.get('ANTHROPIC_API_BASE', os.environ.get('API_BASE', 'https://api.anthropic.com'))
        self.model = os.environ.get('ANTHROPIC_MODEL', os.environ.get('MODEL', 'claude-sonnet-4-20250514'))
        self.max_tokens = int(os.environ.get('ANTHROPIC_MAX_TOKENS', os.environ.get('MAX_TOKENS', '8192')))
        self.temperature = float(os.environ.get('TEMPERATURE', '1.0'))

        use_mock = os.environ.get('USE_ANTHROPIC_MOCK', 'false').lower() == 'true'
        logger.info(f"Anthropic Client initialized - Model: {self.model}, API Base: {self.api_base}, Mock Mode: {use_mock}")

    def _init_client(self):
        """Initialize the Anthropic client."""
        use_mock = os.environ.get('USE_ANTHROPIC_MOCK', 'false').lower() == 'true'

        if use_mock:
            self.client = None
            self._is_mock = True
            return

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key, base_url=self.api_base)
            self._is_mock = False
        except ImportError:
            logger.warning("anthropic package not installed")
            self.client = None
            self._is_mock = True

    def _convert_tools_to_anthropic_format(self, tools: List[Dict[str, Any]]) -> List[Dict]:
        """Convert OpenAI-spec tools to Anthropic format."""
        anthropic_tools = []
        for tool in tools:
            func = tool.get("function", {})
            anthropic_tools.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}})
            })
        return anthropic_tools

    def _convert_messages_to_anthropic_format(self, messages: List[Dict[str, Any]]) -> List[Dict]:
        """Convert messages to Anthropic format."""
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                continue

            if role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id", ""),
                            "content": content
                        }
                    ]
                })
            elif role == "assistant":
                if isinstance(content, str):
                    anthropic_messages.append({
                        "role": "assistant",
                        "content": content
                    })
            else:
                if isinstance(content, str):
                    anthropic_messages.append({
                        "role": "user",
                        "content": content
                    })
        return anthropic_messages

    async def chat_completion(self, messages: List[Dict], **kwargs) -> AnthropicResponse:
        """Generate chat completion using Anthropic API."""
        if self._is_mock or not self.client:
            return await self._mock_completion(messages, **kwargs)

        tools = kwargs.get('tools', [])
        anthropic_tools = self._convert_tools_to_anthropic_format(tools)
        anthropic_messages = self._convert_messages_to_anthropic_format(messages)

        system_prompt = ""
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
                break

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                system=system_prompt if system_prompt else None,
                messages=anthropic_messages,
                tools=anthropic_tools if anthropic_tools else None,
            )

            response_data = {
                "content": [],
                "stop_reason": response.stop_reason,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }
            }

            for block in response.content:
                if hasattr(block, 'type'):
                    response_data["content"].append({
                        "type": block.type,
                        "text": getattr(block, 'text', None) or "",
                        "name": getattr(block, 'name', None) or "",
                        "input": getattr(block, 'input', None) or {},
                        "id": getattr(block, 'id', None) or "",
                    })
                elif isinstance(block, dict):
                    response_data["content"].append({
                        "type": block.get('type', ''),
                        "text": block.get('text', ""),
                        "name": block.get('name', ""),
                        "input": block.get('input', {}),
                        "id": block.get('id', ""),
                    })

            logger.info(f"Anthropic API response - stop_reason: {response.stop_reason}")
            return AnthropicResponse(response_data)

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return await self._mock_completion(messages, **kwargs)

    async def _mock_completion(self, messages: List[Dict], **kwargs) -> AnthropicResponse:
        """Mock completion for testing."""
        user_message = ""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break

        tools = kwargs.get('tools', [])
        available_tools = [t.get('function', {}).get('name', '') for t in tools] if tools else []

        response_data = {
            "content": [{"type": "text", "text": f"Mock response to: {user_message}"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 100, "output_tokens": 50}
        }

        user_lower = user_message.lower()
        if any(kw in user_lower for kw in ['run', 'execute', 'terminal', 'command']) and 'terminal' in available_tools:
            response_data = {
                "content": [
                    {"type": "text", "text": "I'll execute that command for you."},
                    {
                        "type": "tool_use",
                        "name": "terminal",
                        "input": {"command": user_message},
                        "id": "mock_tool_call_1"
                    }
                ],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            }

        return AnthropicResponse(response_data)

    @property
    def chat(self):
        """Return chat interface."""
        return self
