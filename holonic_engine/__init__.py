"""
HolonicEngine - A library for building AI agent systems.

Core abstractions:
- Holon: A pure architectural context capsule (Purpose, Self, Actions)
- HolonicObject: A Holon extended with hierarchy and messaging
"""

__version__ = "0.1.0"
__author__ = "NullCoward"

from .action import ActionParameter, ActionSignature, HolonAction
from .agent import (
    HolonicObject,
    Message,
    MessageHistory,
)
from .client import ExecutionResult
from .heart import Heartbeat, HolonicObjectHeartbeatRecord, HolonicHeart
from .containers import HolonActions, HolonBinding, HolonPurpose, HolonSelf
from .converter import HolonConverter, holon_converter
from .holon import Holon
from .serialization import (
    estimate_token_savings,
    parse_ai_response,
    serialize_for_ai,
)
from .tokens import TokenCounter, count_tokens, is_available as tokens_available
from .logging import configure_logging, get_logger, logger as holonic_logger
from .telemetry import HolonicTelemetry, get_telemetry, reset_telemetry, Timer

# Storage is optional (requires sqlalchemy)
try:
    from .storage import HolonicStorage, SQLStorage
    _storage_available = True
except ImportError:
    _storage_available = False

__all__ = [
    # Core
    "Holon",
    "HolonicObject",
    "Message",
    "MessageHistory",
    "ExecutionResult",
    # Heartbeat
    "HolonicHeart",
    "Heartbeat",
    "HolonicObjectHeartbeatRecord",
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
    # Logging
    "configure_logging",
    "get_logger",
    "holonic_logger",
    # Telemetry
    "HolonicTelemetry",
    "get_telemetry",
    "reset_telemetry",
    "Timer",
]

# Add storage exports if available
if _storage_available:
    __all__.extend([
        "HolonicStorage",
        "SQLStorage",
    ])
