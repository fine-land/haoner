"""
LLM Client - Simple client for interacting with OpenAI-compatible APIs.

Supports configuration via .env file:
- API_KEY: API key
- API_BASE: API base URL (default: https://api.deepseek.com/v1)
- MODEL: Model name (default: deepseek-v4-pro)
- MAX_TOKENS: Max tokens (default: 4096)
- TEMPERATURE: Temperature (default: 1.0)
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MockChatCompletionMessage:
    """Mock message object for testing."""
    def __init__(self, content: str = None, tool_calls: List = None):
        self.content = content
        self.tool_calls = tool_calls or []


class MockChoice:
    """Mock choice object for testing."""
    def __init__(self, message: MockChatCompletionMessage):
        self.message = message


class MockChatCompletion:
    """Mock completion response for testing."""
    def __init__(self, message: MockChatCompletionMessage):
        self.choices = [MockChoice(message)]


class MockToolCall:
    """Mock tool call object."""
    def __init__(self, id: str, function_name: str, arguments: str):
        self.id = id
        self.function = type('Function', (), {
            'name': function_name,
            'arguments': arguments
        })()


class LLMClient:
    """Simple LLM client for OpenAI-compatible APIs."""

    def __init__(self):
        self._load_env()
        self._init_client()

    def _load_env(self):
        """Load configuration from .env file."""
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()

        self.api_key = os.environ.get('API_KEY', '')
        self.api_base = os.environ.get('API_BASE', 'https://api.deepseek.com/v1')
        self.model = os.environ.get('MODEL', 'deepseek-v4-pro')
        self.max_tokens = int(os.environ.get('MAX_TOKENS', '4096'))
        self.temperature = float(os.environ.get('TEMPERATURE', '1.0'))
        self.use_mock = os.environ.get('USE_MOCK_LLM', 'false').lower() == 'true'

        logger.info(f"LLM Client initialized - Model: {self.model}, API Base: {self.api_base}, Mock Mode: {self.use_mock}")

    def _init_client(self):
        """Initialize the actual LLM client."""
        if self.use_mock:
            self.client = MockLLMClient()
        else:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base,
                )
            except ImportError:
                logger.warning("openai package not installed, falling back to mock mode")
                self.use_mock = True
                self.client = MockLLMClient()

    async def chat_completion(self, messages: List[Dict], **kwargs) -> Any:
        """Generate chat completion."""
        if self.use_mock:
            return await self.client.chat_completion(messages, **kwargs)

        params = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.temperature),
            "max_tokens": kwargs.get('max_tokens', self.max_tokens),
            "n": kwargs.get('n', 1),
        }

        if 'tools' in kwargs:
            params['tools'] = kwargs['tools']
            params['tool_choice'] = kwargs.get('tool_choice', 'auto')

        try:
            response = await self.client.chat.completions.create(**params)
            return response
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return await MockLLMClient().chat_completion(messages, **kwargs)

    @property
    def chat(self):
        """Return chat completion interface."""
        return self


class MockLLMClient:
    """Mock LLM client for testing without real API."""

    def __init__(self):
        self.turn = 0

    async def chat_completion(self, messages: List[Dict], **kwargs) -> MockChatCompletion:
        """Generate mock chat completion."""
        self.turn += 1

        tools = kwargs.get('tools', [])
        available_tools = [t['function']['name'] for t in tools] if tools else []

        user_message = ""
        last_tool_result = None

        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', "")
                break
            if msg.get('role') == 'tool':
                last_tool_result = msg.get('content', "")

        if last_tool_result:
            summary = f"I've received the tool result:\n\n{last_tool_result}\n\nThis completes the task."
            return MockChatCompletion(MockChatCompletionMessage(content=summary))

        user_lower = user_message.lower()
        if any(keyword in user_lower for keyword in ['run', 'execute', 'bash', 'shell', 'command', 'terminal']) and 'terminal' in available_tools:
            command = user_message
            import re
            patterns = [
                r'run\s+(.+)',
                r'execute\s+(.+)',
                r'run command:\s*([^\n]+)',
                r'execute command:\s*([^\n]+)',
                r'terminal\s+(.+)',
                r'shell\s+(.+)',
            ]

            extracted_command = None
            for pattern in patterns:
                match = re.search(pattern, user_message, re.IGNORECASE)
                if match:
                    extracted_command = match.group(1).strip()
                    break

            if not extracted_command:
                match = re.search(r'"([^"]+)"', user_message)
                if match:
                    extracted_command = match.group(1)
                else:
                    match = re.search(r"'([^']+)'", user_message)
                    if match:
                        extracted_command = match.group(1)

            command = extracted_command if extracted_command else "echo 'Hello from mock terminal!'"

            tool_call = MockToolCall(
                id=f"call_{self.turn}",
                function_name="terminal",
                arguments=json.dumps({"command": command})
            )

            return MockChatCompletion(
                MockChatCompletionMessage(
                    content="I'll execute the command for you.",
                    tool_calls=[tool_call]
                )
            )

        content = f"Hello! This is a mock response. You said: '{user_message}'\n\n"
        if available_tools:
            content += f"Available tools: {available_tools}\n"
            content += "I can execute shell commands if you ask me to 'run', 'execute', or use 'terminal'."

        return MockChatCompletion(MockChatCompletionMessage(content=content))


_client = None

def get_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
