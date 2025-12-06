"""
Tests for the telemetry module.
"""

import pytest
from datetime import datetime, timezone

from holonic_engine.telemetry import (
    TimingStats,
    CounterStats,
    HolonicTelemetry,
    Timer,
    get_telemetry,
    reset_telemetry,
)


class TestTimingStats:
    """Tests for TimingStats."""

    def test_initial_state(self):
        """Test initial state of timing stats."""
        stats = TimingStats()
        assert stats.count == 0
        assert stats.total_ms == 0.0
        assert stats.avg_ms == 0.0

    def test_record_single(self):
        """Test recording a single timing."""
        stats = TimingStats()
        stats.record(100.0)

        assert stats.count == 1
        assert stats.total_ms == 100.0
        assert stats.min_ms == 100.0
        assert stats.max_ms == 100.0
        assert stats.avg_ms == 100.0

    def test_record_multiple(self):
        """Test recording multiple timings."""
        stats = TimingStats()
        stats.record(100.0)
        stats.record(200.0)
        stats.record(300.0)

        assert stats.count == 3
        assert stats.total_ms == 600.0
        assert stats.min_ms == 100.0
        assert stats.max_ms == 300.0
        assert stats.avg_ms == 200.0

    def test_to_dict(self):
        """Test converting to dictionary."""
        stats = TimingStats()
        stats.record(100.0)
        stats.record(200.0)

        result = stats.to_dict()

        assert result["count"] == 2
        assert result["total_ms"] == 300.0
        assert result["avg_ms"] == 150.0
        assert result["min_ms"] == 100.0
        assert result["max_ms"] == 200.0

    def test_to_dict_empty(self):
        """Test converting empty stats to dictionary."""
        stats = TimingStats()
        result = stats.to_dict()

        assert result["count"] == 0
        assert result["min_ms"] is None
        assert result["max_ms"] is None


class TestCounterStats:
    """Tests for CounterStats."""

    def test_initial_state(self):
        """Test initial state of counter."""
        stats = CounterStats()
        assert stats.count == 0
        assert stats.first_seen is None
        assert stats.last_seen is None

    def test_increment(self):
        """Test incrementing counter."""
        stats = CounterStats()
        stats.increment()

        assert stats.count == 1
        assert stats.first_seen is not None
        assert stats.last_seen is not None

    def test_increment_by_amount(self):
        """Test incrementing by specific amount."""
        stats = CounterStats()
        stats.increment(10)

        assert stats.count == 10

    def test_multiple_increments(self):
        """Test multiple increments."""
        stats = CounterStats()
        stats.increment(5)
        stats.increment(3)
        stats.increment(2)

        assert stats.count == 10

    def test_duration_secs(self):
        """Test duration calculation."""
        stats = CounterStats()
        stats.increment()

        # Duration should be very small but non-negative
        assert stats.duration_secs >= 0

    def test_rate_per_sec(self):
        """Test rate calculation."""
        stats = CounterStats()

        # Rate should be 0 when no duration
        assert stats.rate_per_sec == 0.0

    def test_to_dict(self):
        """Test converting to dictionary."""
        stats = CounterStats()
        stats.increment(5)

        result = stats.to_dict()

        assert result["count"] == 5
        assert "duration_secs" in result
        assert "rate_per_sec" in result


class TestHolonicTelemetry:
    """Tests for HolonicTelemetry."""

    def test_initial_state(self):
        """Test initial state of telemetry."""
        telemetry = HolonicTelemetry()

        assert telemetry.heartbeats.count == 0
        assert telemetry.ai_calls.count == 0
        assert telemetry.prompt_tokens_total == 0

    def test_record_heartbeat(self):
        """Test recording a heartbeat."""
        telemetry = HolonicTelemetry()
        telemetry.record_heartbeat(100.0, 3)

        assert telemetry.heartbeats.count == 1
        assert telemetry.hobjs_processed.count == 3
        assert telemetry.heartbeat_timing.count == 1

    def test_record_ai_call(self):
        """Test recording an AI call."""
        telemetry = HolonicTelemetry()
        telemetry.record_ai_call(500.0, 1000, 200)

        assert telemetry.ai_calls.count == 1
        assert telemetry.prompt_tokens_total == 1000
        assert telemetry.response_tokens_total == 200
        assert telemetry.ai_call_timing.count == 1

    def test_record_action(self):
        """Test recording an action."""
        telemetry = HolonicTelemetry()
        telemetry.record_action("hobj-1", "knowledge_set", 10.0, True)

        assert telemetry.actions_dispatched.count == 1
        assert telemetry.actions_failed.count == 0
        assert "knowledge_set" in telemetry.action_timing

    def test_record_action_failed(self):
        """Test recording a failed action."""
        telemetry = HolonicTelemetry()
        telemetry.record_action("hobj-1", "bad_action", 5.0, False)

        assert telemetry.actions_dispatched.count == 1
        assert telemetry.actions_failed.count == 1

    def test_record_token_allocation(self):
        """Test recording token allocation."""
        telemetry = HolonicTelemetry()
        telemetry.record_token_allocation("hobj-1", 100)

        assert telemetry.tokens_allocated.count == 100
        assert telemetry.hobj_stats["hobj-1"]["tokens_received"] == 100

    def test_record_hobj_heartbeat(self):
        """Test recording hobj heartbeat participation."""
        telemetry = HolonicTelemetry()
        telemetry.record_hobj_heartbeat("hobj-1")
        telemetry.record_hobj_heartbeat("hobj-1")

        assert telemetry.hobj_stats["hobj-1"]["heartbeats"] == 2

    def test_record_error(self):
        """Test recording an error."""
        telemetry = HolonicTelemetry()
        telemetry.record_error("TestError", "Something went wrong", {"key": "value"})

        assert len(telemetry.errors) == 1
        assert telemetry.errors[0]["type"] == "TestError"
        assert telemetry.errors[0]["message"] == "Something went wrong"

    def test_error_limit(self):
        """Test that errors are limited."""
        telemetry = HolonicTelemetry()
        telemetry._max_errors = 5

        for i in range(10):
            telemetry.record_error("Error", f"Error {i}")

        assert len(telemetry.errors) == 5
        # Should have the last 5 errors
        assert telemetry.errors[0]["message"] == "Error 5"

    def test_get_summary(self):
        """Test getting telemetry summary."""
        telemetry = HolonicTelemetry()
        telemetry.record_heartbeat(100.0, 2)
        telemetry.record_ai_call(500.0, 1000, 200)
        telemetry.record_action("hobj-1", "test", 10.0, True)

        summary = telemetry.get_summary()

        assert "heartbeats" in summary
        assert "ai_calls" in summary
        assert "actions" in summary
        assert "tokens" in summary
        assert "hobjs" in summary
        assert "errors" in summary

    def test_get_hobj_summary(self):
        """Test getting per-hobj summary."""
        telemetry = HolonicTelemetry()
        telemetry.record_hobj_heartbeat("hobj-1")
        telemetry.record_action("hobj-1", "test", 10.0, True)
        telemetry.record_token_allocation("hobj-1", 50)

        summary = telemetry.get_hobj_summary("hobj-1")

        assert summary["heartbeats"] == 1
        assert summary["actions"] == 1
        assert summary["tokens_received"] == 50

    def test_get_hobj_summary_not_found(self):
        """Test getting summary for unknown hobj."""
        telemetry = HolonicTelemetry()
        summary = telemetry.get_hobj_summary("unknown")

        assert summary == {}

    def test_reset(self):
        """Test resetting telemetry."""
        telemetry = HolonicTelemetry()
        telemetry.record_heartbeat(100.0, 2)
        telemetry.record_ai_call(500.0, 1000, 200)
        telemetry.record_error("Error", "test")

        telemetry.reset()

        assert telemetry.heartbeats.count == 0
        assert telemetry.ai_calls.count == 0
        assert telemetry.prompt_tokens_total == 0
        assert len(telemetry.errors) == 0


class TestTimer:
    """Tests for Timer context manager."""

    def test_timer_measures_duration(self):
        """Test that timer measures duration."""
        import time

        with Timer() as timer:
            time.sleep(0.01)  # 10ms

        assert timer.duration_ms >= 10.0

    def test_timer_as_context_manager(self):
        """Test timer as context manager."""
        with Timer() as timer:
            pass

        assert timer.duration_ms >= 0


class TestGlobalTelemetry:
    """Tests for global telemetry functions."""

    def test_get_telemetry_singleton(self):
        """Test that get_telemetry returns same instance."""
        reset_telemetry()
        t1 = get_telemetry()
        t2 = get_telemetry()

        assert t1 is t2

    def test_reset_telemetry(self):
        """Test that reset_telemetry creates new instance."""
        t1 = get_telemetry()
        t1.record_heartbeat(100.0, 1)

        reset_telemetry()
        t2 = get_telemetry()

        assert t2.heartbeats.count == 0
