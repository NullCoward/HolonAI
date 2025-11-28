"""
Cattrs converter for Holon serialization.

This module provides custom converters for serializing Holon objects
to JSON-compatible dictionaries using cattrs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import cattrs

if TYPE_CHECKING:
    from .holon import Holon

from .action import ActionParameter, ActionSignature, HolonAction
from .containers import HolonActions, HolonPurpose, HolonSelf


class HolonConverter:
    """
    Custom cattrs converter for Holon objects.

    Handles the special serialization rules:
    - Purpose/Self: list if unkeyed, dict if keyed
    - Actions: list with full metadata
    - Nested Holons: inline without redundant framing
    """

    def __init__(self):
        self._converter = cattrs.Converter()
        self._register_hooks()

    def _register_hooks(self):
        """Register custom unstructure hooks."""
        # ActionParameter: clean dict without internal flags
        self._converter.register_unstructure_hook(
            ActionParameter,
            self._unstructure_action_parameter
        )

        # ActionSignature: parameters list + metadata
        self._converter.register_unstructure_hook(
            ActionSignature,
            self._unstructure_action_signature
        )

        # HolonAction: name, purpose, parameters, docstring
        self._converter.register_unstructure_hook(
            HolonAction,
            self._unstructure_holon_action
        )

    def _unstructure_action_parameter(self, param: ActionParameter) -> dict[str, Any]:
        """Convert ActionParameter to dict for AI consumption."""
        result = {"name": param.name}
        if param.type_hint:
            result["type"] = param.type_hint
        if param.has_default:
            result["default"] = param.default
        return result

    def _unstructure_action_signature(self, sig: ActionSignature) -> dict[str, Any]:
        """Convert ActionSignature to dict."""
        result = {
            "parameters": [
                self._unstructure_action_parameter(p)
                for p in sig.parameters
            ]
        }
        if sig.return_type:
            result["returns"] = sig.return_type
        if sig.docstring:
            result["docstring"] = sig.docstring
        return result

    def _unstructure_holon_action(self, action: HolonAction) -> dict[str, Any]:
        """Convert HolonAction to dict for AI consumption."""
        result = {"name": action.name}

        if action.purpose:
            result["purpose"] = action.purpose

        if action.signature:
            sig_data = self._unstructure_action_signature(action.signature)
            result["parameters"] = sig_data.get("parameters", [])
            if "returns" in sig_data:
                result["returns"] = sig_data["returns"]
            if "docstring" in sig_data:
                result["docstring"] = sig_data["docstring"]

        return result

    def unstructure_holon(self, holon: Holon, *, nested: bool = False) -> dict[str, Any]:
        """
        Convert a Holon to a dictionary.

        Args:
            holon: The Holon to convert
            nested: If True, omit the name (nested Holons don't need it)
        """
        result = {}

        if holon.name and not nested:
            result["name"] = holon.name

        # Purpose: smart serialize (list or dict)
        purpose_data = holon.purpose.serialize()
        if purpose_data:
            result["purpose"] = purpose_data

        # Self: smart serialize (list or dict, handles nested Holons)
        self_data = holon.self_state.serialize()
        if self_data:
            result["self"] = self_data

        # Actions: always a list
        if len(holon.actions) > 0:
            result["actions"] = [
                self._unstructure_holon_action(action)
                for action in holon.actions
            ]

        return result

    def unstructure(self, obj: Any) -> Any:
        """Generic unstructure using cattrs."""
        return self._converter.unstructure(obj)

    def structure(self, data: Any, cls: type) -> Any:
        """Generic structure using cattrs."""
        return self._converter.structure(data, cls)


# Global converter instance
holon_converter = HolonConverter()
