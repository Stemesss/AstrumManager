# -*- coding: utf-8 -*-
"""Abstract base class for AI model providers.

Defines the interface for different AI backends:
- OpenAI (ChatGPT)
- Anthropic (Claude)
- Ollama (local LLMs)
- Google (Gemini)
- Custom implementations

This abstraction ensures the AI system remains model-agnostic.
New providers can be added without modifying AIService or handlers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AIProvider(ABC):
    """
    Abstract base class for AI model providers.

    Each provider implementation handles:
    1. Authentication/initialization
    2. Tokenization
    3. Model inference
    4. Token counting
    5. Error handling
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider (e.g., 'openai', 'claude', 'ollama')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the current model name (e.g., 'gpt-4', 'claude-3-sonnet')."""
        pass

    @property
    @abstractmethod
    def max_context_tokens(self) -> int:
        """Return maximum context window in tokens."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the provider (auth, connection, validation).

        Called once during bot startup.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Cleanup and shutdown.

        Called during bot shutdown.
        """
        pass

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate response using the model.

        Args:
            system_prompt: System-level instructions
            messages: List of {"role": "user"|"assistant", "content": "..."}
            temperature: Creativity level (0.0-1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific options

        Returns:
            {
                "response": str,              # Generated text
                "tokens_used": int,           # Total tokens in conversation
                "model": str,                 # Model name
                "provider": str,              # Provider name
                "raw_response": Any,          # Raw API response (for debugging)
            }

        Raises:
            RuntimeError: If provider not initialized
            Exception: If API call fails
        """
        pass

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (for context window management).

        Args:
            text: Text to count

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if provider is available and working.

        Useful for health checks.
        """
        pass


class NoOpProvider(AIProvider):
    """
    No-operation provider for development/testing.

    Returns placeholder responses without calling any API.
    Useful for testing the AI system architecture without external dependencies.
    """

    @property
    def provider_name(self) -> str:
        return "noop"

    @property
    def model_name(self) -> str:
        return "noop-model-v1"

    @property
    def max_context_tokens(self) -> int:
        return 4096

    async def initialize(self) -> None:
        """No initialization needed."""
        pass

    async def shutdown(self) -> None:
        """No cleanup needed."""
        pass

    async def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Return a placeholder response."""
        response_text = (
            f"[NoOp Response] System: {system_prompt[:50]}... "
            f"Messages: {len(messages)} "
            f"Temperature: {temperature}"
        )
        return {
            "response": response_text,
            "tokens_used": 100,
            "model": self.model_name,
            "provider": self.provider_name,
            "raw_response": None,
        }

    async def count_tokens(self, text: str) -> int:
        """Rough estimate: 1 token ≈ 4 characters."""
        return len(text) // 4

    async def is_available(self) -> bool:
        """Always available."""
        return True
