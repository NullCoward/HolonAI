"""
Tests for HolonBinding, HolonPurpose, HolonSelf, and HolonActions containers.
"""

import pytest
import attrs

from holon_ai import HolonAction, HolonBinding, HolonActions, HolonPurpose, HolonSelf


class TestHolonBinding:
    """Tests for HolonBinding class."""

    def test_static_value_binding(self):
        """Test binding to a static value."""
        binding = HolonBinding(source="hello")
        assert binding.resolve() == "hello"

    def test_static_dict_binding(self):
        """Test binding to a static dictionary."""
        data = {"name": "Alice", "age": 30}
        binding = HolonBinding(source=data)
        assert binding.resolve() == data

    def test_function_binding(self):
        """Test binding to a function that is called on resolve."""
        counter = {"value": 0}

        def get_count():
            counter["value"] += 1
            return counter["value"]

        binding = HolonBinding(source=get_count)
        assert binding.resolve() == 1
        assert binding.resolve() == 2  # Called again, increments

    def test_lambda_binding(self):
        """Test binding to a lambda."""
        binding = HolonBinding(source=lambda: {"timestamp": "now"})
        result = binding.resolve()
        assert result == {"timestamp": "now"}

    def test_keyed_binding(self):
        """Test binding with a key."""
        binding = HolonBinding(source={"x": 1}, key="data")
        assert binding.key == "data"
        assert binding.resolve() == {"x": 1}

    def test_class_instance_binding(self):
        """Test binding to a class instance uses __dict__."""
        class Person:
            def __init__(self, name, age):
                self.name = name
                self.age = age

        person = Person("Bob", 25)
        binding = HolonBinding(source=person)
        result = binding.resolve()
        assert result == {"name": "Bob", "age": 25}

    def test_attrs_class_binding(self):
        """Test binding to an attrs class."""
        @attrs.define
        class Config:
            host: str
            port: int

        config = Config(host="localhost", port=8080)
        binding = HolonBinding(source=config)
        result = binding.resolve()
        assert result == {"host": "localhost", "port": 8080}

    def test_list_binding(self):
        """Test binding to a list."""
        items = [1, 2, 3]
        binding = HolonBinding(source=items)
        assert binding.resolve() == [1, 2, 3]


class TestHolonPurpose:
    """Tests for HolonPurpose container."""

    def test_empty_purpose(self):
        """Test empty purpose container."""
        purpose = HolonPurpose()
        assert len(purpose) == 0
        assert purpose.serialize() == []

    def test_add_single_item(self):
        """Test adding a single item."""
        purpose = HolonPurpose()
        purpose.add("Be helpful")
        assert len(purpose) == 1
        assert purpose.resolve() == ["Be helpful"]

    def test_add_multiple_items(self):
        """Test adding multiple items."""
        purpose = HolonPurpose()
        purpose.add("Be helpful")
        purpose.add("Be concise")
        purpose.add("Be accurate")
        assert len(purpose) == 3
        assert purpose.serialize() == ["Be helpful", "Be concise", "Be accurate"]

    def test_fluent_api(self):
        """Test fluent API returns self."""
        purpose = HolonPurpose()
        result = purpose.add("item1").add("item2")
        assert result is purpose
        assert len(purpose) == 2

    def test_keyed_items_serialize_as_dict(self):
        """Test that all keyed items serialize as dict."""
        purpose = HolonPurpose()
        purpose.add("value1", key="key1")
        purpose.add("value2", key="key2")
        result = purpose.serialize()
        assert result == {"key1": "value1", "key2": "value2"}

    def test_unkeyed_items_serialize_as_list(self):
        """Test that unkeyed items serialize as list."""
        purpose = HolonPurpose()
        purpose.add("item1")
        purpose.add("item2")
        result = purpose.serialize()
        assert result == ["item1", "item2"]

    def test_mixed_items_serialize_as_mixed_list(self):
        """Test mixed keyed/unkeyed items."""
        purpose = HolonPurpose()
        purpose.add("unkeyed1")
        purpose.add("value1", key="key1")
        purpose.add("unkeyed2")
        result = purpose.serialize()
        assert result == ["unkeyed1", {"key1": "value1"}, "unkeyed2"]

    def test_iteration(self):
        """Test iterating over purpose items."""
        purpose = HolonPurpose()
        purpose.add("a").add("b").add("c")
        items = list(purpose)
        assert items == ["a", "b", "c"]

    def test_function_binding_resolved(self):
        """Test that function bindings are resolved."""
        purpose = HolonPurpose()
        purpose.add(lambda: "dynamic value")
        result = purpose.serialize()
        assert result == ["dynamic value"]


class TestHolonSelf:
    """Tests for HolonSelf container."""

    def test_empty_self(self):
        """Test empty self container."""
        self_state = HolonSelf()
        assert len(self_state) == 0
        assert self_state.serialize() == []

    def test_add_keyed_items(self):
        """Test adding keyed items."""
        self_state = HolonSelf()
        self_state.add({"name": "Alice"}, key="user")
        self_state.add(["task1", "task2"], key="tasks")
        result = self_state.serialize()
        assert result == {
            "user": {"name": "Alice"},
            "tasks": ["task1", "task2"]
        }

    def test_add_function_binding(self):
        """Test adding function that is called on serialize."""
        def get_user():
            return {"id": 1, "name": "Bob"}

        self_state = HolonSelf()
        self_state.add(get_user, key="current_user")
        result = self_state.serialize()
        assert result == {"current_user": {"id": 1, "name": "Bob"}}

    def test_nested_holon_serialization(self):
        """Test that nested Holons are serialized properly."""
        from holon_ai import Holon

        inner = Holon(name="InnerHolon")
        inner.add_purpose("Inner purpose")

        self_state = HolonSelf()
        self_state.add(inner, key="nested")
        result = self_state.serialize()

        # Nested holon should be serialized without name
        assert "nested" in result
        assert "purpose" in result["nested"]

    def test_fluent_api(self):
        """Test fluent API chaining."""
        self_state = HolonSelf()
        result = self_state.add("a", key="x").add("b", key="y")
        assert result is self_state

    def test_iteration(self):
        """Test iteration returns resolved values."""
        self_state = HolonSelf()
        self_state.add({"a": 1}, key="first")
        self_state.add({"b": 2}, key="second")
        items = list(self_state)
        assert items == [{"a": 1}, {"b": 2}]


class TestHolonActions:
    """Tests for HolonActions container."""

    def test_empty_actions(self):
        """Test empty actions container."""
        actions = HolonActions()
        assert len(actions) == 0

    def test_add_function(self):
        """Test adding a function directly."""
        def my_action(x: int) -> int:
            return x * 2

        actions = HolonActions()
        actions.add(my_action, name="my_action")
        assert len(actions) == 1
        assert "my_action" in actions

    def test_add_holon_action(self):
        """Test adding a HolonAction object."""
        def func():
            pass

        action = HolonAction(callback=func, name="custom_name")
        actions = HolonActions()
        actions.add(action)
        assert "custom_name" in actions

    def test_add_with_name_override(self):
        """Test adding function with name override."""
        def internal_func():
            pass

        actions = HolonActions()
        actions.add(internal_func, name="public_api")
        assert "public_api" in actions
        assert "internal_func" not in actions

    def test_add_with_purpose(self):
        """Test adding function with purpose."""
        def send_email(to: str, body: str) -> bool:
            return True

        actions = HolonActions()
        actions.add(send_email, name="send_email", purpose="Send an email notification")
        action = actions.get("send_email")
        assert action.purpose == "Send an email notification"

    def test_get_action(self):
        """Test getting action by name."""
        def my_action():
            return "result"

        actions = HolonActions()
        actions.add(my_action, name="my_action")
        action = actions.get("my_action")
        assert action is not None
        assert action.callback is my_action

    def test_get_nonexistent_action(self):
        """Test getting nonexistent action returns None."""
        actions = HolonActions()
        assert actions.get("nonexistent") is None

    def test_execute_action(self):
        """Test executing an action by name."""
        def add(a: int, b: int) -> int:
            return a + b

        actions = HolonActions()
        actions.add(add, name="add")
        result = actions.execute("add", a=5, b=3)
        assert result == 8

    def test_execute_nonexistent_action(self):
        """Test executing nonexistent action raises KeyError."""
        actions = HolonActions()
        with pytest.raises(KeyError, match="Action not found"):
            actions.execute("nonexistent")

    def test_iteration(self):
        """Test iterating over actions."""
        def action1():
            pass

        def action2():
            pass

        actions = HolonActions()
        actions.add(action1, name="action1").add(action2, name="action2")
        action_list = list(actions)
        assert len(action_list) == 2
        names = {a.name for a in action_list}
        assert "action1" in names
        assert "action2" in names

    def test_contains(self):
        """Test __contains__ method."""
        def my_action():
            pass

        actions = HolonActions()
        actions.add(my_action, name="my_action")
        assert "my_action" in actions
        assert "other" not in actions

    def test_fluent_api(self):
        """Test fluent API chaining."""
        def a():
            pass

        def b():
            pass

        actions = HolonActions()
        result = actions.add(a).add(b)
        assert result is actions
        assert len(actions) == 2
