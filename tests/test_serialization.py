"""
Tests for serialization utilities and HolonConverter.
"""

import json

import pytest

from holon_ai import (
    Holon,
    HolonConverter,
    holon_converter,
    serialize_for_ai,
    parse_ai_response,
    estimate_token_savings,
)


class TestHolonConverter:
    """Tests for HolonConverter class."""

    def test_converter_singleton(self):
        """Test that holon_converter is a usable instance."""
        assert isinstance(holon_converter, HolonConverter)

    def test_unstructure_holon_empty(self):
        """Test unstructuring empty Holon."""
        holon = Holon()
        result = holon_converter.unstructure_holon(holon)
        assert result == {}

    def test_unstructure_holon_with_name(self):
        """Test unstructuring named Holon."""
        holon = Holon(name="MyHolon")
        result = holon_converter.unstructure_holon(holon)
        assert result == {"name": "MyHolon"}

    def test_unstructure_holon_nested_omits_name(self):
        """Test that nested=True omits name."""
        holon = Holon(name="Nested")
        result = holon_converter.unstructure_holon(holon, nested=True)
        assert "name" not in result

    def test_unstructure_action_parameter(self):
        """Test unstructuring action parameters."""
        def my_func(x: int, y: str = "default") -> bool:
            """My function."""
            return True

        holon = Holon().add_action(my_func)
        result = holon_converter.unstructure_holon(holon)

        action = result["actions"][0]
        params = action["parameters"]

        assert len(params) == 2
        assert params[0] == {"name": "x", "type": "int"}
        assert params[1] == {"name": "y", "type": "str", "default": "default"}

    def test_unstructure_action_with_docstring(self):
        """Test that docstrings are included."""
        def documented_func(x: int) -> str:
            """This is the docstring."""
            return str(x)

        holon = Holon().add_action(documented_func)
        result = holon_converter.unstructure_holon(holon)
        assert result["actions"][0]["docstring"] == "This is the docstring."

    def test_unstructure_action_with_return_type(self):
        """Test that return types are included."""
        def typed_func(x: int) -> list[str]:
            return []

        holon = Holon().add_action(typed_func)
        result = holon_converter.unstructure_holon(holon)
        assert "returns" in result["actions"][0]

    def test_unstructure_purpose_as_list(self):
        """Test purpose serializes as list when unkeyed."""
        holon = Holon().add_purpose("First").add_purpose("Second")
        result = holon_converter.unstructure_holon(holon)
        assert result["purpose"] == ["First", "Second"]

    def test_unstructure_purpose_as_dict(self):
        """Test purpose serializes as dict when all keyed."""
        holon = Holon()
        holon.add_purpose("value1", key="key1")
        holon.add_purpose("value2", key="key2")
        result = holon_converter.unstructure_holon(holon)
        assert result["purpose"] == {"key1": "value1", "key2": "value2"}

    def test_unstructure_self_as_dict(self):
        """Test self serializes as dict when keyed."""
        holon = Holon()
        holon.add_self({"name": "Alice"}, key="user")
        holon.add_self([1, 2, 3], key="items")
        result = holon_converter.unstructure_holon(holon)
        assert result["self"] == {
            "user": {"name": "Alice"},
            "items": [1, 2, 3]
        }


class TestSerializeForAI:
    """Tests for serialize_for_ai function."""

    def test_serialize_json_format(self):
        """Test JSON serialization."""
        holon = Holon(name="Test").add_purpose("Be helpful")
        result = serialize_for_ai(holon, format="json")
        data = json.loads(result)
        assert data["name"] == "Test"
        assert data["purpose"] == ["Be helpful"]

    def test_serialize_toon_format(self):
        """Test TOON serialization (or fallback to JSON)."""
        holon = Holon(name="Test").add_purpose("Be helpful")
        result = serialize_for_ai(holon, format="toon")
        # Result should be a non-empty string
        assert len(result) > 0
        assert "Test" in result

    def test_serialize_unknown_format(self):
        """Test that unknown format raises error."""
        holon = Holon(name="Test")
        with pytest.raises(ValueError, match="Unknown format"):
            serialize_for_ai(holon, format="xml")

    def test_serialize_default_format(self):
        """Test default format is toon."""
        holon = Holon(name="Test")
        result = serialize_for_ai(holon)
        assert len(result) > 0

    def test_serialize_complete_holon(self):
        """Test serializing a complete Holon."""
        def my_action(x: int) -> int:
            """Double a number."""
            return x * 2

        holon = (
            Holon(name="Complete")
            .add_purpose("Main purpose")
            .add_self({"key": "value"}, key="data")
            .add_action(my_action, name="my_action", purpose="Double input")
        )

        result = serialize_for_ai(holon, format="json")
        data = json.loads(result)

        assert data["name"] == "Complete"
        assert "purpose" in data
        assert "self" in data
        assert "actions" in data


class TestParseAIResponse:
    """Tests for parse_ai_response function."""

    def test_parse_single_action_dict(self):
        """Test parsing single action from dict."""
        response = {"action": "my_action", "params": {"x": 5}}
        result = parse_ai_response(response)
        assert result == [{"action": "my_action", "params": {"x": 5}}]

    def test_parse_single_action_string(self):
        """Test parsing single action from JSON string."""
        response = '{"action": "my_action", "params": {"x": 5}}'
        result = parse_ai_response(response)
        assert result == [{"action": "my_action", "params": {"x": 5}}]

    def test_parse_multiple_actions_dict(self):
        """Test parsing multiple actions from dict."""
        response = {
            "actions": [
                {"action": "action1", "params": {"a": 1}},
                {"action": "action2", "params": {"b": 2}},
            ]
        }
        result = parse_ai_response(response)
        assert len(result) == 2
        assert result[0]["action"] == "action1"
        assert result[1]["action"] == "action2"

    def test_parse_multiple_actions_string(self):
        """Test parsing multiple actions from JSON string."""
        response = json.dumps({
            "actions": [
                {"action": "action1", "params": {}},
                {"action": "action2", "params": {}},
            ]
        })
        result = parse_ai_response(response)
        assert len(result) == 2

    def test_parse_invalid_format(self):
        """Test parsing invalid format raises error."""
        response = {"invalid": "format"}
        with pytest.raises(ValueError, match="Invalid AI response format"):
            parse_ai_response(response)

    def test_parse_empty_params(self):
        """Test parsing action with empty params."""
        response = {"action": "no_params_action", "params": {}}
        result = parse_ai_response(response)
        assert result[0]["params"] == {}

    def test_parse_missing_params(self):
        """Test parsing action without params key."""
        response = {"action": "simple_action"}
        result = parse_ai_response(response)
        assert result == [{"action": "simple_action"}]


class TestEstimateTokenSavings:
    """Tests for estimate_token_savings function."""

    def test_estimate_returns_dict(self):
        """Test that estimate returns a dict with comparison data."""
        holon = (
            Holon(name="Test")
            .add_purpose("Be helpful")
            .add_self({"key": "value"}, key="data")
        )
        try:
            result = estimate_token_savings(holon)
            assert isinstance(result, dict)
            # toon.compare_formats should return comparison stats
        except (ImportError, AttributeError):
            # python-toon may not have compare_formats
            pytest.skip("python-toon compare_formats not available")


class TestRoundTrip:
    """Tests for serialization round-trips."""

    def test_serialize_deserialize_actions(self):
        """Test that serialized actions can be parsed back."""
        def add(a: int, b: int) -> int:
            return a + b

        holon = Holon(name="Test").add_action(add, name="add", purpose="Add numbers")
        serialized = serialize_for_ai(holon, format="json")
        data = json.loads(serialized)

        # Simulate AI response calling the action
        ai_response = {
            "action": data["actions"][0]["name"],
            "params": {"a": 5, "b": 3}
        }

        # Parse the response
        calls = parse_ai_response(ai_response)

        # Dispatch the action
        result = holon.dispatch_many(calls)
        assert result == [8]

    def test_full_workflow(self):
        """Test complete workflow: build -> serialize -> parse -> dispatch."""
        results_log = []

        def log_message(message: str, level: str = "info") -> dict:
            """Log a message."""
            entry = {"message": message, "level": level}
            results_log.append(entry)
            return entry

        def get_status() -> dict:
            """Get system status."""
            return {"status": "ok", "logs": len(results_log)}

        holon = (
            Holon(name="Logger")
            .add_purpose("Log messages and track status")
            .add_self(lambda: {"log_count": len(results_log)}, key="state")
            .add_action(log_message, name="log_message", purpose="Log a message")
            .add_action(get_status, name="get_status", purpose="Get current status")
        )

        # Serialize for AI
        serialized = serialize_for_ai(holon, format="json")
        data = json.loads(serialized)

        assert data["name"] == "Logger"
        assert len(data["actions"]) == 2

        # Simulate AI response with multiple actions
        ai_response = {
            "actions": [
                {"action": "log_message", "params": {"message": "Hello", "level": "info"}},
                {"action": "log_message", "params": {"message": "Error!", "level": "error"}},
                {"action": "get_status", "params": {}},
            ]
        }

        # Parse and dispatch
        calls = parse_ai_response(ai_response)
        results = holon.dispatch_many(calls)

        assert len(results) == 3
        assert results[0] == {"message": "Hello", "level": "info"}
        assert results[1] == {"message": "Error!", "level": "error"}
        assert results[2] == {"status": "ok", "logs": 2}
