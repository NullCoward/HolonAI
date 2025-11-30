"""
Holon - The core object that combines Purpose, Self, and Actions.
"""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

import attrs

from .action import HolonAction
from .containers import HolonActions, HolonPurpose, HolonSelf

if TYPE_CHECKING:
    from .client import ExecutionResult


@attrs.define
class Holon:
    """
    A portable AI context capsule.

    Combines three components:
    - Purpose: The interpretive lens (HOW to interpret)
    - Self: The current state/context (WHAT to interpret)
    - Actions: Available responses (WHAT can be done)

    Holons can be nested - a Holon's Self can contain other Holons,
    creating hierarchical structures that flatten during serialization.

    Token Management:
    - token_limit: Maximum tokens allowed for this Holon's serialization
    - model: Model name for token counting (affects encoding used)
    - token_count: Current token count (dynamic property)

    Execution:
    - Use with_client() to configure an AI client (OpenAI or Anthropic)
    - Use execute() to run the full pipeline: serialize -> AI call -> dispatch
    """
    name: str | None = None
    purpose: HolonPurpose = attrs.Factory(HolonPurpose)
    self_state: HolonSelf = attrs.Factory(HolonSelf)
    actions: HolonActions = attrs.Factory(HolonActions)

    # Token management
    token_limit: int | None = None
    model: str | None = None  # e.g., "gpt-4o", "gpt-4", "claude-sonnet-4-20250514"

    # AI client for execution
    _client: Any = attrs.field(default=None, alias="_client")
    _max_tokens: int = attrs.field(default=4096, alias="_max_tokens")

    # Fluent API for building Holons

    def add_purpose(
        self,
        item: Any,
        *,
        key: str | None = None
    ) -> Holon:
        """Add an item to this Holon's purpose."""
        self.purpose.add(item, key=key)
        return self

    def add_self(
        self,
        item: Any,
        *,
        key: str | None = None
    ) -> Holon:
        """Add an item to this Holon's self state."""
        self.self_state.add(item, key=key)
        return self

    def add_action(
        self,
        action: HolonAction | Callable,
        *,
        name: str | None = None,
        purpose: str | None = None
    ) -> Holon:
        """Add an action to this Holon."""
        self.actions.add(action, name=name, purpose=purpose)
        return self

    def with_token_limit(self, limit: int, model: str | None = None) -> Holon:
        """Set token limit (fluent API)."""
        self.token_limit = limit
        if model:
            self.model = model
        return self

    def with_client(
        self,
        client: Any,
        *,
        model: str,
        max_tokens: int = 4096
    ) -> Holon:
        """
        Configure an AI client for execution (fluent API).

        Supports OpenAI and Anthropic clients directly.

        Args:
            client: An OpenAI or Anthropic client instance
            model: Model to use (e.g., "gpt-4o", "claude-sonnet-4-20250514")
            max_tokens: Maximum tokens in AI response

        Example:
            from openai import OpenAI

            holon = (
                Holon(name="Assistant")
                .with_client(OpenAI(), model="gpt-4o")
                .add_purpose("You are a helpful assistant")
                .add_action(my_action, name="do_thing")
            )
        """
        from .client import detect_client_type

        client_type = detect_client_type(client)
        if client_type is None:
            raise TypeError(
                f"Unsupported client type: {type(client).__name__}. "
                "Supported clients: OpenAI, Anthropic"
            )

        self._client = client
        self.model = model
        self._max_tokens = max_tokens
        return self

    # Token counting properties

    @property
    def token_count(self) -> int:
        """
        Current token count for the serialized Holon.

        Requires tiktoken: pip install tiktoken
        """
        from .tokens import TokenCounter, TIKTOKEN_AVAILABLE

        if not TIKTOKEN_AVAILABLE:
            raise ImportError(
                "Token counting requires the 'tiktoken' package. "
                "Install with: pip install tiktoken"
            )

        data = self.to_dict()
        return TokenCounter.count_json(data, model=self.model)

    @property
    def tokens_remaining(self) -> int | None:
        """
        Tokens remaining before hitting limit.

        Returns None if no limit is set.
        """
        if self.token_limit is None:
            return None
        return self.token_limit - self.token_count

    @property
    def is_over_limit(self) -> bool:
        """
        Check if current token count exceeds the limit.

        Returns False if no limit is set.
        """
        if self.token_limit is None:
            return False
        return self.token_count > self.token_limit

    @property
    def token_usage(self) -> dict[str, Any]:
        """
        Get detailed token usage information.

        Returns dict with count, limit, remaining, over_limit, and percentage.
        """
        count = self.token_count
        result = {
            "count": count,
            "limit": self.token_limit,
            "model": self.model,
        }

        if self.token_limit is not None:
            result["remaining"] = self.token_limit - count
            result["over_limit"] = count > self.token_limit
            result["percentage"] = round((count / self.token_limit) * 100, 1)
        else:
            result["remaining"] = None
            result["over_limit"] = False
            result["percentage"] = None

        return result

    # Serialization

    def to_dict(self, *, nested: bool = False) -> dict[str, Any]:
        """
        Serialize the Holon to a dictionary.

        Args:
            nested: If True, this is a nested Holon (no intro text needed)
        """
        # Use the converter for serialization
        from .converter import holon_converter
        return holon_converter.unstructure_holon(self, nested=nested)

    def to_json(self, **kwargs) -> str:
        """Serialize to JSON string."""
        import json
        return json.dumps(self.to_dict(), **kwargs)

    # Action dispatch

    def dispatch(self, action_name: str, **kwargs) -> Any:
        """Dispatch an action by name."""
        return self.actions.execute(action_name, **kwargs)

    def dispatch_many(self, action_calls: list[dict]) -> list[Any]:
        """
        Dispatch multiple action calls (from AI response).

        Args:
            action_calls: List of {"action": "name", "params": {...}} dicts
        """
        results = []
        for call in action_calls:
            action_name = call.get("action")
            params = call.get("params", {})
            result = self.dispatch(action_name, **params)
            results.append(result)
        return results

    # Execution

    def execute(self, user_message: str | None = None) -> "ExecutionResult":
        """
        Execute the full AI interaction pipeline.

        1. Serialize the Holon (resolves all dynamic bindings)
        2. Append user message if provided
        3. Send to configured AI client
        4. Parse the AI response for action calls
        5. Dispatch all actions
        6. Return results

        Args:
            user_message: Optional message from user to append to prompt

        Returns:
            ExecutionResult with prompt, response, actions, and results

        Raises:
            RuntimeError: If no client configured (use with_client first)

        Example:
            result = holon.execute("Create a new task called 'Review PR'")
            print(result.results)  # Results from executed actions
        """
        from .client import ExecutionResult, call_ai
        from .serialization import parse_ai_response, serialize_for_ai

        if self._client is None:
            raise RuntimeError(
                "No AI client configured. Use with_client() first. "
                "Example: holon.with_client(OpenAI(), model='gpt-4o')"
            )

        # Serialize (resolves dynamic bindings)
        prompt = serialize_for_ai(self)

        # Append user message if provided
        if user_message:
            prompt = f"{prompt}\n\nUser: {user_message}"

        # Call AI
        ai_response = call_ai(
            self._client,
            prompt,
            model=self.model,
            max_tokens=self._max_tokens
        )

        # Parse and dispatch
        try:
            actions_called = parse_ai_response(ai_response)
        except (ValueError, Exception):
            # AI didn't return valid action format
            actions_called = []

        results = self.dispatch_many(actions_called) if actions_called else []

        return ExecutionResult(
            prompt=prompt,
            ai_response=ai_response,
            actions_called=actions_called,
            results=results
        )
