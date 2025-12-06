"""
Storage layer for HolonicEngine.

Provides a generic SQL interface that works with SQLite, PostgreSQL, MySQL, etc.
"""

from .interface import HolonicStorage
from .sql import SQLStorage

__all__ = [
    "HolonicStorage",
    "SQLStorage",
]
