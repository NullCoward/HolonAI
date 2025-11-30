"""
AI Client integration for Holon execution.

Supports direct integration with known AI SDKs:
- OpenAI (openai package)
- Anthropic (anthropic package)
"""

from __future__ import annotations

from typing import Any

import attrs


@attrs.define
class ExecutionResult:
    """
    Result of a Holon execution.

    Contains the full execution trace: what was sent, what came back,
    what actions were called, and what they returned.
    """

    prompt: str
    """The serialized prompt that was sent to the AI."""

    ai_response: str
    """The raw response from the AI."""

    actions_called: list[dict[str, Any]]
    """The parsed action calls from the AI response."""

    results: list[Any]
    """The results from executing each action."""

    @property
    def success(self) -> bool:
        """True if execution completed without errors."""
        return not any(isinstance(r, Exception) for r in self.results)

    @property
    def first_result(self) -> Any:
        """Get the first action result, or None if no actions were called."""
        return self.results[0] if self.results else None

    def __iter__(self):
        """Iterate over (action_call, result) pairs."""
        return iter(zip(self.actions_called, self.results))

    def __len__(self):
        """Number of actions executed."""
        return len(self.results)


def _is_openai_client(obj: Any) -> bool:
    """Check if object is an OpenAI client."""
    # Check by class name to avoid import dependency
    cls_name = type(obj).__name__
    module = type(obj).__module__
    return cls_name == "OpenAI" and module.startswith("openai")


def _is_anthropic_client(obj: Any) -> bool:
    """Check if object is an Anthropic client."""
    cls_name = type(obj).__name__
    module = type(obj).__module__
    return cls_name == "Anthropic" and module.startswith("anthropic")


def _call_openai(client: Any, prompt: str, model: str, max_tokens: int) -> str:
    """Execute a completion using OpenAI client."""
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def _call_anthropic(client: Any, prompt: str, model: str, max_tokens: int) -> str:
    """Execute a completion using Anthropic client."""
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def detect_client_type(client: Any) -> str | None:
    """
    Detect the type of AI client.

    Returns:
        "openai", "anthropic", or None if unknown
    """
    if _is_openai_client(client):
        return "openai"
    elif _is_anthropic_client(client):
        return "anthropic"
    return None


def call_ai(
    client: Any,
    prompt: str,
    model: str,
    max_tokens: int = 4096
) -> str:
    """
    Call the AI using the appropriate SDK method.

    Args:
        client: OpenAI or Anthropic client instance
        prompt: The prompt to send
        model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-20250514")
        max_tokens: Maximum tokens in response

    Returns:
        The AI's response text

    Raises:
        TypeError: If client type is not supported
    """
    client_type = detect_client_type(client)

    if client_type == "openai":
        return _call_openai(client, prompt, model, max_tokens)
    elif client_type == "anthropic":
        return _call_anthropic(client, prompt, model, max_tokens)
    else:
        raise TypeError(
            f"Unsupported client type: {type(client).__name__}. "
            "Supported clients: OpenAI, Anthropic"
        )
