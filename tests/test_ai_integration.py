"""
Integration tests that actually chat with AI APIs.

These tests require API keys to be set as environment variables:
- OPENAI_API_KEY for OpenAI tests
- ANTHROPIC_API_KEY for Anthropic/Claude tests

Tests are skipped if API keys are not available.
"""

import json
import os

import pytest

from holonic_engine import Holon, serialize_for_ai, parse_ai_response


# Check for API availability
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Try to import API clients
try:
    import openai
    OPENAI_AVAILABLE = OPENAI_API_KEY is not None
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = ANTHROPIC_API_KEY is not None
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False


# Sample actions for testing
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


def multiply_numbers(x: int, y: int) -> int:
    """Multiply two numbers together."""
    return x * y


def greet_user(name: str, formal: bool = False) -> str:
    """Generate a greeting for a user."""
    if formal:
        return f"Good day, {name}."
    return f"Hello, {name}!"


def get_weather(city: str) -> dict:
    """Get mock weather data for a city."""
    return {
        "city": city,
        "temperature": 72,
        "conditions": "sunny",
        "unit": "fahrenheit"
    }


def create_test_holon() -> Holon:
    """Create a test Holon with sample actions."""
    return (
        Holon(name="TestAssistant")
        .add_purpose("You are a helpful assistant that can perform calculations and greet users.")
        .add_purpose("When asked to perform an action, respond with a JSON object containing the action name and parameters.")
        .add_purpose("Format your response as: {\"action\": \"action_name\", \"params\": {\"param1\": value1, ...}}")
        .add_self({"user": "TestUser", "context": "integration_test"}, key="session")
        .add_action(add_numbers, name="add_numbers", purpose="Add two numbers together")
        .add_action(multiply_numbers, name="multiply_numbers", purpose="Multiply two numbers")
        .add_action(greet_user, name="greet_user", purpose="Generate a greeting")
        .add_action(get_weather, name="get_weather", purpose="Get weather for a city")
        .with_token_limit(4000, model="gpt-4o")
    )


class TestOpenAIIntegration:
    """Integration tests using OpenAI API."""

    @pytest.fixture
    def client(self):
        """Create OpenAI client."""
        if not OPENAI_AVAILABLE:
            pytest.skip("OpenAI API not available (set OPENAI_API_KEY)")
        return openai.OpenAI()

    @pytest.fixture
    def holon(self):
        """Create test Holon."""
        return create_test_holon()

    def test_simple_calculation(self, client, holon):
        """Test AI can call add_numbers action."""
        context = serialize_for_ai(holon, format="json")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are an AI assistant. Here is your context:\n{context}\n\nRespond ONLY with valid JSON for action calls."
                },
                {
                    "role": "user",
                    "content": "Please add 15 and 27 together."
                }
            ],
            temperature=0,
        )

        # Parse the AI response
        ai_text = response.choices[0].message.content
        # Extract JSON from response (may have markdown code blocks)
        if "```" in ai_text:
            # Extract JSON from code block
            start = ai_text.find("{")
            end = ai_text.rfind("}") + 1
            ai_text = ai_text[start:end]

        action_calls = parse_ai_response(ai_text)
        results = holon.dispatch_many(action_calls)

        assert len(results) == 1
        assert results[0] == 42  # 15 + 27

    def test_greeting_with_parameter(self, client, holon):
        """Test AI can call greet_user with parameters."""
        context = serialize_for_ai(holon, format="json")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are an AI assistant. Here is your context:\n{context}\n\nRespond ONLY with valid JSON for action calls."
                },
                {
                    "role": "user",
                    "content": "Please greet Alice formally."
                }
            ],
            temperature=0,
        )

        ai_text = response.choices[0].message.content
        if "```" in ai_text:
            start = ai_text.find("{")
            end = ai_text.rfind("}") + 1
            ai_text = ai_text[start:end]

        action_calls = parse_ai_response(ai_text)
        results = holon.dispatch_many(action_calls)

        assert len(results) == 1
        assert "Alice" in results[0]

    def test_multiple_actions(self, client, holon):
        """Test AI can call multiple actions."""
        context = serialize_for_ai(holon, format="json")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are an AI assistant. Here is your context:\n{context}\n\nWhen asked for multiple actions, respond with: {{\"actions\": [{{\"action\": \"name\", \"params\": {{...}}}}, ...]}}"
                },
                {
                    "role": "user",
                    "content": "Add 5 and 3, then multiply 4 by 6."
                }
            ],
            temperature=0,
        )

        ai_text = response.choices[0].message.content
        if "```" in ai_text:
            start = ai_text.find("{")
            end = ai_text.rfind("}") + 1
            ai_text = ai_text[start:end]

        action_calls = parse_ai_response(ai_text)
        results = holon.dispatch_many(action_calls)

        # Should have two results
        assert len(results) == 2
        assert 8 in results  # 5 + 3
        assert 24 in results  # 4 * 6


class TestAnthropicIntegration:
    """Integration tests using Anthropic Claude API."""

    @pytest.fixture
    def client(self):
        """Create Anthropic client."""
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("Anthropic API not available (set ANTHROPIC_API_KEY)")
        return anthropic.Anthropic()

    @pytest.fixture
    def holon(self):
        """Create test Holon."""
        return create_test_holon()

    def test_simple_calculation(self, client, holon):
        """Test Claude can call add_numbers action."""
        context = serialize_for_ai(holon, format="json")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=f"You are an AI assistant. Here is your context:\n{context}\n\nRespond ONLY with valid JSON for action calls, no additional text.",
            messages=[
                {
                    "role": "user",
                    "content": "Please add 100 and 50 together."
                }
            ],
        )

        ai_text = response.content[0].text
        # Extract JSON from response
        if "```" in ai_text:
            start = ai_text.find("{")
            end = ai_text.rfind("}") + 1
            ai_text = ai_text[start:end]

        action_calls = parse_ai_response(ai_text)
        results = holon.dispatch_many(action_calls)

        assert len(results) == 1
        assert results[0] == 150  # 100 + 50

    def test_weather_lookup(self, client, holon):
        """Test Claude can call get_weather action."""
        context = serialize_for_ai(holon, format="json")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=f"You are an AI assistant. Here is your context:\n{context}\n\nRespond ONLY with valid JSON for action calls.",
            messages=[
                {
                    "role": "user",
                    "content": "What's the weather in Seattle?"
                }
            ],
        )

        ai_text = response.content[0].text
        if "```" in ai_text:
            start = ai_text.find("{")
            end = ai_text.rfind("}") + 1
            ai_text = ai_text[start:end]

        action_calls = parse_ai_response(ai_text)
        results = holon.dispatch_many(action_calls)

        assert len(results) == 1
        assert results[0]["city"] == "Seattle"
        assert "temperature" in results[0]

    def test_greeting_action(self, client, holon):
        """Test Claude can call greet_user action."""
        context = serialize_for_ai(holon, format="json")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=f"You are an AI assistant. Here is your context:\n{context}\n\nRespond ONLY with valid JSON for action calls.",
            messages=[
                {
                    "role": "user",
                    "content": "Please greet Bob casually."
                }
            ],
        )

        ai_text = response.content[0].text
        if "```" in ai_text:
            start = ai_text.find("{")
            end = ai_text.rfind("}") + 1
            ai_text = ai_text[start:end]

        action_calls = parse_ai_response(ai_text)
        results = holon.dispatch_many(action_calls)

        assert len(results) == 1
        assert "Bob" in results[0]


class TestComplexIntegration:
    """Complex integration tests with either API."""

    @pytest.fixture
    def ai_client(self):
        """Get any available AI client."""
        if OPENAI_AVAILABLE:
            return ("openai", openai.OpenAI())
        elif ANTHROPIC_AVAILABLE:
            return ("anthropic", anthropic.Anthropic())
        else:
            pytest.skip("No AI API available")

    def test_dynamic_self_state(self, ai_client):
        """Test that dynamic self state is resolved correctly."""
        api_type, client = ai_client

        counter = {"value": 0}

        def get_counter():
            counter["value"] += 1
            return counter["value"]

        def increment() -> int:
            """Increment the counter."""
            counter["value"] += 1
            return counter["value"]

        holon = (
            Holon(name="Counter")
            .add_purpose("You manage a counter. Respond with JSON action calls only.")
            .add_self(get_counter, key="current_count")
            .add_action(increment, name="increment", purpose="Increment the counter by 1")
        )

        context = serialize_for_ai(holon, format="json")
        data = json.loads(context)

        # Check that the counter was called during serialization
        assert data["self"]["current_count"] == 1

        # Call again - should increment
        context2 = serialize_for_ai(holon, format="json")
        data2 = json.loads(context2)
        assert data2["self"]["current_count"] == 2

    def test_token_aware_holon(self, ai_client):
        """Test Holon with token awareness."""
        api_type, client = ai_client

        holon = (
            Holon(name="TokenAware")
            .add_purpose("Be concise")
            .add_self({"data": "x" * 100}, key="payload")
            .with_token_limit(1000, model="gpt-4o")
        )

        usage = holon.token_usage
        assert usage["count"] > 0
        assert usage["limit"] == 1000
        assert usage["percentage"] is not None
        assert usage["over_limit"] is False

    def test_nested_holon_serialization(self, ai_client):
        """Test that nested Holons serialize correctly for AI."""
        api_type, client = ai_client

        inner = (
            Holon(name="InnerModule")
            .add_purpose("Handle internal logic")
            .add_self({"status": "active"}, key="state")
        )

        outer = (
            Holon(name="OuterModule")
            .add_purpose("Coordinate modules")
            .add_self(inner, key="submodule")
        )

        context = serialize_for_ai(outer, format="json")
        data = json.loads(context)

        # Outer name should be present
        assert data["name"] == "OuterModule"

        # Inner should be nested without its own name
        assert "submodule" in data["self"]
        assert "name" not in data["self"]["submodule"]
        assert data["self"]["submodule"]["self"]["state"]["status"] == "active"


class TestErrorHandling:
    """Test error handling in AI integration."""

    @pytest.fixture
    def ai_client(self):
        """Get any available AI client."""
        if OPENAI_AVAILABLE:
            return ("openai", openai.OpenAI())
        elif ANTHROPIC_AVAILABLE:
            return ("anthropic", anthropic.Anthropic())
        else:
            pytest.skip("No AI API available")

    def test_invalid_action_dispatch(self, ai_client):
        """Test handling of invalid action name."""
        holon = create_test_holon()

        # Simulate AI returning invalid action
        invalid_response = {"action": "nonexistent_action", "params": {}}
        calls = parse_ai_response(invalid_response)

        with pytest.raises(KeyError, match="Action not found"):
            holon.dispatch_many(calls)

    def test_missing_required_params(self, ai_client):
        """Test handling of missing required parameters."""
        holon = create_test_holon()

        # Simulate AI returning action with missing params
        bad_response = {"action": "add_numbers", "params": {"a": 5}}  # missing 'b'
        calls = parse_ai_response(bad_response)

        with pytest.raises(TypeError):
            holon.dispatch_many(calls)


# Convenience markers for running specific test groups
pytestmark = [
    pytest.mark.integration,
]
