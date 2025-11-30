"""
Token counting utilities for Holon.

Uses tiktoken for accurate token counting with OpenAI models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .holon import Holon

# Try to import tiktoken, gracefully degrade if not available
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False


# Default encoding for modern models (GPT-4o, GPT-4o-mini)
DEFAULT_ENCODING = "o200k_base"

# Model to encoding mapping for common models
MODEL_ENCODINGS = {
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "claude-3-opus": "cl100k_base",  # Approximation
    "claude-3-sonnet": "cl100k_base",  # Approximation
    "claude-3-haiku": "cl100k_base",  # Approximation
}


class TokenCounter:
    """
    Token counter using tiktoken.

    Caches encoders for efficiency.
    """

    _encoders: dict[str, "tiktoken.Encoding"] = {}

    @classmethod
    def get_encoder(cls, model: str | None = None, encoding: str | None = None) -> "tiktoken.Encoding":
        """
        Get a tiktoken encoder.

        Args:
            model: Model name (e.g., "gpt-4o") - will look up encoding
            encoding: Encoding name directly (e.g., "o200k_base")

        Returns:
            tiktoken Encoding instance
        """
        if not TIKTOKEN_AVAILABLE:
            raise ImportError(
                "Token counting requires the 'tiktoken' package. "
                "Install with: pip install tiktoken"
            )

        # Determine encoding to use
        if encoding:
            enc_name = encoding
        elif model:
            enc_name = MODEL_ENCODINGS.get(model, DEFAULT_ENCODING)
        else:
            enc_name = DEFAULT_ENCODING

        # Cache encoders
        if enc_name not in cls._encoders:
            cls._encoders[enc_name] = tiktoken.get_encoding(enc_name)

        return cls._encoders[enc_name]

    @classmethod
    def count(
        cls,
        text: str,
        *,
        model: str | None = None,
        encoding: str | None = None
    ) -> int:
        """
        Count tokens in a text string.

        Args:
            text: The text to tokenize
            model: Model name for encoding lookup
            encoding: Direct encoding name

        Returns:
            Number of tokens
        """
        encoder = cls.get_encoder(model=model, encoding=encoding)
        return len(encoder.encode(text))

    @classmethod
    def count_json(
        cls,
        data: dict,
        *,
        model: str | None = None,
        encoding: str | None = None
    ) -> int:
        """
        Count tokens in a JSON-serializable dict.

        Args:
            data: Dictionary to serialize and count
            model: Model name for encoding lookup
            encoding: Direct encoding name

        Returns:
            Number of tokens
        """
        import json
        text = json.dumps(data)
        return cls.count(text, model=model, encoding=encoding)


def count_tokens(
    text: str,
    *,
    model: str | None = None,
    encoding: str | None = None
) -> int:
    """
    Count tokens in a text string.

    Args:
        text: The text to tokenize
        model: Model name (e.g., "gpt-4o") for encoding lookup
        encoding: Direct encoding name (e.g., "o200k_base")

    Returns:
        Number of tokens
    """
    return TokenCounter.count(text, model=model, encoding=encoding)


def is_available() -> bool:
    """Check if token counting is available (tiktoken installed)."""
    return TIKTOKEN_AVAILABLE
