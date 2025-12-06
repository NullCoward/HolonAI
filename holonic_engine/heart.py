"""
HolonicHeart - The heartbeat scheduler for the Holonic Engine.

Runs periodic heartbeats, collects due holons, serializes and submits to AI,
then dispatches results back to the appropriate holons.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Callable

import attrs

from .client import call_ai, detect_client_type
from .logging import heart_logger, log_heartbeat_start, log_heartbeat_complete, log_token_allocation, log_ai_call, log_ai_response
from .serialization import parse_ai_response
from .telemetry import get_telemetry, Timer
from .tokens import count_tokens

if TYPE_CHECKING:
    from .agent import HolonicObject


@attrs.define
class HolonicObjectHeartbeatRecord:
    """Record of a single HolonicObject's participation in a heartbeat."""
    hobj: "HolonicObject"
    hud_sent: dict[str, Any]
    scheduled_time: datetime  # When this holon was scheduled to heartbeat
    actions_result: dict[str, Any] = attrs.field(factory=dict)


@attrs.define
class Heartbeat:
    """A single heartbeat cycle - records all interaction for history."""
    heartbeat_time: datetime  # When this heartbeat cycle started
    execution_time: datetime | None = attrs.field(default=None)  # When AI call started
    completion_time: datetime | None = attrs.field(default=None)  # When AI call completed
    _records: list[HolonicObjectHeartbeatRecord] = attrs.field(factory=list)
    _full_prompt: str = attrs.field(default="")
    _raw_response: str = attrs.field(default="")
    _parsed_response: dict[str, Any] = attrs.field(factory=dict)

    def add_holonicobject(self, hobj: "HolonicObject", scheduled_time: datetime | None = None) -> None:
        """Add a HolonicObject to this heartbeat and capture its serialized HUD."""
        import copy
        hud = copy.deepcopy(hobj.to_dict())
        # Use the holon's next_heartbeat as scheduled time if not provided
        if scheduled_time is None:
            scheduled_time = hobj.next_heartbeat
        self._records.append(HolonicObjectHeartbeatRecord(
            hobj=hobj,
            hud_sent=hud,
            scheduled_time=scheduled_time,
        ))

    def get_holonicobjects(self) -> list["HolonicObject"]:
        """Get list of all HolonicObjects in this heartbeat."""
        return [r.hobj for r in self._records]

    def get_results(self, hobj: "HolonicObject") -> tuple[dict[str, Any], dict[str, Any]]:
        """Get results for a specific HolonicObject. Returns (actions_json, full_hud_sent)."""
        for record in self._records:
            if record.hobj is hobj:
                return (record.actions_result, record.hud_sent)
        raise KeyError(f"HolonicObject {hobj.id} not found in this heartbeat")

    def build_prompt(self) -> str:
        """Build the combined prompt for AI submission."""
        # Build holon data with timestamps
        holons_data = {}
        for record in self._records:
            holon_data = record.hud_sent.copy()
            holon_data["_heartbeat_info"] = {
                "scheduled_time": record.scheduled_time.isoformat(),
                "active_heartbeat": record.hobj._active_heartbeat_info() if hasattr(record.hobj, '_active_heartbeat_info') else None,
            }
            holons_data[record.hobj.id] = holon_data

        combined_data = {
            "heartbeat_time": self.heartbeat_time.isoformat(),
            "execution_time": self.execution_time.isoformat() if self.execution_time else None,
            "holons": holons_data,
        }
        self._full_prompt = f"""You are processing a heartbeat for multiple holons. Each holon has its own purpose, state, and available actions.

For each holon, analyze its state and decide what actions (if any) to take.

Respond with a JSON object where each key is a holon GUID and the value is an object with an "actions" array:

{{
  "holon-guid-1": {{
    "actions": [
      {{"action": "action_name", "params": {{"key": "value"}}}}
    ]
  }},
  "holon-guid-2": {{
    "actions": []
  }}
}}

If a holon needs no actions, use an empty actions array.

HOLONS DATA:
{json.dumps(combined_data, indent=2)}
"""
        return self._full_prompt

    def process_response(self, response_text: str) -> None:
        """Parse AI response and distribute results to each holon record."""
        self._raw_response = response_text
        try:
            self._parsed_response = json.loads(response_text)
        except json.JSONDecodeError:
            self._parsed_response = parse_ai_response(response_text)

        # Distribute results to each record
        for record in self._records:
            record.actions_result = self._parsed_response.get(record.hobj.id, {"actions": []})

    def dispatch_to_holonicobjects(self) -> dict[str, list[Any]]:
        """Dispatch results to each HolonicObject and return execution results."""
        results: dict[str, list[Any]] = {}
        for record in self._records:
            results[record.hobj.id] = record.hobj.action_results(
                record.actions_result,
                self.heartbeat_time
            )
        return results

    @property
    def full_prompt(self) -> str:
        """The full prompt that was sent to AI."""
        return self._full_prompt

    @property
    def raw_response(self) -> str:
        """The raw response text from AI."""
        return self._raw_response

    @property
    def is_complete(self) -> bool:
        """Check if this heartbeat has completed (AI response received)."""
        return self.completion_time is not None

    @property
    def is_active(self) -> bool:
        """Check if this heartbeat is currently in progress (started but not completed)."""
        return self.execution_time is not None and self.completion_time is None

    def __len__(self) -> int:
        return len(self._records)


@attrs.define
class HolonicHeart:
    """
    The heartbeat scheduler for the Holonic Engine.

    Runs every second (configurable), collects holons due for a heartbeat,
    serializes them, submits to AI, and dispatches results.
    """
    root: "HolonicObject" = attrs.field()
    client: Any = attrs.field()
    model: str = attrs.field(default="gpt-4o")
    interval: float = attrs.field(default=1.0)
    max_tokens: int = attrs.field(default=4096)
    structured_output: bool = attrs.field(default=True)
    token_allocations: list[tuple["HolonicObject", int]] = attrs.field(factory=list)

    _running: bool = attrs.field(default=False, init=False)
    _thread: threading.Thread | None = attrs.field(default=None, init=False)
    _history: list[Heartbeat] = attrs.field(factory=list, init=False)
    _on_heartbeat: Callable[[Heartbeat], None] | None = attrs.field(default=None)

    @property
    def is_running(self) -> bool:
        """Check if the heart is currently beating."""
        return self._running

    def start(self) -> None:
        """Start the heartbeat loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the heartbeat loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.interval * 2)
            self._thread = None

    def _run_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                heartbeat = self.beat()
                if heartbeat and len(heartbeat) > 0 and self._on_heartbeat:
                    self._on_heartbeat(heartbeat)
            except Exception:
                pass  # Silently continue on errors
            time.sleep(self.interval)

    def beat(self) -> Heartbeat | None:
        """Execute a single heartbeat cycle. Returns the Heartbeat object or None if no holons due."""
        telemetry = get_telemetry()

        with Timer() as total_timer:
            # Round to the current second
            now = datetime.now(timezone.utc)
            heartbeat_time = now.replace(microsecond=0)
            next_second = heartbeat_time + timedelta(seconds=1)

            # Allocate tokens to all hobjs in token_allocations (even if frozen)
            for hobj, amount in self.token_allocations:
                hobj.token_bank += amount
                telemetry.record_token_allocation(hobj.id, amount)
                log_token_allocation(hobj.id, amount, hobj.token_bank)

            # Collect all (holon, next_heartbeat) pairs from the tree
            all_heartbeats = self.root.collect_due_heartbeats()

            # Filter for holons due before next second (non-inclusive) with non-negative token_bank
            # Also exclude holons that already have an active heartbeat in progress
            due_holons = [
                (hobj, ts) for hobj, ts in all_heartbeats
                if ts < next_second and hobj.token_bank >= 0 and not hobj.has_active_heartbeat
            ]

            if not due_holons:
                return None

            log_heartbeat_start(heartbeat_time, len(due_holons))

            # Create heartbeat and add all due HolonicObjects
            heartbeat = Heartbeat(heartbeat_time=heartbeat_time)
            for hobj, scheduled_time in due_holons:
                heartbeat.add_holonicobject(hobj, scheduled_time=scheduled_time)
                # Mark each holon as having an active heartbeat
                hobj.mark_heartbeat_started(scheduled_time=scheduled_time)
                telemetry.record_hobj_heartbeat(hobj.id)

            # Set execution time just before AI call
            heartbeat.execution_time = datetime.now(timezone.utc)

            # Store in history BEFORE AI call so other heartbeats can see it's active
            self._history.append(heartbeat)

            # Build prompt and call AI
            prompt = heartbeat.build_prompt()
            prompt_tokens = count_tokens(prompt)
            log_ai_call(prompt_tokens, self.model)

            with Timer() as ai_timer:
                response_text = call_ai(
                    self.client,
                    prompt,
                    self.model,
                    self.max_tokens,
                    structured_output=self.structured_output and detect_client_type(self.client) == "openai"
                )

            # Set completion time after AI call
            heartbeat.completion_time = datetime.now(timezone.utc)

            response_tokens = count_tokens(response_text)
            log_ai_response(response_tokens, ai_timer.duration_ms)
            telemetry.record_ai_call(ai_timer.duration_ms, prompt_tokens, response_tokens)

            # Process response and dispatch to HolonicObjects
            # (dispatch_to_holonicobjects calls action_results which clears active heartbeat)
            heartbeat.process_response(response_text)
            heartbeat.dispatch_to_holonicobjects()

        # Record telemetry
        telemetry.record_heartbeat(total_timer.duration_ms, len(due_holons))
        log_heartbeat_complete(heartbeat_time, len(due_holons), total_timer.duration_ms)

        return heartbeat

    @property
    def history(self) -> list[Heartbeat]:
        """Get the history of all heartbeats."""
        return list(self._history)

    def on_heartbeat(self, callback: Callable[[Heartbeat], None]) -> None:
        """Register a callback for heartbeat results."""
        self._on_heartbeat = callback

    def add_token_allocation(self, hobj: "HolonicObject", amount: int) -> None:
        """Add a token allocation for a HolonicObject."""
        self.token_allocations.append((hobj, amount))

    def remove_token_allocation(self, hobj: "HolonicObject") -> bool:
        """Remove all token allocations for a HolonicObject. Returns True if any removed."""
        original_len = len(self.token_allocations)
        self.token_allocations = [(h, a) for h, a in self.token_allocations if h is not hobj]
        return len(self.token_allocations) < original_len

    def set_token_allocation(self, hobj: "HolonicObject", amount: int) -> None:
        """Set the token allocation for a HolonicObject (replaces any existing)."""
        self.remove_token_allocation(hobj)
        self.add_token_allocation(hobj, amount)
