"""
Storage layer for HolonicEngine.

Provides a generic SQL interface that works with SQLite, PostgreSQL, MySQL, etc.
Supports encrypted .hln files via SQLCipher.
"""

from .interface import HolonicStorage
from .sql import SQLStorage, _SQLCIPHER_AVAILABLE


def is_encryption_available() -> bool:
    """Check if SQLCipher encryption is available."""
    return _SQLCIPHER_AVAILABLE


def open_hln(file_path: str, password: str) -> SQLStorage:
    """
    Open or create an encrypted .hln holon storage file.

    Args:
        file_path: Path to the .hln file (e.g., "agent.hln")
        password: Encryption password

    Returns:
        Connected SQLStorage instance ready for use

    Example:
        storage = open_hln("my_agent.hln", "secret")
        storage.create_tables()  # Only needed for new files
        root = storage.restore_tree(root_id)  # Or create new holons
    """
    storage = SQLStorage(file_path, password=password)
    storage.connect()
    return storage


__all__ = [
    "HolonicStorage",
    "SQLStorage",
    "is_encryption_available",
    "open_hln",
]
