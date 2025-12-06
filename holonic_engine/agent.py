"""
HolonicAgent - An agent that extends Holon with hierarchy and communication.

A HolonicAgent IS-A Holon with additional capabilities:
- Unique ID (GUID)
- Children (hierarchy of child agents)
- Knowledge (JSON structure for persistent state)
- MessageHistory (for inter-agent communication)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import attrs

from .holon import Holon
from .containers import HolonPurpose


@attrs.define
class Message:
    """A message sent between holons."""
    sender_id: str = attrs.field()
    id: str = attrs.field(factory=lambda: str(uuid.uuid4()))
    recipient_ids: list[str] = attrs.field(factory=list)
    content: Any = attrs.field(default=None)
    tokens_attached: int = attrs.field(default=0)
    timestamp: datetime = attrs.field(factory=lambda: datetime.now(timezone.utc))


@attrs.define
class MessageHistory:
    """History of messages for an agent."""
    _messages: list[Message] = attrs.field(factory=list)

    def add(self, message: Message) -> None:
        """Add a message to the history."""
        self._messages.append(message)

    def get_all(self) -> list[Message]:
        """Get all messages."""
        return list(self._messages)

    def get_received(self, agent_id: str) -> list[Message]:
        """Get messages received by a specific agent."""
        return [m for m in self._messages if agent_id in m.recipient_ids]

    def get_sent(self, agent_id: str) -> list[Message]:
        """Get messages sent by a specific agent."""
        return [m for m in self._messages if m.sender_id == agent_id]

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)

    def __iter__(self):
        return iter(self._messages)


import re

def _parse_path(path: str) -> list[str | int]:
    """Parse a path into keys. Supports dot notation and brackets: 'tasks[0].title' or 'users[alice]'."""
    if not path:
        return []

    keys = []
    # Match: word, or [number], or [string]
    pattern = r'([^\.\[\]]+)|\[(\d+)\]|\[([^\]]+)\]'
    for match in re.finditer(pattern, path):
        if match.group(1):  # Regular key
            keys.append(match.group(1))
        elif match.group(2):  # Numeric index [0]
            keys.append(int(match.group(2)))
        elif match.group(3):  # String key [key]
            keys.append(match.group(3))
    return keys


def _get_value_at_path(data: dict | list, path: str) -> Any:
    """Get a value using path like 'tasks[0].title' or 'users[alice].email'."""
    keys = _parse_path(path)
    if not keys:
        return data

    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            raise KeyError(f"Path '{path}' not found")
    return current


def _set_value_at_path(data: dict, path: str, value: Any) -> None:
    """Set a value using path like 'tasks[0].title' or 'config.max'."""
    keys = _parse_path(path)
    if not keys:
        raise ValueError("Path cannot be empty")

    current = data
    for key in keys[:-1]:
        if isinstance(current, dict):
            if key not in current:
                current[key] = {}
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int):
            current = current[key]
        else:
            raise KeyError(f"Cannot traverse path '{path}'")

    final_key = keys[-1]
    if isinstance(current, list) and isinstance(final_key, int):
        current[final_key] = value
    else:
        current[final_key] = value


def _delete_at_path(data: dict, path: str) -> None:
    """Delete a value using path like 'tasks[0]' or 'config.old'."""
    keys = _parse_path(path)
    if not keys:
        raise ValueError("Path cannot be empty")

    current = data
    for key in keys[:-1]:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            raise KeyError(f"Path '{path}' not found")

    final_key = keys[-1]
    if isinstance(current, list) and isinstance(final_key, int):
        if 0 <= final_key < len(current):
            current.pop(final_key)
        else:
            raise KeyError(f"Path '{path}' not found")
    elif isinstance(current, dict) and final_key in current:
        del current[final_key]
    else:
        raise KeyError(f"Path '{path}' not found")


@attrs.define
class HolonicObject(Holon):
    """
    A Holon extended with hierarchy and communication capabilities.

    Inherits from Holon:
        purpose: HolonPurpose - The interpretive lens
        self_state: HolonSelf - The current state/context
        actions: HolonActions - Available responses

    Additional attributes:
        id: Auto-generated immutable GUID
        holon_parent: Reference to parent object (None if root)
        holon_children: Dict of child objects keyed by name
        knowledge: JSON structure for persistent state
        message_history: History of sent/received messages
        last_heartbeat: Timestamp of last heartbeat (None if never)
        next_heartbeat: Timestamp when next heartbeat is due
    """
    id: str = attrs.field(factory=lambda: str(uuid.uuid4()))
    holon_parent: "HolonicObject | None" = attrs.field(default=None)
    holon_children: list["HolonicObject"] = attrs.field(factory=list)
    _purpose_bindings: dict[str, Any] = attrs.field(factory=dict)
    _self_bindings: dict[str, Any] = attrs.field(factory=dict)
    knowledge: dict[str, Any] = attrs.field(factory=dict)
    _token_bank: int = attrs.field(default=0, alias="token_bank")
    message_history: MessageHistory = attrs.field(factory=MessageHistory)
    last_heartbeat: datetime | None = attrs.field(default=None)
    next_heartbeat: datetime = attrs.field(factory=lambda: datetime.now(timezone.utc))
    _heart_rate_secs: int = attrs.field(default=1, alias="heart_rate_secs")

    # Storage binding for auto-persistence (optional)
    _storage: Any = attrs.field(default=None, repr=False)


    def __attrs_post_init__(self):
        """Bind state and actions to the Holon."""
        # Initialize default self bindings (dynamic references)
        self._self_bindings.update({
            "current_time": lambda: datetime.now(timezone.utc).isoformat(),
            "holon_id": lambda: self.id,
            "holon_tree": lambda: self._get_holon_relationships(),
            "knowledge": lambda: self.knowledge,
            "token_bank": lambda: self._token_bank,
            "last_heartbeat": lambda: self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "next_heartbeat": lambda: self.next_heartbeat.isoformat(),
            "heart_rate_secs": lambda: self._heart_rate_secs,
        })

        # Built-in actions for self-management
        self.add_action(self.knowledge_set, name="knowledge_set", purpose="Set a value in knowledge at a dot.path")
        self.add_action(self.knowledge_delete, name="knowledge_delete", purpose="Delete a value from knowledge at a dot.path")
        self.add_action(self.child_purpose_set, name="child_purpose_set", purpose="Set purpose on a child holon by GUID")
        self.add_action(self.child_purpose_clear, name="child_purpose_clear", purpose="Clear all purpose from a child holon")
        self.add_action(self.create_child, name="create_child", purpose="Create a new child holon, optionally copying from a template GUID")
        self.add_action(self.send_message, name="send_message", purpose="Send a message to one or more holons by GUID")
        self.add_action(self.delay_heartbeat, name="sleep", purpose="Delay next heartbeat by specified seconds from its current scheduled time")

    # =========================================================================
    # Properties with auto-persistence
    # =========================================================================

    @property
    def token_bank(self) -> int:
        """Get the token bank value."""
        return self._token_bank

    @token_bank.setter
    def token_bank(self, value: int) -> None:
        """Set token bank and auto-save if storage bound."""
        self._token_bank = value
        self._auto_save()

    @property
    def heart_rate_secs(self) -> int:
        """Get the heart rate in seconds."""
        return self._heart_rate_secs

    @heart_rate_secs.setter
    def heart_rate_secs(self, value: int) -> None:
        """Set heart rate and auto-save if storage bound."""
        self._heart_rate_secs = value
        self._auto_save()

    # =========================================================================
    # Storage binding for auto-persistence
    # =========================================================================

    def bind_storage(self, storage: Any, save_now: bool = True) -> "HolonicObject":
        """
        Bind a storage backend for auto-persistence.

        Once bound, changes to this object are automatically saved.

        Args:
            storage: A storage backend (e.g., SQLStorage)
            save_now: If True, immediately save the current state

        Returns:
            self for chaining
        """
        self._storage = storage
        if save_now:
            self._auto_save(force=True)
        return self

    def unbind_storage(self) -> "HolonicObject":
        """Unbind storage - disables auto-persistence."""
        self._storage = None
        return self

    def _auto_save(self, force: bool = False) -> None:
        """Save to storage if bound. Called automatically on changes."""
        if self._storage is not None:
            self._storage.save_full(self)

    def bind_storage_tree(self, storage: Any, save_now: bool = True) -> "HolonicObject":
        """
        Bind storage to this object and all descendants.

        Args:
            storage: A storage backend (e.g., SQLStorage)
            save_now: If True, immediately save all objects

        Returns:
            self for chaining
        """
        self.bind_storage(storage, save_now=save_now)
        for child in self.holon_children:
            child.bind_storage_tree(storage, save_now=save_now)
        return self

    def unbind_storage_tree(self) -> "HolonicObject":
        """Unbind storage from this object and all descendants."""
        self.unbind_storage()
        for child in self.holon_children:
            child.unbind_storage_tree()
        return self

    def _get_holon_relationships(self) -> dict[str, Any]:
        """Build holon tree relationships for serialization."""
        tree = {
            "holon_children": [
                {
                    "id": child.id,
                    "token_bank": child.token_bank,
                }
                for child in self.holon_children
            ],
        }

        if self.holon_parent is not None:
            tree["holon_parent"] = {"id": self.holon_parent.id, "token_bank": self.holon_parent.token_bank}

        return tree

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary. Resolves all dynamic bindings at serialization time."""
        from .converter import holon_converter
        from .tokens import count_tokens

        result = {}

        # Purpose - resolve dynamic bindings
        purpose_data = self._resolve_purpose()
        if purpose_data:
            result["purpose"] = purpose_data

        # Self state - resolve dynamic bindings
        self_data = self._resolve_self()
        if self_data:
            result["self"] = self_data

        # Actions - use converter for proper serialization
        if len(self.actions) > 0:
            result["actions"] = [
                holon_converter._unstructure_holon_action(action)
                for action in self.actions
            ]

        # Add token count of this HUD
        import json
        result["hud_tokens"] = count_tokens(json.dumps(result))

        return result

    # Child management

    def create_child(self, template_id: str | None = None) -> "HolonicObject":
        """Create a new child. Optionally copy from an existing holon by GUID."""
        if template_id is not None:
            # Find the template holon and copy its purpose/knowledge
            template = self._find_in_tree(template_id)
            if template is None:
                raise KeyError(f"Template holon '{template_id}' not found")

            import copy
            child = HolonicObject(
                holon_parent=self,
                _purpose_bindings=copy.deepcopy(template._purpose_bindings),
                _self_bindings=copy.deepcopy(template._self_bindings),
                knowledge=copy.deepcopy(template.knowledge),
                token_bank=template.token_bank
            )
        else:
            child = HolonicObject(holon_parent=self)

        self.holon_children.append(child)

        # Propagate storage binding to child
        if self._storage is not None:
            child.bind_storage(self._storage, save_now=True)

        self._auto_save()  # Save parent (child list changed)
        return child

    def get_child(self, child_id: str) -> "HolonicObject | None":
        """Get a child object by GUID."""
        for child in self.holon_children:
            if child.id == child_id:
                return child
        return None

    def remove_child(self, child_id: str) -> bool:
        """
        Remove a child object by GUID.

        Returns True if removed, False if not found.
        """
        for i, child in enumerate(self.holon_children):
            if child.id == child_id:
                self.holon_children.pop(i)
                self._auto_save()
                return True
        return False

    # Knowledge management (JSON path operations)

    def knowledge_get(self, path: str = "") -> Any:
        """
        Get a value from knowledge at the given path.

        Args:
            path: Dot-notation path (e.g., "user.settings.theme")
                  Empty string returns entire knowledge dict.
        """
        if not path:
            return self.knowledge
        return _get_value_at_path(self.knowledge, path)

    def knowledge_set(self, path: str, value: Any) -> None:
        """Set a value in knowledge. Path uses dot-notation (e.g., 'user.settings.theme')."""
        _set_value_at_path(self.knowledge, path, value)
        self._auto_save()

    def knowledge_delete(self, path: str) -> None:
        """Delete a value from knowledge. Path uses dot-notation."""
        _delete_at_path(self.knowledge, path)
        self._auto_save()

    def knowledge_move(self, from_path: str, to_path: str) -> None:
        """
        Move a value from one path to another.

        Args:
            from_path: Source dot-notation path
            to_path: Destination dot-notation path
        """
        value = _get_value_at_path(self.knowledge, from_path)
        _set_value_at_path(self.knowledge, to_path, value)
        _delete_at_path(self.knowledge, from_path)
        self._auto_save()

    def knowledge_exists(self, path: str) -> bool:
        """Check if a path exists in knowledge."""
        try:
            _get_value_at_path(self.knowledge, path)
            return True
        except KeyError:
            return False

    # Purpose management (JSON path operations with dynamic binding)

    def _resolve_purpose(self) -> dict[str, Any]:
        """Resolve all purpose bindings to their current values."""
        import types

        def resolve_value(v: Any) -> Any:
            if isinstance(v, (types.FunctionType, types.MethodType)):
                return v()
            elif isinstance(v, dict):
                return {k: resolve_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [resolve_value(item) for item in v]
            return v

        return resolve_value(self._purpose_bindings)

    def purpose_get(self, path: str = "") -> Any:
        """Get a value from purpose at the given path. Resolves bindings."""
        resolved = self._resolve_purpose()
        if not path:
            return resolved
        return _get_value_at_path(resolved, path)

    def purpose_set(self, path: str, value: Any) -> None:
        """Set a value in purpose. Value can be static or callable (dynamic binding)."""
        _set_value_at_path(self._purpose_bindings, path, value)
        self._auto_save()

    def purpose_delete(self, path: str) -> None:
        """Delete a value from purpose at the given path."""
        _delete_at_path(self._purpose_bindings, path)
        self._auto_save()

    def purpose_move(self, from_path: str, to_path: str) -> None:
        """Move a value from one path to another in purpose."""
        value = _get_value_at_path(self._purpose_bindings, from_path)
        _set_value_at_path(self._purpose_bindings, to_path, value)
        _delete_at_path(self._purpose_bindings, from_path)
        self._auto_save()

    def purpose_exists(self, path: str) -> bool:
        """Check if a path exists in purpose."""
        try:
            _get_value_at_path(self._purpose_bindings, path)
            return True
        except KeyError:
            return False

    # Self state management (JSON path operations with dynamic binding)

    def _resolve_self(self) -> dict[str, Any]:
        """Resolve all self bindings to their current values."""
        import types

        def resolve_value(v: Any) -> Any:
            if isinstance(v, (types.FunctionType, types.MethodType)):
                return v()
            elif isinstance(v, dict):
                return {k: resolve_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [resolve_value(item) for item in v]
            return v

        return resolve_value(self._self_bindings)

    def self_get(self, path: str = "") -> Any:
        """Get a value from self state at the given path. Resolves bindings."""
        resolved = self._resolve_self()
        if not path:
            return resolved
        return _get_value_at_path(resolved, path)

    def self_set(self, path: str, value: Any) -> None:
        """Set a value in self state. Value can be static or callable (dynamic binding)."""
        _set_value_at_path(self._self_bindings, path, value)
        self._auto_save()

    def self_delete(self, path: str) -> None:
        """Delete a value from self state at the given path."""
        _delete_at_path(self._self_bindings, path)
        self._auto_save()

    def self_move(self, from_path: str, to_path: str) -> None:
        """Move a value from one path to another in self state."""
        value = _get_value_at_path(self._self_bindings, from_path)
        _set_value_at_path(self._self_bindings, to_path, value)
        _delete_at_path(self._self_bindings, from_path)
        self._auto_save()

    def self_exists(self, path: str) -> bool:
        """Check if a path exists in self state."""
        try:
            _get_value_at_path(self._self_bindings, path)
            return True
        except KeyError:
            return False

    # Children purpose management

    def child_purpose_set(self, child_id: str, path: str, value: Any) -> None:
        """Set a purpose value on a child holon."""
        child = self.get_child(child_id)
        if child is None:
            raise KeyError(f"Child '{child_id}' not found")
        child.purpose_set(path, value)

    def child_purpose_clear(self, child_id: str) -> None:
        """Clear all purpose from a child holon."""
        child = self.get_child(child_id)
        if child is None:
            raise KeyError(f"Child '{child_id}' not found")
        child._purpose_bindings.clear()

    def child_purpose_get(self, child_id: str, path: str = "") -> Any:
        """
        Get purpose from a child.

        Args:
            child_id: GUID of the child object
            path: Dot-notation path (empty for entire purpose)

        Returns:
            The purpose value at the path
        """
        child = self.get_child(child_id)
        if child is None:
            raise KeyError(f"Child '{child_id}' not found")
        return child.purpose_get(path)

    # Children heartbeat management

    def child_set_next_heartbeat(self, child_id: str, next_time: datetime) -> None:
        """Set a child's next heartbeat time."""
        child = self.get_child(child_id)
        if child is None:
            raise KeyError(f"Child '{child_id}' not found")
        child.next_heartbeat = next_time
        child._auto_save()

    def child_delay_heartbeat(self, child_id: str, seconds: int) -> None:
        """Delay a child's next heartbeat by the specified seconds."""
        child = self.get_child(child_id)
        if child is None:
            raise KeyError(f"Child '{child_id}' not found")
        child.delay_heartbeat(seconds)

    def child_set_heart_rate(self, child_id: str, rate_secs: int) -> None:
        """Set a child's heart rate in seconds."""
        child = self.get_child(child_id)
        if child is None:
            raise KeyError(f"Child '{child_id}' not found")
        child.heart_rate_secs = rate_secs

    # Messaging

    def _get_root(self) -> "HolonicObject":
        """Get the root object of this tree."""
        obj = self
        while obj.holon_parent is not None:
            obj = obj.holon_parent
        return obj

    def _find_in_tree(self, obj_id: str) -> "HolonicObject | None":
        """Find an object by ID within this object's tree (up and down)."""
        root = self._get_root()
        return self._find_in_subtree(root, obj_id)

    def _find_in_subtree(self, obj: "HolonicObject", obj_id: str) -> "HolonicObject | None":
        """Recursively search for an object in a subtree."""
        if obj.id == obj_id:
            return obj
        for child in obj.holon_children:
            found = self._find_in_subtree(child, obj_id)
            if found is not None:
                return found
        return None

    def add_message(self, message: Message) -> None:
        """
        Add a message to this agent's message history.

        This is for programmatic use - it just adds to local history.

        Args:
            message: The message to add
        """
        self.message_history.add(message)
        # Persist message if storage is bound
        if self._storage is not None:
            self._storage.save_message(
                message.id,
                message.sender_id,
                message.recipient_ids,
                message.content,
                message.tokens_attached,
                message.timestamp,
            )

    def send_message(self, recipient_ids: str | list[str], content: Any, tokens: int = 0) -> Message:
        """Send a message to one or more holons by GUID. Optionally attach tokens."""
        if isinstance(recipient_ids, str):
            recipient_ids = [recipient_ids]

        message = Message(
            sender_id=self.id,
            recipient_ids=recipient_ids,
            content=content,
            tokens_attached=tokens
        )

        # Add to sender's history
        self.add_message(message)

        # Deliver to recipients in tree
        for rid in recipient_ids:
            recipient = self._find_in_tree(rid)
            if recipient is not None and recipient.id != self.id:
                recipient.add_message(message)

        return message

    def get_messages(self) -> list[Message]:
        """Get all messages in this agent's history."""
        return self.message_history.get_all()

    def get_received_messages(self) -> list[Message]:
        """Get messages received by this agent."""
        return self.message_history.get_received(self.id)

    def get_sent_messages(self) -> list[Message]:
        """Get messages sent by this agent."""
        return self.message_history.get_sent(self.id)

    # Heartbeat management

    def collect_due_heartbeats(self, heartbeats: list[tuple["HolonicObject", datetime]] | None = None) -> list[tuple["HolonicObject", datetime]]:
        """Collect (holon, next_heartbeat) pairs from this holon and all children recursively."""
        if heartbeats is None:
            heartbeats = []
        heartbeats.append((self, self.next_heartbeat))
        for child in self.holon_children:
            child.collect_due_heartbeats(heartbeats)
        return heartbeats

    def set_next_heartbeat(self, next_time: datetime) -> None:
        """Set when this holon should next wake up."""
        self.next_heartbeat = next_time

    def delay_heartbeat(self, seconds: int) -> None:
        """Push the next heartbeat back by the specified number of seconds."""
        from datetime import timedelta
        self.next_heartbeat = self.next_heartbeat + timedelta(seconds=seconds)
        self._auto_save()

    def action_results(self, results: dict[str, Any], heartbeat_time: datetime) -> list[Any]:
        """Process action results from AI response. Dispatches actions and updates heartbeat times."""
        from datetime import timedelta
        self.last_heartbeat = heartbeat_time
        self.next_heartbeat = heartbeat_time + timedelta(seconds=self._heart_rate_secs)
        action_calls = results.get("actions", [])
        results = self.dispatch_many(action_calls)
        self._auto_save()  # Save after heartbeat processing
        return results


