"""
Tests for the storage layer.

Uses SQLite in-memory for all tests.
"""

import pytest
from datetime import datetime, timezone, timedelta

from holonic_engine import HolonicObject, Heartbeat
from holonic_engine.storage import SQLStorage


@pytest.fixture
def storage():
    """Create an in-memory SQLite storage for testing."""
    store = SQLStorage("sqlite:///:memory:")
    store.connect()
    store.create_tables()
    yield store
    store.disconnect()


class TestSQLStorageConnection:
    """Tests for connection management."""

    def test_connect_disconnect(self):
        """Test basic connect/disconnect."""
        store = SQLStorage("sqlite:///:memory:")
        store.connect()
        assert store._engine is not None
        store.disconnect()
        assert store._engine is None

    def test_context_manager(self):
        """Test context manager usage."""
        with SQLStorage("sqlite:///:memory:") as store:
            store.create_tables()
            assert store._engine is not None
        assert store._engine is None

    def test_engine_requires_connect(self):
        """Test that engine property requires connection."""
        store = SQLStorage("sqlite:///:memory:")
        with pytest.raises(RuntimeError, match="not connected"):
            _ = store.engine


class TestHolonPersistence:
    """Tests for Holon (type/template) persistence."""

    def test_save_and_load_holon(self, storage):
        """Test saving and loading a Holon."""
        hobj = HolonicObject()
        hobj.purpose_set("role", "TestAgent")
        hobj.purpose_set("goal", "Complete tasks")

        storage.save_holon(hobj)
        loaded = storage.load_holon(hobj.id)

        assert loaded is not None
        assert loaded["id"] == hobj.id
        assert loaded["purpose"]["role"] == "TestAgent"
        assert loaded["purpose"]["goal"] == "Complete tasks"

    def test_save_holon_with_actions(self, storage):
        """Test saving holon with custom actions."""
        hobj = HolonicObject()

        def custom_action(x: int, y: str) -> str:
            return f"{y}: {x}"

        hobj.add_action(custom_action, name="custom", purpose="Do something custom")

        storage.save_holon(hobj)
        loaded = storage.load_holon(hobj.id)

        assert loaded is not None
        # Should have built-in actions plus custom
        action_names = [a["name"] for a in loaded["actions"]]
        assert "custom" in action_names

    def test_load_nonexistent_holon(self, storage):
        """Test loading a nonexistent holon."""
        loaded = storage.load_holon("nonexistent-id")
        assert loaded is None

    def test_delete_holon(self, storage):
        """Test deleting a holon."""
        hobj = HolonicObject()
        storage.save_holon(hobj)

        result = storage.delete_holon(hobj.id)
        assert result is True

        loaded = storage.load_holon(hobj.id)
        assert loaded is None

    def test_list_holons(self, storage):
        """Test listing all holons."""
        hobj1 = HolonicObject()
        hobj2 = HolonicObject()
        storage.save_holon(hobj1)
        storage.save_holon(hobj2)

        holon_ids = storage.list_holons()
        assert len(holon_ids) == 2
        assert hobj1.id in holon_ids
        assert hobj2.id in holon_ids


class TestHobjPersistence:
    """Tests for HolonicObject (instance) persistence."""

    def test_save_and_load_hobj(self, storage):
        """Test saving and loading a HolonicObject."""
        hobj = HolonicObject()
        hobj.knowledge_set("name", "TestAgent")
        hobj.knowledge_set("count", 42)
        hobj.token_bank = 100
        hobj.heart_rate_secs = 5

        # Must save holon first (foreign key)
        storage.save_holon(hobj)
        storage.save_hobj(hobj)
        loaded = storage.load_hobj(hobj.id)

        assert loaded is not None
        assert loaded["id"] == hobj.id
        assert loaded["holon_id"] == hobj.id
        assert loaded["knowledge"]["name"] == "TestAgent"
        assert loaded["knowledge"]["count"] == 42
        assert loaded["token_bank"] == 100
        assert loaded["heart_rate_secs"] == 5

    def test_save_updates_existing(self, storage):
        """Test that save updates existing record."""
        hobj = HolonicObject()
        hobj.knowledge_set("value", 1)

        storage.save_holon(hobj)
        storage.save_hobj(hobj)

        hobj.knowledge_set("value", 2)
        storage.save_hobj(hobj)

        loaded = storage.load_hobj(hobj.id)
        assert loaded["knowledge"]["value"] == 2

    def test_load_nonexistent(self, storage):
        """Test loading a nonexistent hobj."""
        loaded = storage.load_hobj("nonexistent-id")
        assert loaded is None

    def test_delete_hobj(self, storage):
        """Test deleting a hobj."""
        hobj = HolonicObject()
        storage.save_holon(hobj)
        storage.save_hobj(hobj)

        result = storage.delete_hobj(hobj.id)
        assert result is True

        loaded = storage.load_hobj(hobj.id)
        assert loaded is None

    def test_delete_nonexistent(self, storage):
        """Test deleting nonexistent hobj."""
        result = storage.delete_hobj("nonexistent-id")
        assert result is False

    def test_list_root_hobjs(self, storage):
        """Test listing root hobjs."""
        root1 = HolonicObject()
        root2 = HolonicObject()
        storage.save_holon(root1)
        storage.save_holon(root2)
        storage.save_hobj(root1)
        storage.save_hobj(root2)

        roots = storage.list_hobjs(parent_id=None)
        assert len(roots) == 2
        assert root1.id in roots
        assert root2.id in roots

    def test_list_children(self, storage):
        """Test listing children of a parent."""
        root = HolonicObject()
        child1 = root.create_child()
        child2 = root.create_child()

        storage.save_holon(root)
        storage.save_holon(child1)
        storage.save_holon(child2)
        storage.save_hobj(root)
        storage.save_hobj(child1)
        storage.save_hobj(child2)

        children = storage.list_hobjs(parent_id=root.id)
        assert len(children) == 2
        assert child1.id in children
        assert child2.id in children

    def test_list_hobjs_by_holon(self, storage):
        """Test listing hobjs by holon type."""
        hobj = HolonicObject()
        storage.save_holon(hobj)
        storage.save_hobj(hobj)

        hobjs = storage.list_hobjs_by_holon(hobj.id)
        assert len(hobjs) == 1
        assert hobj.id in hobjs

    def test_save_with_timestamps(self, storage):
        """Test saving hobj with heartbeat timestamps."""
        hobj = HolonicObject()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        hobj.last_heartbeat = now
        hobj.next_heartbeat = now + timedelta(seconds=5)

        storage.save_holon(hobj)
        storage.save_hobj(hobj)
        loaded = storage.load_hobj(hobj.id)

        assert loaded["last_heartbeat"] is not None
        assert loaded["next_heartbeat"] is not None


class TestHolonReferences:
    """Tests for holon reference tracking."""

    def test_add_holon_reference(self, storage):
        """Test adding a holon reference."""
        hobj = HolonicObject()
        storage.save_holon(hobj)
        storage.save_hobj(hobj)

        ref_id = storage.add_holon_reference(hobj.id, hobj.id, "primary")
        assert ref_id > 0

    def test_get_holon_references(self, storage):
        """Test getting references to a holon."""
        hobj1 = HolonicObject()
        hobj2 = HolonicObject()
        storage.save_holon(hobj1)
        storage.save_holon(hobj2)
        storage.save_hobj(hobj1)
        storage.save_hobj(hobj2)

        # Both hobjs reference the same holon
        storage.add_holon_reference(hobj1.id, hobj1.id, "primary")
        storage.add_holon_reference(hobj1.id, hobj2.id, "shared")

        refs = storage.get_holon_references(hobj1.id)
        assert len(refs) == 2

    def test_get_hobj_holon_references(self, storage):
        """Test getting holons referenced by a hobj."""
        hobj = HolonicObject()
        holon2 = HolonicObject()
        storage.save_holon(hobj)
        storage.save_holon(holon2)
        storage.save_hobj(hobj)

        storage.add_holon_reference(hobj.id, hobj.id, "primary")
        storage.add_holon_reference(holon2.id, hobj.id, "inherited")

        refs = storage.get_hobj_holon_references(hobj.id)
        assert len(refs) == 2

    def test_remove_holon_reference(self, storage):
        """Test removing a holon reference."""
        hobj = HolonicObject()
        storage.save_holon(hobj)
        storage.save_hobj(hobj)
        storage.add_holon_reference(hobj.id, hobj.id, "primary")

        result = storage.remove_holon_reference(hobj.id, hobj.id)
        assert result is True

        refs = storage.get_holon_references(hobj.id)
        assert len(refs) == 0


class TestFullPersistence:
    """Tests for combined holon + hobj persistence."""

    def test_save_full(self, storage):
        """Test saving both holon and hobj together."""
        hobj = HolonicObject()
        hobj.purpose_set("role", "Agent")
        hobj.knowledge_set("state", "active")

        storage.save_full(hobj)

        holon_data = storage.load_holon(hobj.id)
        hobj_data = storage.load_hobj(hobj.id)

        assert holon_data is not None
        assert hobj_data is not None
        assert holon_data["purpose"]["role"] == "Agent"
        assert hobj_data["knowledge"]["state"] == "active"


class TestTreePersistence:
    """Tests for tree save/load/restore."""

    def test_save_tree(self, storage):
        """Test saving an entire tree."""
        root = HolonicObject()
        child1 = root.create_child()
        child2 = root.create_child()
        grandchild = child1.create_child()

        count = storage.save_tree(root)

        assert count == 4

    def test_load_tree(self, storage):
        """Test loading a tree structure."""
        root = HolonicObject()
        root.purpose_set("role", "root")
        root.knowledge_set("name", "root")
        child1 = root.create_child()
        child1.knowledge_set("name", "child1")
        child2 = root.create_child()
        child2.knowledge_set("name", "child2")

        storage.save_tree(root)

        tree = storage.load_tree(root.id)

        assert tree is not None
        assert tree["knowledge"]["name"] == "root"
        assert tree["holon"]["purpose"]["role"] == "root"
        assert len(tree["children"]) == 2

        child_names = {c["knowledge"]["name"] for c in tree["children"]}
        assert child_names == {"child1", "child2"}

    def test_restore_hobj(self, storage):
        """Test restoring a single hobj."""
        original = HolonicObject()
        original.knowledge_set("value", 42)
        original.token_bank = 100
        original.purpose_set("role", "tester")

        storage.save_full(original)

        restored = storage.restore_hobj(original.id)

        assert restored is not None
        assert restored.id == original.id
        assert restored.knowledge_get("value") == 42
        assert restored.token_bank == 100

    def test_restore_tree(self, storage):
        """Test restoring an entire tree with relationships."""
        root = HolonicObject()
        root.purpose_set("role", "root")
        root.knowledge_set("name", "root")
        child = root.create_child()
        child.knowledge_set("name", "child")
        grandchild = child.create_child()
        grandchild.knowledge_set("name", "grandchild")

        storage.save_tree(root)

        restored = storage.restore_tree(root.id)

        assert restored is not None
        assert restored.knowledge_get("name") == "root"
        assert len(restored.holon_children) == 1

        restored_child = restored.holon_children[0]
        assert restored_child.knowledge_get("name") == "child"
        assert restored_child.holon_parent is restored
        assert len(restored_child.holon_children) == 1

        restored_grandchild = restored_child.holon_children[0]
        assert restored_grandchild.knowledge_get("name") == "grandchild"
        assert restored_grandchild.holon_parent is restored_child

    def test_restore_nonexistent_tree(self, storage):
        """Test restoring nonexistent tree."""
        restored = storage.restore_tree("nonexistent")
        assert restored is None


class TestHeartbeatPersistence:
    """Tests for heartbeat history."""

    def test_save_heartbeat(self, storage):
        """Test saving a heartbeat."""
        hobj = HolonicObject()
        storage.save_full(hobj)

        heartbeat = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        heartbeat.add_holonicobject(hobj)
        heartbeat.build_prompt()
        heartbeat.process_response(f'{{"{hobj.id}": {{"actions": []}}}}')

        heartbeat_id = storage.save_heartbeat(heartbeat)

        assert heartbeat_id > 0

    def test_get_heartbeat(self, storage):
        """Test getting a specific heartbeat."""
        hobj = HolonicObject()
        hobj.knowledge_set("value", 1)
        storage.save_full(hobj)

        now = datetime.now(timezone.utc)
        heartbeat = Heartbeat(heartbeat_time=now)
        heartbeat.add_holonicobject(hobj)
        heartbeat.build_prompt()
        heartbeat.process_response(f'{{"{hobj.id}": {{"actions": [{{"action": "test"}}]}}}}')

        heartbeat_id = storage.save_heartbeat(heartbeat)

        loaded = storage.get_heartbeat(heartbeat_id)

        assert loaded is not None
        assert loaded["hobj_count"] == 1
        assert len(loaded["hobjs"]) == 1
        assert loaded["hobjs"][0]["hobj_id"] == hobj.id

    def test_get_heartbeats_list(self, storage):
        """Test getting heartbeat list."""
        hobj = HolonicObject()
        storage.save_full(hobj)

        for i in range(3):
            hb = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
            hb.add_holonicobject(hobj)
            hb.build_prompt()
            hb.process_response(f'{{"{hobj.id}": {{"actions": []}}}}')
            storage.save_heartbeat(hb)

        heartbeats = storage.get_heartbeats(limit=10)
        assert len(heartbeats) == 3

    def test_get_heartbeats_filtered(self, storage):
        """Test filtering heartbeats by time."""
        hobj = HolonicObject()
        storage.save_full(hobj)

        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=1)

        # Old heartbeat
        hb1 = Heartbeat(heartbeat_time=old_time)
        hb1.add_holonicobject(hobj)
        hb1.build_prompt()
        hb1.process_response(f'{{"{hobj.id}": {{"actions": []}}}}')
        storage.save_heartbeat(hb1)

        # New heartbeat
        hb2 = Heartbeat(heartbeat_time=now)
        hb2.add_holonicobject(hobj)
        hb2.build_prompt()
        hb2.process_response(f'{{"{hobj.id}": {{"actions": []}}}}')
        storage.save_heartbeat(hb2)

        # Filter for recent only
        recent = storage.get_heartbeats(since=now - timedelta(minutes=5))
        assert len(recent) == 1

    def test_get_hobj_heartbeats(self, storage):
        """Test getting heartbeats for specific hobj."""
        hobj1 = HolonicObject()
        hobj2 = HolonicObject()
        storage.save_full(hobj1)
        storage.save_full(hobj2)

        # Heartbeat with hobj1 only
        hb1 = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hb1.add_holonicobject(hobj1)
        hb1.build_prompt()
        hb1.process_response(f'{{"{hobj1.id}": {{"actions": []}}}}')
        storage.save_heartbeat(hb1)

        # Heartbeat with hobj2 only
        hb2 = Heartbeat(heartbeat_time=datetime.now(timezone.utc))
        hb2.add_holonicobject(hobj2)
        hb2.build_prompt()
        hb2.process_response(f'{{"{hobj2.id}": {{"actions": []}}}}')
        storage.save_heartbeat(hb2)

        # Should only get hobj1's heartbeat
        hobj1_heartbeats = storage.get_hobj_heartbeats(hobj1.id)
        assert len(hobj1_heartbeats) == 1


class TestMessagePersistence:
    """Tests for message history."""

    def test_save_message(self, storage):
        """Test saving a message."""
        msg_id = storage.save_message(
            from_id="hobj-1",
            to_id="hobj-2",
            content="Hello!",
        )
        assert msg_id > 0

    def test_get_messages_sent(self, storage):
        """Test getting sent messages."""
        storage.save_message("hobj-1", "hobj-2", "Message 1")
        storage.save_message("hobj-1", "hobj-3", "Message 2")
        storage.save_message("hobj-2", "hobj-1", "Reply")

        sent = storage.get_messages("hobj-1", direction="sent")
        assert len(sent) == 2

    def test_get_messages_received(self, storage):
        """Test getting received messages."""
        storage.save_message("hobj-1", "hobj-2", "Message 1")
        storage.save_message("hobj-3", "hobj-2", "Message 2")

        received = storage.get_messages("hobj-2", direction="received")
        assert len(received) == 2

    def test_get_messages_both(self, storage):
        """Test getting all messages."""
        storage.save_message("hobj-1", "hobj-2", "Sent")
        storage.save_message("hobj-2", "hobj-1", "Received")

        all_msgs = storage.get_messages("hobj-1", direction="both")
        assert len(all_msgs) == 2


class TestTelemetryPersistence:
    """Tests for telemetry snapshots."""

    def test_save_telemetry(self, storage):
        """Test saving telemetry snapshot."""
        snapshot = {
            "heartbeats": {"count": 10},
            "ai_calls": {"count": 5},
        }
        snap_id = storage.save_telemetry_snapshot(snapshot)
        assert snap_id > 0

    def test_get_telemetry_snapshots(self, storage):
        """Test getting telemetry snapshots."""
        storage.save_telemetry_snapshot({"value": 1})
        storage.save_telemetry_snapshot({"value": 2})
        storage.save_telemetry_snapshot({"value": 3})

        snapshots = storage.get_telemetry_snapshots(limit=10)
        assert len(snapshots) == 3

        # Most recent first
        assert snapshots[0]["data"]["value"] == 3

    def test_get_telemetry_filtered(self, storage):
        """Test filtering telemetry by time."""
        storage.save_telemetry_snapshot({"old": True})

        from time import sleep
        sleep(0.1)
        cutoff = datetime.now(timezone.utc)
        sleep(0.1)

        storage.save_telemetry_snapshot({"new": True})

        recent = storage.get_telemetry_snapshots(since=cutoff)
        assert len(recent) == 1
        assert recent[0]["data"]["new"] is True
