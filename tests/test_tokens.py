"""
Tests for token counting functionality.
"""

import pytest

from holon_ai import TokenCounter, count_tokens, tokens_available


class TestTokensAvailable:
    """Tests for tokens availability check."""

    def test_tokens_available(self):
        """Test that tiktoken is available."""
        # tiktoken is a required dependency, so this should be True
        assert tokens_available() is True


class TestTokenCounter:
    """Tests for TokenCounter class."""

    def test_count_simple_text(self):
        """Test counting tokens in simple text."""
        count = TokenCounter.count("Hello, world!")
        assert count > 0
        assert isinstance(count, int)

    def test_count_empty_string(self):
        """Test counting tokens in empty string."""
        count = TokenCounter.count("")
        assert count == 0

    def test_count_with_model(self):
        """Test counting with specific model."""
        text = "This is a test message for token counting."
        count_gpt4o = TokenCounter.count(text, model="gpt-4o")
        count_gpt4 = TokenCounter.count(text, model="gpt-4")
        # Both should return valid counts
        assert count_gpt4o > 0
        assert count_gpt4 > 0

    def test_count_with_encoding(self):
        """Test counting with specific encoding."""
        text = "Test message"
        count = TokenCounter.count(text, encoding="cl100k_base")
        assert count > 0

    def test_count_json(self):
        """Test counting tokens in JSON data."""
        data = {"name": "Alice", "age": 30, "items": [1, 2, 3]}
        count = TokenCounter.count_json(data)
        assert count > 0

    def test_count_json_with_model(self):
        """Test counting JSON with specific model."""
        data = {"key": "value"}
        count = TokenCounter.count_json(data, model="gpt-4o")
        assert count > 0

    def test_get_encoder_caching(self):
        """Test that encoders are cached."""
        enc1 = TokenCounter.get_encoder(model="gpt-4o")
        enc2 = TokenCounter.get_encoder(model="gpt-4o")
        assert enc1 is enc2  # Same cached instance

    def test_get_encoder_different_models(self):
        """Test different encoders for different model families."""
        enc_o200k = TokenCounter.get_encoder(encoding="o200k_base")
        enc_cl100k = TokenCounter.get_encoder(encoding="cl100k_base")
        # They should be different encoder instances
        assert enc_o200k is not enc_cl100k

    def test_default_encoding(self):
        """Test default encoding when no model specified."""
        enc = TokenCounter.get_encoder()
        # Default is o200k_base for modern models
        assert enc is not None


class TestCountTokensFunction:
    """Tests for the count_tokens convenience function."""

    def test_count_tokens_simple(self):
        """Test the convenience function."""
        count = count_tokens("Hello, world!")
        assert count > 0

    def test_count_tokens_with_model(self):
        """Test with model parameter."""
        count = count_tokens("Test", model="gpt-4o")
        assert count > 0

    def test_count_tokens_with_encoding(self):
        """Test with encoding parameter."""
        count = count_tokens("Test", encoding="cl100k_base")
        assert count > 0


class TestTokenCountingAccuracy:
    """Tests for token counting accuracy."""

    def test_known_token_count(self):
        """Test against known token counts."""
        # "Hello" is typically 1 token in most encodings
        count = count_tokens("Hello")
        assert count >= 1

    def test_longer_text_more_tokens(self):
        """Test that longer text has more tokens."""
        short = count_tokens("Hi")
        long = count_tokens("Hello, this is a much longer sentence with many words.")
        assert long > short

    def test_special_characters(self):
        """Test counting with special characters."""
        count = count_tokens("Hello! @#$%^&*() 你好")
        assert count > 0

    def test_code_snippet(self):
        """Test counting code."""
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        count = count_tokens(code)
        assert count > 0

    def test_json_structure(self):
        """Test that JSON structure tokens are counted."""
        simple = TokenCounter.count_json({"a": "b"})
        complex = TokenCounter.count_json({
            "a": "b",
            "c": {"d": "e", "f": [1, 2, 3]},
            "g": "longer string value"
        })
        assert complex > simple


class TestModelEncodings:
    """Tests for model-to-encoding mappings."""

    def test_gpt4o_encoding(self):
        """Test GPT-4o uses o200k_base."""
        text = "Test"
        count = TokenCounter.count(text, model="gpt-4o")
        count_direct = TokenCounter.count(text, encoding="o200k_base")
        assert count == count_direct

    def test_gpt4_encoding(self):
        """Test GPT-4 uses cl100k_base."""
        text = "Test"
        count = TokenCounter.count(text, model="gpt-4")
        count_direct = TokenCounter.count(text, encoding="cl100k_base")
        assert count == count_direct

    def test_unknown_model_uses_default(self):
        """Test unknown model falls back to default encoding."""
        text = "Test"
        count = TokenCounter.count(text, model="unknown-model-xyz")
        # Should not raise, uses default
        assert count > 0
