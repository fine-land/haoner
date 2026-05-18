"""
LLM Client Factory - Unified interface for multiple LLM providers.

Supports:
- OpenAI (and OpenAI-compatible APIs like DeepSeek)
- Anthropic (Claude API)
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def create_llm_client(provider: str = None) -> Any:
    """
    Create an LLM client based on the specified provider.

    Args:
        provider: "openai" or "anthropic". If None, reads from LLM_PROVIDER env var.

    Returns:
        LLM client instance
    """
    if provider is None:
        provider = os.environ.get('LLM_PROVIDER', 'openai').lower()

    if provider == 'anthropic':
        from .anthropic_client import AnthropicClient
        return AnthropicClient()
    else:
        from .llm_client import LLMClient
        return LLMClient()


class UnifiedLLMClient:
    """
    Unified LLM client that wraps both OpenAI and Anthropic clients.
    Provides consistent interface regardless of the underlying provider.
    """

    def __init__(self, provider: str = None):
        self.provider = provider or os.environ.get('LLM_PROVIDER', 'openai').lower()

        if self.provider == 'anthropic':
            from .anthropic_client import AnthropicClient
            self.client = AnthropicClient()
        else:
            from .llm_client import LLMClient
            self.client = LLMClient()

        logger.info(f"UnifiedLLMClient initialized with provider: {self.provider}")

    async def chat_completion(self, messages: List[Dict], **kwargs) -> Any:
        """Generate chat completion using the underlying client."""
        return await self.client.chat_completion(messages, **kwargs)

    @property
    def chat(self):
        """Return chat interface."""
        return self.client.chat if hasattr(self.client, 'chat') else self.client
