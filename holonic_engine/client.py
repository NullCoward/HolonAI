"""
AI Client integration for Holon execution.

Supports direct integration with known AI SDKs:
- OpenAI (openai package)
- Anthropic (anthropic package)

OpenAI Structured Outputs:
When enabled, uses response_format with json_schema to guarantee
valid action responses. This provides:
- 100% valid JSON (no parsing errors)
- Schema compliance (correct structure)
- Potentially better performance (no retries, no wasted tokens)
"""

from __future__ import annotations

from typing import Any

import attrs


# JSON Schema for Holon action responses
# Matches the format expected by parse_ai_response()
ACTION_RESPONSE_SCHEMA = {
    "name": "holon_action_response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "description": "List of actions to execute",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "The name of the action to call"
                        },
                        "params": {
                            "type": "object",
                            "description": "Parameters to pass to the action",
                            "additionalProperties": True
                        }
                    },
                    "required": ["action"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["actions"],
        "additionalProperties": False
    }
}


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


def _call_openai(
    client: Any,
    prompt: str,
    model: str,
    max_tokens: int,
    structured_output: bool = False
) -> str:
    """
    Execute a completion using OpenAI client.

    Args:
        client: OpenAI client instance
        prompt: The prompt to send
        model: Model identifier
        max_tokens: Maximum tokens in response
        structured_output: If True, use response_format with ACTION_RESPONSE_SCHEMA
                          to guarantee valid JSON action responses
    """
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }

    if structured_output:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": ACTION_RESPONSE_SCHEMA
        }

    response = client.chat.completions.create(**kwargs)
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
    max_tokens: int = 4096,
    structured_output: bool = False
) -> str:
    """
    Call the AI using the appropriate SDK method.

    Args:
        client: OpenAI or Anthropic client instance
        prompt: The prompt to send
        model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-20250514")
        max_tokens: Maximum tokens in response
        structured_output: If True and using OpenAI, use response_format
                          to guarantee valid JSON action responses

    Returns:
        The AI's response text

    Raises:
        TypeError: If client type is not supported
    """
    client_type = detect_client_type(client)

    if client_type == "openai":
        return _call_openai(client, prompt, model, max_tokens, structured_output)
    elif client_type == "anthropic":
        # Note: Anthropic doesn't support structured outputs the same way
        # Falls back to prompt-based JSON formatting
        return _call_anthropic(client, prompt, model, max_tokens)
    else:
        raise TypeError(
            f"Unsupported client type: {type(client).__name__}. "
            "Supported clients: OpenAI, Anthropic"
        )


def create_openai_client(api_key: str | None = None) -> Any:
    """
    Create an OpenAI client for internal use.

    Args:
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY environment variable.

    Returns:
        OpenAI client instance

    Raises:
        ImportError: If openai package is not installed
        ValueError: If no API key provided or found in environment
    """
    import os

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "OpenAI package not installed. Install with: pip install openai"
        )

    # Use provided key or fall back to environment variable
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "No OpenAI API key provided. Either pass api_key parameter "
            "or set OPENAI_API_KEY environment variable."
        )

    return OpenAI(api_key=key)
