"""
Tests for the core Holon class.
"""

import json

import pytest

from holonic_engine import Holon


class TestHolonCreation:
    """Tests for Holon instantiation."""

    def test_create_empty_holon(self):
        """Test creating an empty Holon."""
        holon = Holon()
        assert holon.name is None
        assert len(holon.purpose) == 0
        assert len(holon.self_state) == 0
        assert len(holon.actions) == 0

    def test_create_named_holon(self):
        """Test creating a named Holon."""
        holon = Holon(name="TestHolon")
        assert holon.name == "TestHolon"

    def test_holon_with_token_settings(self):
        """Test creating Holon with token settings."""
        holon = Holon(name="Test", token_limit=4000, model="gpt-4o")
        assert holon.token_limit == 4000
        assert holon.model == "gpt-4o"


class TestHolonFluentAPI:
    """Tests for the fluent builder API."""

    def test_add_purpose(self):
        """Test adding purpose items."""
        holon = Holon()
        result = holon.add_purpose("Be helpful")
        assert result is holon  # Returns self for chaining
        assert len(holon.purpose) == 1

    def test_add_purpose_chain(self):
        """Test chaining multiple purpose additions."""
        holon = (
            Holon(name="Test")
            .add_purpose("First")
            .add_purpose("Second")
            .add_purpose("Third")
        )
        assert len(holon.purpose) == 3

    def test_add_purpose_with_key(self):
        """Test adding keyed purpose item."""
        holon = Holon().add_purpose("value", key="mykey")
        serialized = holon.purpose.serialize()
        assert serialized == {"mykey": "value"}

    def test_add_self(self):
        """Test adding self state items."""
        holon = Holon()
        holon.add_self({"name": "Alice"}, key="user")
        assert len(holon.self_state) == 1

    def test_add_self_with_function(self):
        """Test adding function to self state."""
        def get_data():
            return {"value": 42}

        holon = Holon().add_self(get_data, key="dynamic")
        serialized = holon.self_state.serialize()
        assert serialized == {"dynamic": {"value": 42}}

    def test_add_action(self):
        """Test adding an action."""
        def my_action(x: int) -> int:
            return x * 2

        holon = Holon().add_action(my_action, name="my_action")
        assert len(holon.actions) == 1
        assert "my_action" in holon.actions

    def test_add_action_with_name(self):
        """Test adding action with custom name."""
        def internal_func():
            pass

        holon = Holon().add_action(internal_func, name="public_name")
        assert "public_name" in holon.actions

    def test_add_action_with_purpose(self):
        """Test adding action with purpose description."""
        def send_email(to: str) -> bool:
            return True

        holon = Holon().add_action(send_email, name="send_email", purpose="Send an email")
        action = holon.actions.get("send_email")
        assert action.purpose == "Send an email"

    def test_with_token_limit(self):
        """Test setting token limit."""
        holon = Holon().with_token_limit(8000)
        assert holon.token_limit == 8000

    def test_with_token_limit_and_model(self):
        """Test setting token limit with model."""
        holon = Holon().with_token_limit(4000, model="gpt-4o")
        assert holon.token_limit == 4000
        assert holon.model == "gpt-4o"

    def test_full_fluent_chain(self):
        """Test complete fluent API chain."""
        def get_user():
            return {"id": 1}

        def perform_action(x: int) -> str:
            return f"Result: {x}"

        holon = (
            Holon(name="CompleteHolon")
            .add_purpose("Main purpose")
            .add_purpose("Secondary purpose")
            .add_self(get_user, key="user")
            .add_self({"setting": True}, key="config")
            .add_action(perform_action, purpose="Do something")
            .with_token_limit(4000, model="gpt-4o")
        )

        assert holon.name == "CompleteHolon"
        assert len(holon.purpose) == 2
        assert len(holon.self_state) == 2
        assert len(holon.actions) == 1
        assert holon.token_limit == 4000


class TestHolonSerialization:
    """Tests for Holon serialization."""

    def test_to_dict_empty(self):
        """Test serializing empty Holon."""
        holon = Holon()
        result = holon.to_dict()
        assert result == {}

    def test_to_dict_with_name(self):
        """Test serializing named Holon."""
        holon = Holon(name="TestHolon")
        result = holon.to_dict()
        assert result == {"name": "TestHolon"}

    def test_to_dict_with_purpose(self):
        """Test serializing Holon with purpose."""
        holon = Holon(name="Test").add_purpose("Be helpful")
        result = holon.to_dict()
        assert result["name"] == "Test"
        assert result["purpose"] == ["Be helpful"]

    def test_to_dict_with_self(self):
        """Test serializing Holon with self state."""
        holon = Holon().add_self({"value": 42}, key="data")
        result = holon.to_dict()
        assert result["self"] == {"data": {"value": 42}}

    def test_to_dict_with_actions(self):
        """Test serializing Holon with actions."""
        def my_action(x: int) -> str:
            """Do something."""
            return str(x)

        holon = Holon().add_action(my_action, name="my_action", purpose="Test action")
        result = holon.to_dict()
        assert "actions" in result
        assert len(result["actions"]) == 1
        assert result["actions"][0]["name"] == "my_action"
        assert result["actions"][0]["purpose"] == "Test action"

    def test_to_dict_nested_flag(self):
        """Test that nested=True omits name."""
        holon = Holon(name="Nested")
        result = holon.to_dict(nested=True)
        assert "name" not in result

    def test_to_json(self):
        """Test JSON serialization."""
        holon = Holon(name="Test").add_purpose("Purpose")
        json_str = holon.to_json()
        data = json.loads(json_str)
        assert data["name"] == "Test"
        assert data["purpose"] == ["Purpose"]

    def test_to_json_with_indent(self):
        """Test JSON serialization with indent."""
        holon = Holon(name="Test")
        json_str = holon.to_json(indent=2)
        assert "\n" in json_str  # Indented has newlines


class TestHolonTokenManagement:
    """Tests for Holon token counting and management."""

    def test_token_count(self):
        """Test getting token count."""
        holon = (
            Holon(name="Test")
            .add_purpose("Be helpful and accurate")
            .add_self({"user": "Alice"}, key="context")
            .with_token_limit(4000, model="gpt-4o")
        )
        count = holon.token_count
        assert count > 0
        assert isinstance(count, int)

    def test_tokens_remaining_no_limit(self):
        """Test tokens_remaining with no limit."""
        holon = Holon(name="Test")
        assert holon.tokens_remaining is None

    def test_tokens_remaining_with_limit(self):
        """Test tokens_remaining with limit set."""
        holon = Holon(name="Test").with_token_limit(4000, model="gpt-4o")
        remaining = holon.tokens_remaining
        assert remaining is not None
        assert remaining < 4000
        assert remaining > 0

    def test_is_over_limit_no_limit(self):
        """Test is_over_limit with no limit."""
        holon = Holon(name="Test")
        assert holon.is_over_limit is False

    def test_is_over_limit_under(self):
        """Test is_over_limit when under limit."""
        holon = Holon(name="Test").with_token_limit(10000)
        assert holon.is_over_limit is False

    def test_is_over_limit_over(self):
        """Test is_over_limit when over limit."""
        # Create a small limit to trigger over
        holon = Holon(name="Test").with_token_limit(1)
        assert holon.is_over_limit is True

    def test_token_usage_dict(self):
        """Test token_usage returns proper dict."""
        holon = Holon(name="Test").with_token_limit(4000, model="gpt-4o")
        usage = holon.token_usage
        assert "count" in usage
        assert "limit" in usage
        assert "model" in usage
        assert "remaining" in usage
        assert "over_limit" in usage
        assert "percentage" in usage
        assert usage["limit"] == 4000
        assert usage["model"] == "gpt-4o"

    def test_token_usage_no_limit(self):
        """Test token_usage with no limit."""
        holon = Holon(name="Test")
        usage = holon.token_usage
        assert usage["limit"] is None
        assert usage["remaining"] is None
        assert usage["over_limit"] is False
        assert usage["percentage"] is None


class TestHolonDispatch:
    """Tests for Holon action dispatch."""

    def test_dispatch_simple(self):
        """Test dispatching a simple action."""
        def add(a: int, b: int) -> int:
            return a + b

        holon = Holon().add_action(add, name="add")
        result = holon.dispatch("add", a=5, b=3)
        assert result == 8

    def test_dispatch_with_defaults(self):
        """Test dispatching action with defaults."""
        def greet(user_name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {user_name}!"

        holon = Holon().add_action(greet, name="greet")
        result = holon.dispatch("greet", user_name="Alice")
        assert result == "Hello, Alice!"

    def test_dispatch_nonexistent_action(self):
        """Test dispatching nonexistent action."""
        holon = Holon()
        with pytest.raises(KeyError):
            holon.dispatch("nonexistent")

    def test_dispatch_many(self):
        """Test dispatching multiple actions."""
        def add(a: int, b: int) -> int:
            return a + b

        def multiply(x: int, y: int) -> int:
            return x * y

        holon = Holon().add_action(add, name="add").add_action(multiply, name="multiply")
        calls = [
            {"action": "add", "params": {"a": 2, "b": 3}},
            {"action": "multiply", "params": {"x": 4, "y": 5}},
        ]
        results = holon.dispatch_many(calls)
        assert results == [5, 20]

    def test_dispatch_many_empty(self):
        """Test dispatching empty list."""
        holon = Holon()
        results = holon.dispatch_many([])
        assert results == []


class TestNestedHolons:
    """Tests for nested Holon structures."""

    def test_nested_holon_in_self(self):
        """Test nesting a Holon in self state."""
        inner = Holon(name="Inner").add_purpose("Inner purpose")
        outer = Holon(name="Outer").add_self(inner, key="nested")

        result = outer.to_dict()
        assert "self" in result
        assert "nested" in result["self"]
        # Nested holon should not have name in output
        assert "name" not in result["self"]["nested"]
        assert result["self"]["nested"]["purpose"] == ["Inner purpose"]

    def test_deeply_nested_holons(self):
        """Test deeply nested Holon structures."""
        level3 = Holon(name="Level3").add_purpose("Deepest")
        level2 = Holon(name="Level2").add_self(level3, key="child")
        level1 = Holon(name="Level1").add_self(level2, key="child")

        result = level1.to_dict()
        assert result["self"]["child"]["self"]["child"]["purpose"] == ["Deepest"]
