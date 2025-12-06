"""
Abstract storage interface for HolonicEngine.

Defines the Protocol that all storage backends must implement.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ..agent import HolonicObject
    from ..heart import Heartbeat


class HolonicStorage(Protocol):
    """
    Abstract storage interface for persisting HolonicEngine state.

    Implementations can use any SQL database (SQLite, PostgreSQL, MySQL, etc.)
    or other storage backends.
    """

    # Connection management

    def connect(self) -> None:
        """Establish connection to the storage backend."""
        ...

    def disconnect(self) -> None:
        """Close connection to the storage backend."""
        ...

    def create_tables(self) -> None:
        """Create the required tables if they don't exist."""
        ...

    # HolonicObject persistence

    def save_hobj(self, hobj: "HolonicObject") -> None:
        """
        Save a HolonicObject's current state.

        Creates or updates the record based on hobj.id.
        """
        ...

    def load_hobj(self, hobj_id: str) -> dict[str, Any] | None:
        """
        Load a HolonicObject's state by ID.

        Returns the state dict or None if not found.
        """
        ...

    def delete_hobj(self, hobj_id: str) -> bool:
        """
        Delete a HolonicObject from storage.

        Returns True if deleted, False if not found.
        """
        ...

    def list_hobjs(self, parent_id: str | None = None) -> list[str]:
        """
        List HolonicObject IDs.

        Args:
            parent_id: If provided, only list children of this parent.
                       If None, list root hobjs (those with no parent).
        """
        ...

    def load_tree(self, root_id: str) -> dict[str, Any] | None:
        """
        Load an entire holon tree starting from root_id.

        Returns nested dict with 'children' containing child hobjs.
        """
        ...

    # Heartbeat history

    def save_heartbeat(self, heartbeat: "Heartbeat") -> int:
        """
        Save a heartbeat record.

        Returns the heartbeat ID.
        """
        ...

    def get_heartbeat(self, heartbeat_id: int) -> dict[str, Any] | None:
        """Get a specific heartbeat by ID."""
        ...

    def get_heartbeats(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get heartbeat history.

        Args:
            since: Only heartbeats after this time
            until: Only heartbeats before this time
            limit: Maximum number of results
            offset: Skip this many results
        """
        ...

    def get_hobj_heartbeats(
        self,
        hobj_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get heartbeat history for a specific hobj."""
        ...

    # Message history

    def save_message(
        self,
        from_id: str,
        to_id: str,
        content: str,
        timestamp: datetime | None = None,
    ) -> int:
        """
        Save a message between hobjs.

        Returns the message ID.
        """
        ...

    def get_messages(
        self,
        hobj_id: str,
        direction: str = "both",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get messages for a hobj.

        Args:
            hobj_id: The hobj to get messages for
            direction: "sent", "received", or "both"
            limit: Maximum number of results
        """
        ...

    # Telemetry

    def save_telemetry_snapshot(self, snapshot: dict[str, Any]) -> int:
        """
        Save a telemetry snapshot.

        Returns the snapshot ID.
        """
        ...

    def get_telemetry_snapshots(
        self,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get telemetry snapshots."""
        ...

    # Bulk operations

    def save_tree(self, root: "HolonicObject") -> int:
        """
        Save an entire holon tree.

        Recursively saves root and all children.
        Returns the number of hobjs saved.
        """
        ...
