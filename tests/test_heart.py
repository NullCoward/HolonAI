"""
Tests for the Heartbeat and HolonicHeart classes.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from holonic_engine import (
    HolonicObject,
    Heartbeat,
    HolonicObjectHeartbeatRecord,
    HolonicHeart,
)


class TestHeartbeat:
    """Tests for the Heartbeat class."""

    def test_create_heartbeat(self):
        """Test creating a heartbeat."""
        now = datetime.now(timezone.utc)
        heartbeat = Heartbeat(heartbeat_time=now)
        assert heartbeat.heartbeat_time == now
        assert len(heartbeat) == 0

    def test_add_holonicobject(self):
        """Test adding a HolonicObject to heartbeat."""
        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hobj = HolonicObject()
        hobj.purpose_set("role", "test")

        heartbeat.add_holonicobject(hobj)

        assert len(heartbeat) == 1
        assert hobj in heartbeat.get_holonicobjects()

    def test_add_multiple_holonicobjects(self):
        """Test adding multiple HolonicObjects."""
        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hobj1 = HolonicObject()
        hobj2 = HolonicObject()

        heartbeat.add_holonicobject(hobj1)
        heartbeat.add_holonicobject(hobj2)

        assert len(heartbeat) == 2
        hobjs = heartbeat.get_holonicobjects()
        assert hobj1 in hobjs
        assert hobj2 in hobjs

    def test_hud_captured_at_add_time(self):
        """Test that HUD is captured when hobj is added."""
        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hobj = HolonicObject()
        hobj.knowledge_set("value", 1)

        heartbeat.add_holonicobject(hobj)

        # Modify after adding
        hobj.knowledge_set("value", 999)

        # HUD should have original value
        actions, hud = heartbeat.get_results(hobj)
        assert hud["self"]["knowledge"]["value"] == 1

    def test_build_prompt(self):
        """Test building the prompt."""
        now = datetime.now(timezone.utc)
        heartbeat = Heartbeat(heartbeat_time=now)
        hobj = HolonicObject()
        hobj.purpose_set("role", "Test Agent")

        heartbeat.add_holonicobject(hobj)
        prompt = heartbeat.build_prompt()

        assert now.isoformat() in prompt
        assert hobj.id in prompt
        assert "Test Agent" in prompt
        assert heartbeat.full_prompt == prompt

    def test_process_response(self):
        """Test processing AI response."""
        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hobj = HolonicObject()
        heartbeat.add_holonicobject(hobj)

        response = f'{{"{hobj.id}": {{"actions": [{{"action": "knowledge_set", "params": {{"path": "test", "value": 1}}}}]}}}}'
        heartbeat.process_response(response)

        actions, hud = heartbeat.get_results(hobj)
        assert len(actions["actions"]) == 1
        assert actions["actions"][0]["action"] == "knowledge_set"

    def test_process_response_empty_actions(self):
        """Test processing response with no actions."""
        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hobj = HolonicObject()
        heartbeat.add_holonicobject(hobj)

        response = f'{{"{hobj.id}": {{"actions": []}}}}'
        heartbeat.process_response(response)

        actions, hud = heartbeat.get_results(hobj)
        assert actions["actions"] == []

    def test_process_response_missing_hobj(self):
        """Test that missing hobjs get empty actions."""
        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hobj = HolonicObject()
        heartbeat.add_holonicobject(hobj)

        response = '{"some-other-id": {"actions": []}}'
        heartbeat.process_response(response)

        actions, hud = heartbeat.get_results(hobj)
        assert actions["actions"] == []

    def test_get_results_not_found(self):
        """Test getting results for hobj not in heartbeat."""
        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hobj = HolonicObject()

        with pytest.raises(KeyError):
            heartbeat.get_results(hobj)

    def test_dispatch_to_holonicobjects(self):
        """Test dispatching results to hobjs."""
        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hobj = HolonicObject()
        heartbeat.add_holonicobject(hobj)

        response = f'{{"{hobj.id}": {{"actions": [{{"action": "knowledge_set", "params": {{"path": "dispatched", "value": true}}}}]}}}}'
        heartbeat.process_response(response)
        heartbeat.dispatch_to_holonicobjects()

        assert hobj.knowledge_get("dispatched") is True

    def test_dispatch_updates_last_heartbeat(self):
        """Test that dispatch updates last_heartbeat."""
        now = datetime.now(timezone.utc).replace(microsecond=0)
        heartbeat = Heartbeat(heartbeat_time=now)
        hobj = HolonicObject()
        heartbeat.add_holonicobject(hobj)

        response = f'{{"{hobj.id}": {{"actions": []}}}}'
        heartbeat.process_response(response)
        heartbeat.dispatch_to_holonicobjects()

        assert hobj.last_heartbeat == now

    def test_raw_response_stored(self):
        """Test that raw response is stored."""
        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hobj = HolonicObject()
        heartbeat.add_holonicobject(hobj)

        response = f'{{"{hobj.id}": {{"actions": []}}}}'
        heartbeat.process_response(response)

        assert heartbeat.raw_response == response


class TestHolonicObjectHeartbeatRecord:
    """Tests for HolonicObjectHeartbeatRecord."""

    def test_create_record(self):
        """Test creating a record."""
        hobj = HolonicObject()
        hud = hobj.to_dict()
        scheduled_time = datetime.now(timezone.utc)
        record = HolonicObjectHeartbeatRecord(hobj=hobj, hud_sent=hud, scheduled_time=scheduled_time)

        assert record.hobj is hobj
        assert record.hud_sent == hud
        assert record.scheduled_time == scheduled_time
        assert record.actions_result == {}

    def test_record_with_actions(self):
        """Test record with actions result."""
        hobj = HolonicObject()
        hud = hobj.to_dict()
        scheduled_time = datetime.now(timezone.utc)
        record = HolonicObjectHeartbeatRecord(
            hobj=hobj,
            hud_sent=hud,
            scheduled_time=scheduled_time,
            actions_result={"actions": [{"action": "test"}]}
        )

        assert record.scheduled_time == scheduled_time
        assert len(record.actions_result["actions"]) == 1


class TestHolonicHeart:
    """Tests for the HolonicHeart class."""

    def test_create_heart(self):
        """Test creating a heart."""
        root = HolonicObject()
        client = Mock()

        heart = HolonicHeart(root=root, client=client)

        assert heart.root is root
        assert heart.client is client
        assert heart.interval == 1.0
        assert heart.token_allocations == []
        assert heart.history == []

    def test_token_allocations_init(self):
        """Test initializing with token allocations."""
        root = HolonicObject()
        client = Mock()
        child = root.create_child()

        heart = HolonicHeart(
            root=root,
            client=client,
            token_allocations=[(child, 10)]
        )

        assert len(heart.token_allocations) == 1
        assert heart.token_allocations[0] == (child, 10)

    def test_add_token_allocation(self):
        """Test adding token allocation."""
        root = HolonicObject()
        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        heart.add_token_allocation(root, 50)

        assert len(heart.token_allocations) == 1
        assert heart.token_allocations[0] == (root, 50)

    def test_remove_token_allocation(self):
        """Test removing token allocation."""
        root = HolonicObject()
        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        heart.add_token_allocation(root, 50)
        result = heart.remove_token_allocation(root)

        assert result is True
        assert len(heart.token_allocations) == 0

    def test_remove_token_allocation_not_found(self):
        """Test removing non-existent allocation."""
        root = HolonicObject()
        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        result = heart.remove_token_allocation(root)

        assert result is False

    def test_set_token_allocation(self):
        """Test setting token allocation (replaces existing)."""
        root = HolonicObject()
        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        heart.add_token_allocation(root, 50)
        heart.set_token_allocation(root, 100)

        assert len(heart.token_allocations) == 1
        assert heart.token_allocations[0] == (root, 100)

    def test_beat_allocates_tokens(self):
        """Test that beat allocates tokens."""
        root = HolonicObject()
        root.token_bank = 0
        root.next_heartbeat = datetime.now(timezone.utc) + timedelta(hours=1)  # Not due

        client = Mock()
        heart = HolonicHeart(root=root, client=client)
        heart.add_token_allocation(root, 25)

        heart.beat()

        assert root.token_bank == 25

    def test_beat_allocates_to_frozen(self):
        """Test that beat allocates tokens even to frozen hobjs."""
        root = HolonicObject()
        root.token_bank = -100
        root.next_heartbeat = datetime.now(timezone.utc) + timedelta(hours=1)  # Not due

        client = Mock()
        heart = HolonicHeart(root=root, client=client)
        heart.add_token_allocation(root, 10)

        heart.beat()

        assert root.token_bank == -90

    def test_beat_skips_frozen_hobjs(self):
        """Test that beat skips frozen hobjs for processing."""
        root = HolonicObject()
        root.token_bank = -1
        root.next_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=1)  # Due

        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        result = heart.beat()

        assert result is None
        client.chat.completions.create.assert_not_called()

    def test_beat_returns_none_when_no_due(self):
        """Test that beat returns None when no hobjs are due."""
        root = HolonicObject()
        root.next_heartbeat = datetime.now(timezone.utc) + timedelta(hours=1)

        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        result = heart.beat()

        assert result is None

    @patch('holonic_engine.heart.call_ai')
    def test_beat_processes_due_hobjs(self, mock_call_ai):
        """Test that beat processes due hobjs."""
        root = HolonicObject()
        root.token_bank = 100
        root.next_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=1)

        mock_call_ai.return_value = f'{{"{root.id}": {{"actions": []}}}}'

        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        result = heart.beat()

        assert result is not None
        assert len(result) == 1
        mock_call_ai.assert_called_once()

    @patch('holonic_engine.heart.call_ai')
    def test_beat_stores_in_history(self, mock_call_ai):
        """Test that beat stores heartbeat in history."""
        root = HolonicObject()
        root.token_bank = 100
        root.next_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=1)

        mock_call_ai.return_value = f'{{"{root.id}": {{"actions": []}}}}'

        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        heart.beat()

        assert len(heart.history) == 1

    @patch('holonic_engine.heart.call_ai')
    def test_beat_dispatches_actions(self, mock_call_ai):
        """Test that beat dispatches actions to hobjs."""
        root = HolonicObject()
        root.token_bank = 100
        root.next_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=1)

        mock_call_ai.return_value = f'{{"{root.id}": {{"actions": [{{"action": "knowledge_set", "params": {{"path": "test", "value": 42}}}}]}}}}'

        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        heart.beat()

        assert root.knowledge_get("test") == 42

    def test_on_heartbeat_callback(self):
        """Test registering heartbeat callback."""
        root = HolonicObject()
        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        callback = Mock()
        heart.on_heartbeat(callback)

        assert heart._on_heartbeat is callback

    @patch('holonic_engine.heart.call_ai')
    def test_beat_with_children(self, mock_call_ai):
        """Test beat with parent and children."""
        root = HolonicObject()
        root.token_bank = 100
        root.next_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=1)

        child1 = root.create_child()
        child1.token_bank = 50
        child1.next_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=1)

        child2 = root.create_child()
        child2.token_bank = -10  # Frozen
        child2.next_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=1)

        mock_call_ai.return_value = f'{{"{root.id}": {{"actions": []}}, "{child1.id}": {{"actions": []}}}}'

        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        result = heart.beat()

        # Should process root and child1, but not child2 (frozen)
        assert result is not None
        assert len(result) == 2


class TestHeartStartStop:
    """Tests for heart start/stop functionality."""

    def test_start_creates_thread(self):
        """Test that start creates a background thread."""
        root = HolonicObject()
        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        heart.start()

        assert heart._running is True
        assert heart._thread is not None
        assert heart._thread.is_alive()

        heart.stop()

    def test_stop_stops_thread(self):
        """Test that stop stops the background thread."""
        root = HolonicObject()
        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        heart.start()
        heart.stop()

        assert heart._running is False

    def test_start_idempotent(self):
        """Test that calling start twice doesn't create multiple threads."""
        root = HolonicObject()
        client = Mock()
        heart = HolonicHeart(root=root, client=client)

        heart.start()
        thread1 = heart._thread
        heart.start()
        thread2 = heart._thread

        assert thread1 is thread2

        heart.stop()
