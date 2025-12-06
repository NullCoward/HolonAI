"""
Holon - The core architectural object that combines Purpose, Self, and Actions.

A Holon is a pure data structure representing an AI context capsule.
It contains no execution logic or token management - those concerns
belong to the HolonicAgent that wraps it.
"""

from __future__ import annotations

from typing import Any, Callable

import attrs

from .action import HolonAction
from .containers import HolonActions, HolonPurpose, HolonSelf


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

    This is a pure architectural object with no execution logic.
    For AI execution and token management, see HolonicAgent.
    """
    purpose: HolonPurpose = attrs.Factory(HolonPurpose)
    self_state: HolonSelf = attrs.Factory(HolonSelf)
    actions: HolonActions = attrs.Factory(HolonActions)

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

    # Serialization

    def to_dict(self) -> dict[str, Any]:
        """Serialize the Holon to a dictionary."""
        from .converter import holon_converter
        return holon_converter.unstructure_holon(self)

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
