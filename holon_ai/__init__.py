"""
HolonAI - A library for building AI agent systems.

A Holon is a portable AI context capsule that combines:
- Purpose: The interpretive lens (HOW to interpret)
- Self: The current state/context (WHAT to interpret)
- Actions: Available responses (WHAT can be done)
"""

__version__ = "0.1.0"
__author__ = "NullCoward"

from .action import ActionParameter, ActionSignature, HolonAction
from .containers import HolonActions, HolonBinding, HolonPurpose, HolonSelf
from .converter import HolonConverter, holon_converter
from .holon import Holon
from .serialization import (
    estimate_token_savings,
    parse_ai_response,
    serialize_for_ai,
)
from .tokens import TokenCounter, count_tokens, is_available as tokens_available

__all__ = [
    # Core
    "Holon",
    # Containers
    "HolonPurpose",
    "HolonSelf",
    "HolonActions",
    "HolonBinding",
    # Actions
    "HolonAction",
    "ActionParameter",
    "ActionSignature",
    # Converter
    "HolonConverter",
    "holon_converter",
    # Serialization
    "serialize_for_ai",
    "parse_ai_response",
    "estimate_token_savings",
    # Tokens
    "TokenCounter",
    "count_tokens",
    "tokens_available",
]
