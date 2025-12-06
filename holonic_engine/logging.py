"""
Logging configuration for HolonicEngine.

Provides structured logging with configurable levels and formats.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Create logger hierarchy
logger = logging.getLogger("holonic_engine")
heart_logger = logging.getLogger("holonic_engine.heart")
agent_logger = logging.getLogger("holonic_engine.agent")
action_logger = logging.getLogger("holonic_engine.action")


class HolonicFormatter(logging.Formatter):
    """Custom formatter with ISO timestamps and structured output."""

    def format(self, record: logging.LogRecord) -> str:
        # Add timestamp
        record.iso_time = datetime.now(timezone.utc).isoformat()

        # Add extra context if present
        extras = []
        for key in ['hobj_id', 'heartbeat_time', 'action_name', 'token_count', 'duration_ms']:
            if hasattr(record, key):
                extras.append(f"{key}={getattr(record, key)}")

        if extras:
            record.extras = " [" + ", ".join(extras) + "]"
        else:
            record.extras = ""

        return super().format(record)


def configure_logging(
    level: int = logging.INFO,
    format_string: str | None = None,
    stream: Any = None
) -> None:
    """
    Configure logging for the HolonicEngine.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_string: Custom format string
        stream: Output stream (defaults to stderr)
    """
    if format_string is None:
        format_string = "%(iso_time)s [%(levelname)s] %(name)s: %(message)s%(extras)s"

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(HolonicFormatter(format_string))

    logger.setLevel(level)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger under the holonic_engine namespace."""
    return logging.getLogger(f"holonic_engine.{name}")


# Convenience functions for logging with context
def log_heartbeat_start(heartbeat_time: datetime, hobj_count: int) -> None:
    """Log the start of a heartbeat cycle."""
    heart_logger.info(
        f"Heartbeat started with {hobj_count} hobjs",
        extra={"heartbeat_time": heartbeat_time.isoformat()}
    )


def log_heartbeat_complete(heartbeat_time: datetime, hobj_count: int, duration_ms: float) -> None:
    """Log the completion of a heartbeat cycle."""
    heart_logger.info(
        f"Heartbeat complete, processed {hobj_count} hobjs",
        extra={"heartbeat_time": heartbeat_time.isoformat(), "duration_ms": round(duration_ms, 2)}
    )


def log_token_allocation(hobj_id: str, amount: int, new_balance: int) -> None:
    """Log a token allocation."""
    heart_logger.debug(
        f"Allocated {amount} tokens, new balance: {new_balance}",
        extra={"hobj_id": hobj_id}
    )


def log_action_dispatch(hobj_id: str, action_name: str, params: dict) -> None:
    """Log an action being dispatched."""
    action_logger.debug(
        f"Dispatching action: {action_name}",
        extra={"hobj_id": hobj_id, "action_name": action_name}
    )


def log_action_result(hobj_id: str, action_name: str, success: bool, duration_ms: float) -> None:
    """Log an action result."""
    level = logging.DEBUG if success else logging.WARNING
    action_logger.log(
        level,
        f"Action {'succeeded' if success else 'failed'}: {action_name}",
        extra={"hobj_id": hobj_id, "action_name": action_name, "duration_ms": round(duration_ms, 2)}
    )


def log_hobj_frozen(hobj_id: str, token_bank: int) -> None:
    """Log when an hobj is skipped due to frozen state."""
    agent_logger.debug(
        f"Skipped frozen hobj (token_bank={token_bank})",
        extra={"hobj_id": hobj_id}
    )


def log_ai_call(prompt_tokens: int, model: str) -> None:
    """Log an AI API call."""
    heart_logger.info(
        f"Calling AI model {model}",
        extra={"token_count": prompt_tokens}
    )


def log_ai_response(response_tokens: int, duration_ms: float) -> None:
    """Log an AI API response."""
    heart_logger.info(
        f"AI response received",
        extra={"token_count": response_tokens, "duration_ms": round(duration_ms, 2)}
    )
