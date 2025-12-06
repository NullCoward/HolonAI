"""
Generic SQL storage implementation for HolonicEngine.

Works with SQLite, PostgreSQL, MySQL, and other SQLAlchemy-supported databases.
Supports encrypted SQLite via SQLCipher for portable .hln files.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, select, delete, update, and_, event
from sqlalchemy.engine import Engine

from .schema import (
    metadata,
    holons,
    hobjs,
    holon_references,
    heartbeats,
    heartbeat_hobjs,
    messages,
    telemetry_snapshots,
)

if TYPE_CHECKING:
    from ..agent import HolonicObject
    from ..heart import Heartbeat
    from ..holon import Holon


# Check if SQLCipher is available
_SQLCIPHER_AVAILABLE = False
try:
    import sqlcipher3
    _SQLCIPHER_AVAILABLE = True
except ImportError:
    pass


class SQLStorage:
    """
    Generic SQL storage backend using SQLAlchemy Core.

    Supports any SQLAlchemy-compatible database:
    - SQLite: "sqlite:///path/to/db.sqlite" or "sqlite:///:memory:"
    - Encrypted SQLite: SQLStorage("path/to/agent.hln", password="secret")
    - PostgreSQL: "postgresql://user:pass@host/dbname"
    - MySQL: "mysql://user:pass@host/dbname"
    """

    def __init__(
        self,
        connection_string: str = "sqlite:///:memory:",
        password: str | None = None,
    ):
        """
        Initialize storage with a database connection string.

        Args:
            connection_string: SQLAlchemy connection string, or just a file path
                for encrypted .hln files (e.g., "agent.hln" or "/path/to/agent.hln").
                Defaults to in-memory SQLite.
            password: Optional password for SQLCipher encryption.
                If provided with a file path, creates an encrypted database.
        """
        self._password = password
        self._file_path: str | None = None

        # If password provided and connection_string looks like a file path,
        # set up for encrypted SQLite
        if password and not connection_string.startswith(("sqlite:", "postgresql:", "mysql:")):
            self._file_path = connection_string
            self.connection_string = f"sqlite:///{connection_string}"
        else:
            self.connection_string = connection_string

        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine, creating it if needed."""
        if self._engine is None:
            raise RuntimeError("Storage not connected. Call connect() first.")
        return self._engine

    @property
    def is_encrypted(self) -> bool:
        """Check if this storage uses encryption."""
        return self._password is not None

    def connect(self) -> None:
        """Establish connection to the database."""
        if self._password and self.connection_string.startswith("sqlite:"):
            # Use SQLCipher for encrypted SQLite
            if not _SQLCIPHER_AVAILABLE:
                raise RuntimeError(
                    "SQLCipher not available. Install with: pip install sqlcipher3-binary"
                )
            # Create engine with SQLCipher
            self._engine = create_engine(
                self.connection_string,
                module=sqlcipher3.dbapi2,
            )
            # Set the encryption key on each connection
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute(f"PRAGMA key = '{self._password}'")
                cursor.close()
        else:
            self._engine = create_engine(self.connection_string)

    def disconnect(self) -> None:
        """Close connection to the database."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def create_tables(self) -> None:
        """Create all tables if they don't exist."""
        metadata.create_all(self.engine)

    # =========================================================================
    # Holon persistence (the "type" / template)
    # =========================================================================

    def save_holon(self, holon: "Holon") -> None:
        """Save a Holon's definition (purpose, actions)."""
        now = datetime.now(timezone.utc)

        # Serialize purpose and self_state bindings
        # Store only static values - lambdas/callables are dynamic references regenerated at runtime
        if hasattr(holon, '_purpose_bindings') and holon._purpose_bindings:
            static_bindings = {k: v for k, v in holon._purpose_bindings.items() if not callable(v)}
            purpose_json = json.dumps(static_bindings) if static_bindings else None
        elif holon.purpose:
            purpose_json = json.dumps(holon.purpose.serialize())
        else:
            purpose_json = None

        if hasattr(holon, '_self_bindings') and holon._self_bindings:
            static_bindings = {k: v for k, v in holon._self_bindings.items() if not callable(v)}
            self_state_json = json.dumps(static_bindings) if static_bindings else None
        elif holon.self_state:
            self_state_json = json.dumps(holon.self_state.serialize())
        else:
            self_state_json = None

        # Serialize actions - get the action signatures
        actions_data = []
        for action in holon.actions:
            action_data = {
                "name": action.name,
                "purpose": action.purpose,
            }
            if action.signature:
                action_data["parameters"] = [
                    {"name": p.name, "type": p.type_hint, "required": not p.has_default}
                    for p in action.signature.parameters
                ]
            actions_data.append(action_data)
        actions_json = json.dumps(actions_data) if actions_data else None

        with self.engine.connect() as conn:
            existing = conn.execute(
                select(holons.c.id).where(holons.c.id == holon.id)
            ).fetchone()

            if existing:
                conn.execute(
                    update(holons)
                    .where(holons.c.id == holon.id)
                    .values(
                        purpose=purpose_json,
                        self_state=self_state_json,
                        actions=actions_json,
                        updated_at=now,
                    )
                )
            else:
                conn.execute(
                    holons.insert().values(
                        id=holon.id,
                        purpose=purpose_json,
                        self_state=self_state_json,
                        actions=actions_json,
                        created_at=now,
                        updated_at=now,
                    )
                )
            conn.commit()

    def load_holon(self, holon_id: str) -> dict[str, Any] | None:
        """Load a Holon's definition by ID."""
        with self.engine.connect() as conn:
            row = conn.execute(
                select(holons).where(holons.c.id == holon_id)
            ).fetchone()

            if row is None:
                return None

            return {
                "id": row.id,
                "purpose": json.loads(row.purpose) if row.purpose else {},
                "self_state": json.loads(row.self_state) if row.self_state else {},
                "actions": json.loads(row.actions) if row.actions else [],
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    def delete_holon(self, holon_id: str) -> bool:
        """Delete a Holon from storage."""
        with self.engine.connect() as conn:
            result = conn.execute(
                delete(holons).where(holons.c.id == holon_id)
            )
            conn.commit()
            return result.rowcount > 0

    def list_holons(self) -> list[str]:
        """List all Holon IDs."""
        with self.engine.connect() as conn:
            result = conn.execute(select(holons.c.id))
            return [row.id for row in result]

    def get_holon_references(self, holon_id: str) -> list[dict[str, Any]]:
        """Get all hobjs that reference a holon."""
        with self.engine.connect() as conn:
            result = conn.execute(
                select(holon_references)
                .where(holon_references.c.holon_id == holon_id)
            )
            return [
                {
                    "hobj_id": row.hobj_id,
                    "reference_type": row.reference_type,
                    "created_at": row.created_at,
                }
                for row in result
            ]

    # =========================================================================
    # HolonicObject persistence (the instance / runtime state)
    # =========================================================================

    def save_hobj(self, hobj: "HolonicObject") -> None:
        """Save a HolonicObject's current state."""
        now = datetime.now(timezone.utc)

        knowledge_json = json.dumps(hobj.knowledge) if hobj.knowledge else None

        with self.engine.connect() as conn:
            existing = conn.execute(
                select(hobjs.c.id).where(hobjs.c.id == hobj.id)
            ).fetchone()

            if existing:
                conn.execute(
                    update(hobjs)
                    .where(hobjs.c.id == hobj.id)
                    .values(
                        holon_id=hobj.id,  # For now, hobj and holon share ID
                        parent_id=hobj.holon_parent.id if hobj.holon_parent else None,
                        knowledge=knowledge_json,
                        token_bank=hobj.token_bank,
                        heart_rate_secs=hobj.heart_rate_secs,
                        last_heartbeat=hobj.last_heartbeat,
                        next_heartbeat=hobj.next_heartbeat,
                        updated_at=now,
                    )
                )
            else:
                conn.execute(
                    hobjs.insert().values(
                        id=hobj.id,
                        holon_id=hobj.id,  # For now, hobj and holon share ID
                        parent_id=hobj.holon_parent.id if hobj.holon_parent else None,
                        knowledge=knowledge_json,
                        token_bank=hobj.token_bank,
                        heart_rate_secs=hobj.heart_rate_secs,
                        last_heartbeat=hobj.last_heartbeat,
                        next_heartbeat=hobj.next_heartbeat,
                        created_at=now,
                        updated_at=now,
                    )
                )
            conn.commit()

    def load_hobj(self, hobj_id: str) -> dict[str, Any] | None:
        """Load a HolonicObject's state by ID."""
        with self.engine.connect() as conn:
            row = conn.execute(
                select(hobjs).where(hobjs.c.id == hobj_id)
            ).fetchone()

            if row is None:
                return None

            return {
                "id": row.id,
                "holon_id": row.holon_id,
                "parent_id": row.parent_id,
                "knowledge": json.loads(row.knowledge) if row.knowledge else {},
                "token_bank": row.token_bank,
                "heart_rate_secs": row.heart_rate_secs,
                "last_heartbeat": row.last_heartbeat,
                "next_heartbeat": row.next_heartbeat,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    def delete_hobj(self, hobj_id: str) -> bool:
        """Delete a HolonicObject from storage."""
        with self.engine.connect() as conn:
            result = conn.execute(
                delete(hobjs).where(hobjs.c.id == hobj_id)
            )
            conn.commit()
            return result.rowcount > 0

    def list_hobjs(self, parent_id: str | None = None) -> list[str]:
        """List HolonicObject IDs by parent."""
        with self.engine.connect() as conn:
            if parent_id is None:
                result = conn.execute(
                    select(hobjs.c.id).where(hobjs.c.parent_id.is_(None))
                )
            else:
                result = conn.execute(
                    select(hobjs.c.id).where(hobjs.c.parent_id == parent_id)
                )
            return [row.id for row in result]

    def list_hobjs_by_holon(self, holon_id: str) -> list[str]:
        """List all HolonicObject IDs that use a specific Holon."""
        with self.engine.connect() as conn:
            result = conn.execute(
                select(hobjs.c.id).where(hobjs.c.holon_id == holon_id)
            )
            return [row.id for row in result]

    def load_tree(self, root_id: str) -> dict[str, Any] | None:
        """Load an entire holon tree starting from root_id."""
        root_data = self.load_hobj(root_id)
        if root_data is None:
            return None

        # Load the holon definition
        holon_data = self.load_holon(root_data.get("holon_id") or root_id)
        if holon_data:
            root_data["holon"] = holon_data

        # Recursively load children
        child_ids = self.list_hobjs(parent_id=root_id)
        root_data["children"] = [
            self.load_tree(child_id)
            for child_id in child_ids
        ]

        return root_data

    # =========================================================================
    # Holon references (for multi-reference scenarios)
    # =========================================================================

    def add_holon_reference(
        self,
        holon_id: str,
        hobj_id: str,
        reference_type: str = "primary",
    ) -> int:
        """Add a reference from a hobj to a holon."""
        now = datetime.now(timezone.utc)

        with self.engine.connect() as conn:
            result = conn.execute(
                holon_references.insert().values(
                    holon_id=holon_id,
                    hobj_id=hobj_id,
                    reference_type=reference_type,
                    created_at=now,
                )
            )
            conn.commit()
            return result.lastrowid

    def remove_holon_reference(self, holon_id: str, hobj_id: str) -> bool:
        """Remove a reference from a hobj to a holon."""
        with self.engine.connect() as conn:
            result = conn.execute(
                delete(holon_references).where(
                    and_(
                        holon_references.c.holon_id == holon_id,
                        holon_references.c.hobj_id == hobj_id,
                    )
                )
            )
            conn.commit()
            return result.rowcount > 0

    def get_hobj_holon_references(self, hobj_id: str) -> list[dict[str, Any]]:
        """Get all holons referenced by a hobj."""
        with self.engine.connect() as conn:
            result = conn.execute(
                select(holon_references)
                .where(holon_references.c.hobj_id == hobj_id)
            )
            return [
                {
                    "holon_id": row.holon_id,
                    "reference_type": row.reference_type,
                    "created_at": row.created_at,
                }
                for row in result
            ]

    # =========================================================================
    # Combined save/restore (saves both Holon and HolonicObject)
    # =========================================================================

    def save_full(self, hobj: "HolonicObject") -> None:
        """Save both the Holon definition and HolonicObject state."""
        self.save_holon(hobj)  # HolonicObject inherits from Holon
        self.save_hobj(hobj)

    def save_tree(self, root: "HolonicObject") -> int:
        """Save an entire holon tree recursively (both holons and hobjs)."""
        count = 0
        self.save_full(root)
        count += 1

        for child in root.holon_children:
            count += self.save_tree(child)

        return count

    def restore_hobj(self, hobj_id: str) -> "HolonicObject | None":
        """
        Restore a HolonicObject from storage.

        Creates a new HolonicObject instance with the stored state.
        Note: Does not restore parent/child relationships - use restore_tree for that.
        """
        from ..agent import HolonicObject

        hobj_data = self.load_hobj(hobj_id)
        if hobj_data is None:
            return None

        # Load holon definition if available
        holon_data = None
        if hobj_data.get("holon_id"):
            holon_data = self.load_holon(hobj_data["holon_id"])

        # Create hobj with stored ID
        hobj = HolonicObject()
        object.__setattr__(hobj, 'id', hobj_data['id'])

        # Restore hobj state
        hobj.knowledge.update(hobj_data['knowledge'])
        hobj.token_bank = hobj_data['token_bank']
        hobj.heart_rate_secs = hobj_data['heart_rate_secs']
        hobj.last_heartbeat = hobj_data['last_heartbeat']
        hobj.next_heartbeat = hobj_data['next_heartbeat']

        # Restore holon purpose bindings if available
        if holon_data and holon_data.get('purpose'):
            hobj._purpose_bindings.update(holon_data['purpose'])

        # Restore holon self_state bindings if available
        if holon_data and holon_data.get('self_state'):
            hobj._self_bindings.update(holon_data['self_state'])

        return hobj

    def restore_tree(self, root_id: str) -> "HolonicObject | None":
        """
        Restore an entire holon tree from storage.

        Creates HolonicObject instances and reconnects parent/child relationships.
        """
        tree_data = self.load_tree(root_id)
        if tree_data is None:
            return None

        return self._restore_tree_recursive(tree_data, parent=None)

    def _restore_tree_recursive(
        self,
        data: dict[str, Any],
        parent: "HolonicObject | None",
    ) -> "HolonicObject":
        """Recursively restore a holon tree."""
        from ..agent import HolonicObject, Message

        # Create hobj
        hobj = HolonicObject(holon_parent=parent)
        object.__setattr__(hobj, 'id', data['id'])

        # Restore hobj state
        hobj.knowledge.update(data['knowledge'])
        hobj.token_bank = data['token_bank']
        hobj.heart_rate_secs = data['heart_rate_secs']
        hobj.last_heartbeat = data['last_heartbeat']
        hobj.next_heartbeat = data['next_heartbeat']

        # Restore holon purpose if available
        if data.get('holon') and data['holon'].get('purpose'):
            hobj._purpose_bindings.update(data['holon']['purpose'])

        # Restore holon self_state if available
        if data.get('holon') and data['holon'].get('self_state'):
            hobj._self_bindings.update(data['holon']['self_state'])

        # Restore message history from storage
        stored_messages = self.get_messages(hobj.id, direction="both", limit=1000)
        for msg_data in stored_messages:
            message = Message(
                sender_id=msg_data['sender_id'],
                id=msg_data['id'],
                recipient_ids=msg_data['recipient_ids'],
                content=msg_data['content'],
                tokens_attached=msg_data['tokens_attached'],
                timestamp=msg_data['timestamp'],
            )
            hobj.message_history.add(message)

        # Restore children
        for child_data in data.get('children', []):
            child = self._restore_tree_recursive(child_data, parent=hobj)
            hobj.holon_children.append(child)

        return hobj

    # =========================================================================
    # Heartbeat history
    # =========================================================================

    def save_heartbeat(self, heartbeat: "Heartbeat") -> int:
        """Save a heartbeat record and its hobj participation."""
        now = datetime.now(timezone.utc)

        with self.engine.connect() as conn:
            result = conn.execute(
                heartbeats.insert().values(
                    heartbeat_time=heartbeat.heartbeat_time,
                    prompt=heartbeat.full_prompt,
                    response=heartbeat.raw_response,
                    hobj_count=len(heartbeat),
                    duration_ms=None,
                    created_at=now,
                )
            )
            heartbeat_id = result.lastrowid

            for hobj in heartbeat.get_holonicobjects():
                actions_result, hud_sent = heartbeat.get_results(hobj)
                conn.execute(
                    heartbeat_hobjs.insert().values(
                        heartbeat_id=heartbeat_id,
                        hobj_id=hobj.id,
                        hud_sent=json.dumps(hud_sent),
                        actions_result=json.dumps(actions_result),
                    )
                )

            conn.commit()
            return heartbeat_id

    def get_heartbeat(self, heartbeat_id: int) -> dict[str, Any] | None:
        """Get a specific heartbeat by ID."""
        with self.engine.connect() as conn:
            row = conn.execute(
                select(heartbeats).where(heartbeats.c.id == heartbeat_id)
            ).fetchone()

            if row is None:
                return None

            hobj_rows = conn.execute(
                select(heartbeat_hobjs).where(heartbeat_hobjs.c.heartbeat_id == heartbeat_id)
            ).fetchall()

            return {
                "id": row.id,
                "heartbeat_time": row.heartbeat_time,
                "prompt": row.prompt,
                "response": row.response,
                "hobj_count": row.hobj_count,
                "duration_ms": row.duration_ms,
                "hobjs": [
                    {
                        "hobj_id": hr.hobj_id,
                        "hud_sent": json.loads(hr.hud_sent) if hr.hud_sent else {},
                        "actions_result": json.loads(hr.actions_result) if hr.actions_result else {},
                    }
                    for hr in hobj_rows
                ],
            }

    def get_heartbeats(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get heartbeat history."""
        with self.engine.connect() as conn:
            query = select(heartbeats).order_by(heartbeats.c.heartbeat_time.desc())

            conditions = []
            if since is not None:
                conditions.append(heartbeats.c.heartbeat_time >= since)
            if until is not None:
                conditions.append(heartbeats.c.heartbeat_time <= until)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.limit(limit).offset(offset)
            rows = conn.execute(query).fetchall()

            return [
                {
                    "id": row.id,
                    "heartbeat_time": row.heartbeat_time,
                    "hobj_count": row.hobj_count,
                    "duration_ms": row.duration_ms,
                }
                for row in rows
            ]

    def get_hobj_heartbeats(
        self,
        hobj_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get heartbeat history for a specific hobj."""
        with self.engine.connect() as conn:
            query = (
                select(heartbeats, heartbeat_hobjs.c.hud_sent, heartbeat_hobjs.c.actions_result)
                .join(heartbeat_hobjs, heartbeats.c.id == heartbeat_hobjs.c.heartbeat_id)
                .where(heartbeat_hobjs.c.hobj_id == hobj_id)
                .order_by(heartbeats.c.heartbeat_time.desc())
                .limit(limit)
            )

            rows = conn.execute(query).fetchall()

            return [
                {
                    "heartbeat_id": row.id,
                    "heartbeat_time": row.heartbeat_time,
                    "hud_sent": json.loads(row.hud_sent) if row.hud_sent else {},
                    "actions_result": json.loads(row.actions_result) if row.actions_result else {},
                }
                for row in rows
            ]

    # =========================================================================
    # Message history
    # =========================================================================

    def save_message(
        self,
        message_id: str,
        sender_id: str,
        recipient_ids: list[str],
        content: Any,
        tokens_attached: int = 0,
        timestamp: datetime | None = None,
    ) -> None:
        """Save a message between hobjs."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        content_json = json.dumps(content) if not isinstance(content, str) else content

        with self.engine.connect() as conn:
            conn.execute(
                messages.insert().values(
                    id=message_id,
                    sender_id=sender_id,
                    recipient_ids=json.dumps(recipient_ids),
                    content=content_json,
                    tokens_attached=tokens_attached,
                    timestamp=timestamp,
                )
            )
            conn.commit()

    def get_messages(
        self,
        hobj_id: str,
        direction: str = "both",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get messages for a hobj."""
        with self.engine.connect() as conn:
            if direction == "sent":
                condition = messages.c.sender_id == hobj_id
            elif direction == "received":
                # Check if hobj_id is in the recipient_ids JSON array
                # This is a simple LIKE check - works for SQLite/PostgreSQL
                condition = messages.c.recipient_ids.contains(hobj_id)
            else:
                condition = (messages.c.sender_id == hobj_id) | messages.c.recipient_ids.contains(hobj_id)

            query = (
                select(messages)
                .where(condition)
                .order_by(messages.c.timestamp.desc())
                .limit(limit)
            )

            rows = conn.execute(query).fetchall()

            return [
                {
                    "id": row.id,
                    "sender_id": row.sender_id,
                    "recipient_ids": json.loads(row.recipient_ids),
                    "content": json.loads(row.content) if row.content.startswith('{') or row.content.startswith('[') else row.content,
                    "tokens_attached": row.tokens_attached,
                    "timestamp": row.timestamp,
                }
                for row in rows
            ]

    # =========================================================================
    # Telemetry
    # =========================================================================

    def save_telemetry_snapshot(self, snapshot: dict[str, Any]) -> int:
        """Save a telemetry snapshot."""
        now = datetime.now(timezone.utc)

        with self.engine.connect() as conn:
            result = conn.execute(
                telemetry_snapshots.insert().values(
                    snapshot_time=now,
                    data=json.dumps(snapshot),
                )
            )
            conn.commit()
            return result.lastrowid

    def get_telemetry_snapshots(
        self,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get telemetry snapshots."""
        with self.engine.connect() as conn:
            query = (
                select(telemetry_snapshots)
                .order_by(telemetry_snapshots.c.snapshot_time.desc())
            )

            if since is not None:
                query = query.where(telemetry_snapshots.c.snapshot_time >= since)

            query = query.limit(limit)
            rows = conn.execute(query).fetchall()

            return [
                {
                    "id": row.id,
                    "snapshot_time": row.snapshot_time,
                    "data": json.loads(row.data),
                }
                for row in rows
            ]

    # =========================================================================
    # Context manager
    # =========================================================================

    def __enter__(self) -> "SQLStorage":
        """Enter context manager - connect to database."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager - disconnect from database."""
        self.disconnect()
