"""
SQLAlchemy schema definitions for HolonicEngine storage.

Uses SQLAlchemy Core (not ORM) for portability across SQL databases.

Schema separation:
- holons: The Holon "type" - purpose, actions, structure (can be referenced by multiple hobjs)
- hobjs: The HolonicObject instance - knowledge, tokens, heartbeat state, hierarchy
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

# Shared metadata for all tables
metadata = MetaData()

# Holon definitions (the "type" or "template")
holons = Table(
    "holons",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("purpose", Text, nullable=True),  # JSON - purpose bindings
    Column("self_state", Text, nullable=True),  # JSON - self state bindings
    Column("actions", Text, nullable=True),  # JSON - action definitions
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

# HolonicObject instances (the runtime state)
hobjs = Table(
    "hobjs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("holon_id", String(36), ForeignKey("holons.id", ondelete="SET NULL"), nullable=True),
    Column("parent_id", String(36), ForeignKey("hobjs.id", ondelete="SET NULL"), nullable=True),
    Column("knowledge", Text, nullable=True),  # JSON - instance state
    Column("token_bank", Integer, default=0),
    Column("heart_rate_secs", Integer, default=1),
    Column("last_heartbeat", DateTime, nullable=True),
    Column("next_heartbeat", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Index("ix_hobjs_holon_id", "holon_id"),
    Index("ix_hobjs_parent_id", "parent_id"),
)

# Track which hobjs reference which holons (for multi-reference scenarios)
holon_references = Table(
    "holon_references",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("holon_id", String(36), ForeignKey("holons.id", ondelete="CASCADE"), nullable=False),
    Column("hobj_id", String(36), ForeignKey("hobjs.id", ondelete="CASCADE"), nullable=False),
    Column("reference_type", String(50), nullable=False),  # e.g., "primary", "inherited", "shared"
    Column("created_at", DateTime, nullable=False),
    Index("ix_holon_refs_holon", "holon_id"),
    Index("ix_holon_refs_hobj", "hobj_id"),
)

# Heartbeat history
heartbeats = Table(
    "heartbeats",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("heartbeat_time", DateTime, nullable=False),
    Column("prompt", Text, nullable=True),
    Column("response", Text, nullable=True),
    Column("hobj_count", Integer, default=0),
    Column("duration_ms", Float, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Index("ix_heartbeats_time", "heartbeat_time"),
)

# Which hobjs participated in which heartbeat
heartbeat_hobjs = Table(
    "heartbeat_hobjs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("heartbeat_id", Integer, ForeignKey("heartbeats.id", ondelete="CASCADE"), nullable=False),
    Column("hobj_id", String(36), ForeignKey("hobjs.id", ondelete="CASCADE"), nullable=False),
    Column("hud_sent", Text, nullable=True),  # JSON snapshot
    Column("actions_result", Text, nullable=True),  # JSON
    Index("ix_heartbeat_hobjs_heartbeat", "heartbeat_id"),
    Index("ix_heartbeat_hobjs_hobj", "hobj_id"),
)

# Message history between hobjs
messages = Table(
    "messages",
    metadata,
    Column("id", String(36), primary_key=True),  # Message GUID
    Column("sender_id", String(36), nullable=False),
    Column("recipient_ids", Text, nullable=False),  # JSON array of recipient GUIDs
    Column("content", Text, nullable=False),
    Column("tokens_attached", Integer, default=0),
    Column("timestamp", DateTime, nullable=False),
    Index("ix_messages_sender", "sender_id"),
    Index("ix_messages_timestamp", "timestamp"),
)

# Telemetry snapshots
telemetry_snapshots = Table(
    "telemetry_snapshots",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("snapshot_time", DateTime, nullable=False),
    Column("data", Text, nullable=False),  # JSON
    Index("ix_telemetry_time", "snapshot_time"),
)
