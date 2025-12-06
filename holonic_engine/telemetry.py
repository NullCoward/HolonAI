"""
Telemetry and metrics collection for HolonicEngine.

Collects performance metrics, usage statistics, and timing data
for debugging and optimization.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import attrs


@dataclass
class TimingStats:
    """Statistics for a timed operation."""
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0

    def record(self, duration_ms: float) -> None:
        """Record a timing measurement."""
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)

    @property
    def avg_ms(self) -> float:
        """Average duration in milliseconds."""
        return self.total_ms / self.count if self.count > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "count": self.count,
            "total_ms": round(self.total_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.count > 0 else None,
            "max_ms": round(self.max_ms, 2) if self.count > 0 else None,
        }


@dataclass
class CounterStats:
    """Simple counter with total and rate tracking."""
    count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None

    def increment(self, amount: int = 1) -> None:
        """Increment the counter."""
        now = datetime.now(timezone.utc)
        if self.first_seen is None:
            self.first_seen = now
        self.last_seen = now
        self.count += amount

    @property
    def duration_secs(self) -> float:
        """Duration between first and last increment."""
        if self.first_seen is None or self.last_seen is None:
            return 0.0
        return (self.last_seen - self.first_seen).total_seconds()

    @property
    def rate_per_sec(self) -> float:
        """Rate per second."""
        duration = self.duration_secs
        return self.count / duration if duration > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "count": self.count,
            "duration_secs": round(self.duration_secs, 2),
            "rate_per_sec": round(self.rate_per_sec, 4),
        }


@attrs.define
class HolonicTelemetry:
    """
    Telemetry collector for the HolonicEngine.

    Tracks:
    - Heartbeat timing and counts
    - AI API calls and token usage
    - Action dispatch timing
    - Token allocations and flows
    - Error counts
    """

    # Timing stats
    heartbeat_timing: TimingStats = attrs.field(factory=TimingStats)
    ai_call_timing: TimingStats = attrs.field(factory=TimingStats)
    action_timing: dict[str, TimingStats] = attrs.field(factory=lambda: defaultdict(TimingStats))
    serialization_timing: TimingStats = attrs.field(factory=TimingStats)

    # Counters
    heartbeats: CounterStats = attrs.field(factory=CounterStats)
    hobjs_processed: CounterStats = attrs.field(factory=CounterStats)
    actions_dispatched: CounterStats = attrs.field(factory=CounterStats)
    actions_failed: CounterStats = attrs.field(factory=CounterStats)
    tokens_allocated: CounterStats = attrs.field(factory=CounterStats)
    ai_calls: CounterStats = attrs.field(factory=CounterStats)

    # Token tracking
    prompt_tokens_total: int = attrs.field(default=0)
    response_tokens_total: int = attrs.field(default=0)

    # Error tracking
    errors: list[dict[str, Any]] = attrs.field(factory=list)
    _max_errors: int = attrs.field(default=100)

    # Per-hobj stats
    hobj_stats: dict[str, dict[str, Any]] = attrs.field(factory=lambda: defaultdict(lambda: {
        "heartbeats": 0,
        "actions": 0,
        "tokens_received": 0,
        "tokens_spent": 0,
        "errors": 0,
    }))

    def record_heartbeat(self, duration_ms: float, hobj_count: int) -> None:
        """Record a heartbeat cycle."""
        self.heartbeats.increment()
        self.heartbeat_timing.record(duration_ms)
        self.hobjs_processed.increment(hobj_count)

    def record_ai_call(self, duration_ms: float, prompt_tokens: int, response_tokens: int) -> None:
        """Record an AI API call."""
        self.ai_calls.increment()
        self.ai_call_timing.record(duration_ms)
        self.prompt_tokens_total += prompt_tokens
        self.response_tokens_total += response_tokens

    def record_action(self, hobj_id: str, action_name: str, duration_ms: float, success: bool) -> None:
        """Record an action dispatch."""
        self.actions_dispatched.increment()
        self.action_timing[action_name].record(duration_ms)
        self.hobj_stats[hobj_id]["actions"] += 1

        if not success:
            self.actions_failed.increment()
            self.hobj_stats[hobj_id]["errors"] += 1

    def record_token_allocation(self, hobj_id: str, amount: int) -> None:
        """Record a token allocation."""
        self.tokens_allocated.increment(amount)
        self.hobj_stats[hobj_id]["tokens_received"] += amount

    def record_hobj_heartbeat(self, hobj_id: str) -> None:
        """Record that an hobj participated in a heartbeat."""
        self.hobj_stats[hobj_id]["heartbeats"] += 1

    def record_error(self, error_type: str, message: str, context: dict[str, Any] | None = None) -> None:
        """Record an error."""
        if len(self.errors) >= self._max_errors:
            self.errors.pop(0)

        self.errors.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": error_type,
            "message": message,
            "context": context or {},
        })

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all telemetry data."""
        return {
            "heartbeats": {
                **self.heartbeats.to_dict(),
                "timing": self.heartbeat_timing.to_dict(),
            },
            "ai_calls": {
                **self.ai_calls.to_dict(),
                "timing": self.ai_call_timing.to_dict(),
                "prompt_tokens_total": self.prompt_tokens_total,
                "response_tokens_total": self.response_tokens_total,
            },
            "actions": {
                "dispatched": self.actions_dispatched.to_dict(),
                "failed": self.actions_failed.to_dict(),
                "by_name": {
                    name: stats.to_dict()
                    for name, stats in self.action_timing.items()
                },
            },
            "tokens": {
                "allocated": self.tokens_allocated.to_dict(),
            },
            "hobjs": {
                "processed": self.hobjs_processed.to_dict(),
                "unique_count": len(self.hobj_stats),
            },
            "errors": {
                "count": len(self.errors),
                "recent": self.errors[-5:] if self.errors else [],
            },
        }

    def get_hobj_summary(self, hobj_id: str) -> dict[str, Any]:
        """Get stats for a specific hobj."""
        return dict(self.hobj_stats.get(hobj_id, {}))

    def reset(self) -> None:
        """Reset all telemetry data."""
        self.heartbeat_timing = TimingStats()
        self.ai_call_timing = TimingStats()
        self.action_timing.clear()
        self.serialization_timing = TimingStats()
        self.heartbeats = CounterStats()
        self.hobjs_processed = CounterStats()
        self.actions_dispatched = CounterStats()
        self.actions_failed = CounterStats()
        self.tokens_allocated = CounterStats()
        self.ai_calls = CounterStats()
        self.prompt_tokens_total = 0
        self.response_tokens_total = 0
        self.errors.clear()
        self.hobj_stats.clear()


class Timer:
    """Context manager for timing operations."""

    def __init__(self) -> None:
        self.start_time: float = 0
        self.duration_ms: float = 0

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000


# Global telemetry instance
_telemetry: HolonicTelemetry | None = None


def get_telemetry() -> HolonicTelemetry:
    """Get the global telemetry instance."""
    global _telemetry
    if _telemetry is None:
        _telemetry = HolonicTelemetry()
    return _telemetry


def reset_telemetry() -> None:
    """Reset the global telemetry instance."""
    global _telemetry
    _telemetry = HolonicTelemetry()
