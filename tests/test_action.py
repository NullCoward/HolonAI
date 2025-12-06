"""
Tests for HolonAction, ActionParameter, and ActionSignature.
"""

import pytest

from holonic_engine import ActionParameter, ActionSignature, HolonAction


class TestActionParameter:
    """Tests for ActionParameter dataclass."""

    def test_basic_parameter(self):
        """Test creating a basic parameter."""
        param = ActionParameter(name="x")
        assert param.name == "x"
        assert param.type_hint is None
        assert param.default is None
        assert param.has_default is False

    def test_parameter_with_type_hint(self):
        """Test parameter with type hint."""
        param = ActionParameter(name="count", type_hint="int")
        assert param.name == "count"
        assert param.type_hint == "int"

    def test_parameter_with_default(self):
        """Test parameter with default value."""
        param = ActionParameter(
            name="limit",
            type_hint="int",
            default=10,
            has_default=True
        )
        assert param.name == "limit"
        assert param.default == 10
        assert param.has_default is True

    def test_parameter_with_none_default(self):
        """Test parameter where None is an explicit default."""
        param = ActionParameter(
            name="optional",
            type_hint="str | None",
            default=None,
            has_default=True
        )
        assert param.default is None
        assert param.has_default is True


class TestActionSignature:
    """Tests for ActionSignature class."""

    def test_from_simple_function(self):
        """Test extracting signature from a simple function."""
        def simple_func(x: int, y: str) -> bool:
            """A simple function."""
            return True

        sig = ActionSignature.from_callable(simple_func)
        assert len(sig.parameters) == 2
        assert sig.parameters[0].name == "x"
        assert sig.parameters[0].type_hint == "int"
        assert sig.parameters[1].name == "y"
        assert sig.parameters[1].type_hint == "str"
        assert sig.return_type == "bool"
        assert sig.docstring == "A simple function."

    def test_from_function_with_defaults(self):
        """Test extracting signature with default values."""
        def with_defaults(a: int, b: str = "hello", c: bool = False) -> None:
            pass

        sig = ActionSignature.from_callable(with_defaults)
        assert sig.parameters[0].has_default is False
        assert sig.parameters[1].has_default is True
        assert sig.parameters[1].default == "hello"
        assert sig.parameters[2].has_default is True
        assert sig.parameters[2].default is False

    def test_from_function_no_annotations(self):
        """Test function without type annotations."""
        def no_annotations(x, y):
            return x + y

        sig = ActionSignature.from_callable(no_annotations)
        assert sig.parameters[0].type_hint is None
        assert sig.parameters[1].type_hint is None
        assert sig.return_type is None

    def test_from_function_complex_types(self):
        """Test function with complex type annotations."""
        def complex_types(items: list[str], mapping: dict[str, int]) -> list[int]:
            """Process items."""
            return []

        sig = ActionSignature.from_callable(complex_types)
        assert "list" in sig.parameters[0].type_hint.lower()
        assert "dict" in sig.parameters[1].type_hint.lower()

    def test_from_lambda(self):
        """Test extracting signature from a lambda."""
        func = lambda x, y: x + y
        sig = ActionSignature.from_callable(func)
        assert len(sig.parameters) == 2
        assert sig.parameters[0].name == "x"


class TestHolonAction:
    """Tests for HolonAction class."""

    def test_basic_action(self):
        """Test creating a basic action."""
        def my_action(x: int) -> int:
            """Double a number."""
            return x * 2

        action = HolonAction(callback=my_action)
        # Name includes module path for non-__main__ modules
        assert "my_action" in action.name
        assert action.signature is not None
        assert action.signature.docstring == "Double a number."

    def test_action_with_custom_name(self):
        """Test action with custom name override."""
        def internal_func():
            pass

        action = HolonAction(callback=internal_func, name="public_name")
        assert action.name == "public_name"

    def test_action_with_purpose(self):
        """Test action with purpose description."""
        def send_email(to: str, subject: str) -> bool:
            return True

        action = HolonAction(
            callback=send_email,
            purpose="Send an email to a user"
        )
        assert action.purpose == "Send an email to a user"

    def test_action_execute(self):
        """Test executing an action."""
        def add(a: int, b: int) -> int:
            return a + b

        action = HolonAction(callback=add)
        result = action.execute(a=5, b=3)
        assert result == 8

    def test_action_execute_with_defaults(self):
        """Test executing action with default parameters."""
        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        action = HolonAction(callback=greet)
        result = action.execute(name="Alice")
        assert result == "Hello, Alice!"

        result = action.execute(name="Bob", greeting="Hi")
        assert result == "Hi, Bob!"

    def test_action_name_derivation_module(self):
        """Test that action name includes module for non-main functions."""
        # Import a function from the module
        from holonic_engine.tokens import count_tokens
        action = HolonAction(callback=count_tokens)
        assert "holonic_engine.tokens" in action.name

    def test_action_with_lambda(self):
        """Test action created from lambda."""
        action = HolonAction(callback=lambda x: x * 2)
        # Lambda names include module path
        assert "<lambda>" in action.name
        assert action.execute(x=5) == 10

    def test_action_with_class_method(self):
        """Test action with a method."""
        class Calculator:
            def add(self, a: int, b: int) -> int:
                """Add two numbers."""
                return a + b

        calc = Calculator()
        action = HolonAction(callback=calc.add)
        assert "add" in action.name
        result = action.execute(a=2, b=3)
        assert result == 5
