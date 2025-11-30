"""
Serialization utilities for Holon - JSON and TOON format support.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .holon import Holon

from .converter import holon_converter

# Try to import toon-python, gracefully degrade if not available
try:
    import toon
    TOON_AVAILABLE = True
except ImportError:
    TOON_AVAILABLE = False


def serialize_for_ai(holon: Holon, *, format: str = "toon") -> str:
    """
    Serialize a Holon for AI consumption.

    Args:
        holon: The Holon to serialize
        format: Output format - "json" or "toon"

    Returns:
        Serialized string ready for AI input
    """
    data = holon_converter.unstructure_holon(holon)

    if format == "toon":
        if TOON_AVAILABLE:
            return toon.encode(data)
        else:
            # Fallback to JSON if TOON not available
            return json.dumps(data, indent=2)
    elif format == "json":
        return json.dumps(data, indent=2)
    else:
        raise ValueError(f"Unknown format: {format}. Use 'json' or 'toon'.")


def parse_ai_response(response: str | dict) -> list[dict]:
    """
    Parse an AI response containing action calls.

    Expected format:
    {
        "actions": [
            {"action": "action.name", "params": {...}},
            ...
        ]
    }

    Or a single action:
    {"action": "action.name", "params": {...}}

    Args:
        response: JSON string or dict from AI

    Returns:
        List of action call dictionaries
    """
    if isinstance(response, str):
        data = json.loads(response)
    else:
        data = response

    # Handle list of actions
    if "actions" in data:
        return data["actions"]

    # Handle single action
    if "action" in data:
        return [data]

    raise ValueError(
        "Invalid AI response format. Expected 'actions' list or single 'action'."
    )


def estimate_token_savings(holon: Holon) -> dict[str, Any]:
    """
    Estimate token savings when using TOON vs JSON.

    Requires toon-python package.

    Returns:
        Dictionary with format comparison stats
    """
    if not TOON_AVAILABLE:
        raise ImportError(
            "Token estimation requires the 'python-toon' package. "
            "Install with: pip install python-toon"
        )

    data = holon_converter.unstructure_holon(holon)
    return toon.compare_formats(data)
