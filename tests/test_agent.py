"""
Tests for the HolonicObject class.
"""

import pytest

from holonic_engine import (
    Holon,
    HolonicObject,
    Message,
    MessageHistory,
)


class TestHolonicObjectCreation:
    """Tests for HolonicObject instantiation."""

    def test_create_object(self):
        """Test creating a basic object."""
        obj = HolonicObject()
        assert obj.id is not None
        assert len(obj.id) == 36  # UUID format
        assert isinstance(obj, Holon)  # HolonicObject IS-A Holon
        assert obj.holon_children == []
        assert obj.knowledge == {}

    def test_object_has_unique_id(self):
        """Test that each object has a unique ID."""
        obj1 = HolonicObject()
        obj2 = HolonicObject()
        assert obj1.id != obj2.id


class TestChildManagement:
    """Tests for child object management."""

    def test_create_child(self):
        """Test creating a child object."""
        parent = HolonicObject()
        child = parent.create_child()

        assert len(parent.holon_children) == 1
        assert parent.holon_children[0] is child
        assert isinstance(child, HolonicObject)
        assert child.holon_parent is parent

    def test_create_child_unique_id(self):
        """Test that child has unique ID."""
        parent = HolonicObject()
        child = parent.create_child()
        assert child.id != parent.id

    def test_create_multiple_children(self):
        """Test creating multiple children."""
        parent = HolonicObject()
        child1 = parent.create_child()
        child2 = parent.create_child()

        assert len(parent.holon_children) == 2
        assert child1.id != child2.id

    def test_get_child(self):
        """Test getting a child by GUID."""
        parent = HolonicObject()
        child = parent.create_child()

        found = parent.get_child(child.id)
        assert found is child

    def test_get_child_not_found(self):
        """Test getting nonexistent child returns None."""
        parent = HolonicObject()
        assert parent.get_child("nonexistent-guid") is None

    def test_remove_child(self):
        """Test removing a child."""
        parent = HolonicObject()
        child = parent.create_child()
        child_id = child.id

        result = parent.remove_child(child_id)
        assert result is True
        assert len(parent.holon_children) == 0

    def test_remove_child_not_found(self):
        """Test removing nonexistent child returns False."""
        parent = HolonicObject()
        result = parent.remove_child("nonexistent-guid")
        assert result is False


class TestKnowledgeManagement:
    """Tests for knowledge JSON path operations."""

    def test_knowledge_set_simple(self):
        """Test setting a simple value."""
        obj = HolonicObject()
        obj.knowledge_set("name", "Alice")
        assert obj.knowledge == {"name": "Alice"}

    def test_knowledge_set_nested(self):
        """Test setting a nested value."""
        obj = HolonicObject()
        obj.knowledge_set("user.name", "Alice")
        assert obj.knowledge == {"user": {"name": "Alice"}}

    def test_knowledge_set_deeply_nested(self):
        """Test setting a deeply nested value."""
        obj = HolonicObject()
        obj.knowledge_set("a.b.c.d", "value")
        assert obj.knowledge == {"a": {"b": {"c": {"d": "value"}}}}

    def test_knowledge_get_simple(self):
        """Test getting a simple value."""
        obj = HolonicObject()
        obj.knowledge = {"name": "Alice"}
        assert obj.knowledge_get("name") == "Alice"

    def test_knowledge_get_nested(self):
        """Test getting a nested value."""
        obj = HolonicObject()
        obj.knowledge = {"user": {"name": "Alice"}}
        assert obj.knowledge_get("user.name") == "Alice"

    def test_knowledge_get_all(self):
        """Test getting entire knowledge with empty path."""
        obj = HolonicObject()
        obj.knowledge = {"key": "value"}
        assert obj.knowledge_get("") == {"key": "value"}

    def test_knowledge_get_not_found(self):
        """Test getting nonexistent path raises KeyError."""
        obj = HolonicObject()
        with pytest.raises(KeyError):
            obj.knowledge_get("nonexistent")

    def test_knowledge_delete(self):
        """Test deleting a value."""
        obj = HolonicObject()
        obj.knowledge = {"name": "Alice", "age": 30}
        obj.knowledge_delete("age")
        assert obj.knowledge == {"name": "Alice"}

    def test_knowledge_delete_nested(self):
        """Test deleting a nested value."""
        obj = HolonicObject()
        obj.knowledge = {"user": {"name": "Alice", "age": 30}}
        obj.knowledge_delete("user.age")
        assert obj.knowledge == {"user": {"name": "Alice"}}

    def test_knowledge_delete_not_found(self):
        """Test deleting nonexistent path raises KeyError."""
        obj = HolonicObject()
        with pytest.raises(KeyError):
            obj.knowledge_delete("nonexistent")

    def test_knowledge_move(self):
        """Test moving a value."""
        obj = HolonicObject()
        obj.knowledge = {"old": "value"}
        obj.knowledge_move("old", "new")
        assert obj.knowledge == {"new": "value"}

    def test_knowledge_move_nested(self):
        """Test moving a nested value."""
        obj = HolonicObject()
        obj.knowledge = {"a": {"x": "value"}}
        obj.knowledge_move("a.x", "b.y")
        assert obj.knowledge == {"a": {}, "b": {"y": "value"}}

    def test_knowledge_exists(self):
        """Test checking if path exists."""
        obj = HolonicObject()
        obj.knowledge = {"name": "Alice"}
        assert obj.knowledge_exists("name") is True
        assert obj.knowledge_exists("nonexistent") is False


class TestPurposeManagement:
    """Tests for purpose JSON path operations."""

    def test_purpose_set_simple(self):
        """Test setting a simple purpose value."""
        obj = HolonicObject()
        obj.purpose_set("role", "Be helpful")
        assert obj.purpose_get() == {"role": "Be helpful"}

    def test_purpose_set_nested(self):
        """Test setting a nested purpose value."""
        obj = HolonicObject()
        obj.purpose_set("constraints.tone", "Be concise")
        assert obj.purpose_get() == {"constraints": {"tone": "Be concise"}}

    def test_purpose_get_simple(self):
        """Test getting a simple purpose value."""
        obj = HolonicObject()
        obj.purpose_set("role", "Assistant")
        assert obj.purpose_get("role") == "Assistant"

    def test_purpose_get_all(self):
        """Test getting entire purpose with empty path."""
        obj = HolonicObject()
        obj.purpose_set("role", "Assistant")
        assert obj.purpose_get("") == {"role": "Assistant"}

    def test_purpose_delete(self):
        """Test deleting a purpose value."""
        obj = HolonicObject()
        obj.purpose_set("role", "Assistant")
        obj.purpose_set("tone", "Friendly")
        obj.purpose_delete("tone")
        assert obj.purpose_get() == {"role": "Assistant"}

    def test_purpose_exists(self):
        """Test checking if purpose path exists."""
        obj = HolonicObject()
        obj.purpose_set("role", "Assistant")
        assert obj.purpose_exists("role") is True
        assert obj.purpose_exists("nonexistent") is False


class TestChildPurposeManagement:
    """Tests for managing children's purpose."""

    def test_child_purpose_set(self):
        """Test setting purpose on child."""
        parent = HolonicObject()
        child = parent.create_child()

        parent.child_purpose_set(child.id, "role", "Worker")
        assert child.purpose_get() == {"role": "Worker"}

    def test_child_purpose_set_not_found(self):
        """Test setting purpose on nonexistent child raises KeyError."""
        parent = HolonicObject()
        with pytest.raises(KeyError, match="not found"):
            parent.child_purpose_set("nonexistent-guid", "role", "Worker")

    def test_child_purpose_clear(self):
        """Test clearing child's purpose."""
        parent = HolonicObject()
        child = parent.create_child()
        child.purpose_set("role", "Worker")
        child.purpose_set("tone", "Friendly")

        parent.child_purpose_clear(child.id)
        assert child.purpose_get() == {}

    def test_child_purpose_get(self):
        """Test getting child's purpose."""
        parent = HolonicObject()
        child = parent.create_child()
        child.purpose_set("role", "Worker")

        result = parent.child_purpose_get(child.id)
        assert result == {"role": "Worker"}


class TestMessageHistory:
    """Tests for MessageHistory class."""

    def test_message_history_empty(self):
        """Test empty message history."""
        history = MessageHistory()
        assert len(history) == 0
        assert history.get_all() == []

    def test_message_history_add(self):
        """Test adding messages."""
        history = MessageHistory()
        msg = Message(sender_id="sender-1")
        history.add(msg)
        assert len(history) == 1

    def test_message_history_clear(self):
        """Test clearing messages."""
        history = MessageHistory()
        history.add(Message(sender_id="sender-1"))
        history.clear()
        assert len(history) == 0


class TestMessaging:
    """Tests for inter-object messaging."""

    def test_send_message_to_child(self):
        """Test sending message to child object."""
        parent = HolonicObject()
        child = parent.create_child()

        msg = parent.send_message(child.id, "Hello!")

        assert msg.sender_id == parent.id
        assert child.id in msg.recipient_ids
        assert msg.content == "Hello!"

    def test_send_message_to_parent(self):
        """Test sending message to parent object."""
        parent = HolonicObject()
        child = parent.create_child()

        msg = child.send_message(parent.id, "Hello boss!")

        assert msg.sender_id == child.id
        assert parent.id in msg.recipient_ids

    def test_send_message_multiple_recipients(self):
        """Test sending message to multiple recipients in tree."""
        parent = HolonicObject()
        child1 = parent.create_child()
        child2 = parent.create_child()

        msg = parent.send_message([child1.id, child2.id], "Broadcast")

        assert len(msg.recipient_ids) == 2
        assert child1.id in msg.recipient_ids
        assert child2.id in msg.recipient_ids

    def test_message_in_sender_history(self):
        """Test that sent message is in sender's history."""
        parent = HolonicObject()
        child = parent.create_child()

        parent.send_message(child.id, "Test")

        sent = parent.get_sent_messages()
        assert len(sent) == 1
        assert sent[0].content == "Test"

    def test_message_in_receiver_history(self):
        """Test that message is delivered to receiver in tree."""
        parent = HolonicObject()
        child = parent.create_child()

        parent.send_message(child.id, "Test")

        received = child.get_received_messages()
        assert len(received) == 1
        assert received[0].content == "Test"

    def test_message_has_timestamp(self):
        """Test that messages have timestamps."""
        parent = HolonicObject()
        child = parent.create_child()

        msg = parent.send_message(child.id, "Test")

        assert msg.timestamp is not None

    def test_message_has_unique_id(self):
        """Test that each message has unique ID."""
        parent = HolonicObject()
        child = parent.create_child()

        msg1 = parent.send_message(child.id, "First")
        msg2 = parent.send_message(child.id, "Second")

        assert msg1.id != msg2.id

    def test_sibling_messaging(self):
        """Test messaging between sibling objects."""
        parent = HolonicObject()
        child1 = parent.create_child()
        child2 = parent.create_child()

        msg = child1.send_message(child2.id, "Hey sibling!")

        received = child2.get_received_messages()
        assert len(received) == 1
        assert received[0].content == "Hey sibling!"

    def test_add_message_direct(self):
        """Test add_message adds to local history only."""
        obj = HolonicObject()
        msg = Message(sender_id="external", content="Direct add")

        obj.add_message(msg)

        assert len(obj.get_messages()) == 1
        assert obj.get_messages()[0].content == "Direct add"


class TestSelfSerialization:
    """Tests for self serialization."""

    def test_self_shows_holon_id(self):
        """Test that holon_id is directly in self."""
        obj = HolonicObject()
        data = obj.to_dict()
        assert data["self"]["holon_id"] == obj.id

    def test_tree_shows_children_with_token_bank(self):
        """Test that holon_children include id and token_bank."""
        parent = HolonicObject()
        child1 = parent.create_child()
        child1.token_bank = 100
        child2 = parent.create_child()
        child2.token_bank = -50

        tree = parent._get_holon_relationships()
        child_ids = [c["id"] for c in tree["holon_children"]]
        assert child1.id in child_ids
        assert child2.id in child_ids

        # Check token_bank is included
        for child_ref in tree["holon_children"]:
            if child_ref["id"] == child1.id:
                assert child_ref["token_bank"] == 100
            elif child_ref["id"] == child2.id:
                assert child_ref["token_bank"] == -50

    def test_tree_shows_parent_with_token_bank(self):
        """Test that holon_parent includes id and token_bank."""
        parent = HolonicObject()
        parent.token_bank = 500
        child = parent.create_child()

        tree = child._get_holon_relationships()
        assert tree["holon_parent"]["id"] == parent.id
        assert tree["holon_parent"]["token_bank"] == 500

    def test_root_has_no_parent_in_tree(self):
        """Test that root object has no holon_parent."""
        obj = HolonicObject()
        tree = obj._get_holon_relationships()
        assert "holon_parent" not in tree


class TestHeartbeat:
    """Tests for heartbeat functionality."""

    def test_object_has_next_heartbeat(self):
        """Test that new object has next_heartbeat set to now."""
        from datetime import datetime, timezone, timedelta
        obj = HolonicObject()
        now = datetime.now(timezone.utc)
        # Should be within a second of now
        assert abs((obj.next_heartbeat - now).total_seconds()) < 1

    def test_object_has_no_last_heartbeat(self):
        """Test that new object has no last_heartbeat."""
        obj = HolonicObject()
        assert obj.last_heartbeat is None

    def test_set_next_heartbeat(self):
        """Test setting next heartbeat time."""
        from datetime import datetime, timezone, timedelta
        obj = HolonicObject()
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        obj.set_next_heartbeat(future)
        assert obj.next_heartbeat == future

    def test_collect_due_heartbeats_single(self):
        """Test collecting heartbeats from single holon."""
        obj = HolonicObject()
        heartbeats = obj.collect_due_heartbeats()
        assert len(heartbeats) == 1
        assert heartbeats[0][0] is obj
        assert heartbeats[0][1] == obj.next_heartbeat

    def test_collect_due_heartbeats_with_children(self):
        """Test collecting heartbeats from holon with children."""
        parent = HolonicObject()
        child1 = parent.create_child()
        child2 = parent.create_child()

        heartbeats = parent.collect_due_heartbeats()
        assert len(heartbeats) == 3

        holons = [h[0] for h in heartbeats]
        assert parent in holons
        assert child1 in holons
        assert child2 in holons

    def test_collect_due_heartbeats_nested(self):
        """Test collecting heartbeats from nested hierarchy."""
        root = HolonicObject()
        child = root.create_child()
        grandchild = child.create_child()

        heartbeats = root.collect_due_heartbeats()
        assert len(heartbeats) == 3

        holons = [h[0] for h in heartbeats]
        assert root in holons
        assert child in holons
        assert grandchild in holons

    def test_action_results_updates_last_heartbeat(self):
        """Test that action_results updates last_heartbeat."""
        from datetime import datetime, timezone
        obj = HolonicObject()
        now = datetime.now(timezone.utc)

        obj.action_results({"actions": []}, now)

        assert obj.last_heartbeat == now

    def test_action_results_updates_next_heartbeat(self):
        """Test that action_results sets next_heartbeat based on heart_rate_secs."""
        from datetime import datetime, timezone, timedelta
        obj = HolonicObject()
        obj.heart_rate_secs = 5
        now = datetime.now(timezone.utc)

        obj.action_results({"actions": []}, now)

        assert obj.next_heartbeat == now + timedelta(seconds=5)

    def test_default_heart_rate_secs(self):
        """Test that default heart_rate_secs is 1."""
        obj = HolonicObject()
        assert obj.heart_rate_secs == 1

    def test_heart_rate_in_serialization(self):
        """Test that heart_rate_secs appears in serialization."""
        obj = HolonicObject()
        obj.heart_rate_secs = 10
        data = obj.to_dict()
        assert data["self"]["heart_rate_secs"] == 10

    def test_heartbeat_in_serialization(self):
        """Test that heartbeat timestamps appear in serialization."""
        obj = HolonicObject()
        data = obj.to_dict()

        assert "last_heartbeat" in data["self"]
        assert "next_heartbeat" in data["self"]
        assert data["self"]["last_heartbeat"] is None
        assert data["self"]["next_heartbeat"] is not None


class TestDynamicPurposeBinding:
    """Tests for dynamic purpose binding."""

    def test_purpose_with_callable(self):
        """Test that purpose can contain callable that resolves at serialization."""
        obj = HolonicObject()
        counter = [0]

        def get_count():
            counter[0] += 1
            return counter[0]

        obj.purpose_set("count", get_count)

        # Each purpose_get should call the function
        assert obj.purpose_get("count") == 1
        assert obj.purpose_get("count") == 2

    def test_purpose_callable_in_serialization(self):
        """Test that callable in purpose resolves during to_dict()."""
        obj = HolonicObject()
        obj.purpose_set("dynamic", lambda: "resolved_value")

        data = obj.to_dict()
        assert data["purpose"]["dynamic"] == "resolved_value"

    def test_purpose_nested_callable(self):
        """Test callable in nested purpose structure."""
        obj = HolonicObject()
        obj.purpose_set("outer.inner", lambda: "nested_value")

        data = obj.to_dict()
        assert data["purpose"]["outer"]["inner"] == "nested_value"
