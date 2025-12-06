# HolonicEngine

A Python library for building AI agent systems using the **Holon** abstraction.

## Core Concepts

### Holon - The Context Capsule

A Holon is a pure architectural object that bundles everything an AI needs to understand and act:

```
┌─────────────────────────────────────────────────────────────────┐
│                            HOLON                                │
├─────────────────────────────────────────────────────────────────┤
│  HolonPurpose ─────── The lens (HOW to interpret)               │
│  HolonSelf ────────── The state (WHAT to interpret)             │
│  HolonActions ─────── The responses (WHAT can be done)          │
└─────────────────────────────────────────────────────────────────┘
```

### HolonicObject - Extended Holon

A HolonicObject extends Holon with hierarchy, state management, and messaging:

```
┌─────────────────────────────────────────────────────────────────┐
│                   HOLONIC OBJECT (extends Holon)                │
├─────────────────────────────────────────────────────────────────┤
│  Inherited from Holon:                                          │
│    purpose, self_state, actions                                 │
│                                                                 │
│  Additional:                                                    │
│    id ───────────────── Unique GUID (auto-generated)            │
│    holon_parent ─────── Reference to parent object              │
│    holon_children ───── Dict of child objects (by name)         │
│    knowledge ────────── JSON structure for persistent state     │
│    message_history ──── Inter-object communication              │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install git+https://github.com/NullCoward/HolonicEngine.git
```

Or install from source:

```bash
git clone https://github.com/NullCoward/HolonicEngine.git
cd HolonicEngine
pip install -e .
```

## Quick Example

```python
from holonic_engine import HolonicObject

# Define actions
def create_task(title: str, priority: str = "medium") -> dict:
    """Create a new task."""
    return {"title": title, "priority": priority}

# Build a HolonicObject (which IS-A Holon)
obj = (
    HolonicObject()
    .add_purpose("You are a task management assistant")
    .add_self({"user": "alice"}, key="context")
    .add_self(lambda: get_tasks(), key="tasks")  # Callables auto-resolve
    .add_action(create_task, name="create_task", purpose="Create a new task")
)

# Object capabilities
print(obj.id)  # Auto-generated GUID

# Create child objects
worker = obj.create_child("worker")
obj.child_purpose_add("worker", "Handle task execution")

# Manage knowledge
obj.knowledge_set("config.max_tasks", 10)
print(obj.knowledge_get("config.max_tasks"))  # 10

# Send messages between objects
obj.send_message(worker.id, {"type": "task", "action": "process"})
```

## Documentation

- [Architecture](docs/architecture.md) - Core concepts and design
- [Serialization](docs/serialization.md) - JSON, TOON, and token counting
- [Quickstart](docs/quickstart.md) - Getting started guide

## Key Features

- **Inheritance Model** - HolonicObject extends Holon (IS-A relationship)
- **Object Hierarchy** - Create parent-child object relationships
- **Knowledge Management** - JSON path operations (get, set, delete, move)
- **Inter-Object Messaging** - Send messages to one or many objects by GUID
- **Dynamic Bindings** - Callables automatically resolve at serialization time
- **Nested Holons** - Compose hierarchical structures
- **TOON Serialization** - Token-optimized format for 30-60% cost savings
- **Fluent API** - Chainable builder pattern

## API Overview

### Holon (Base Class)

```python
holon = (
    Holon()
    .add_purpose("System prompt")          # Add purpose items
    .add_self(data, key="context")         # Add self state
    .add_action(callback, name="action")   # Add actions
)

holon.to_dict()           # Serialize to dict
holon.to_json()           # Serialize to JSON string
holon.dispatch("action")  # Execute an action
```

### HolonicObject (Extends Holon)

```python
obj = HolonicObject()  # Has all Holon methods plus:

# Properties
obj.id                  # Auto-generated GUID
obj.holon_parent        # Reference to parent (None if root)
obj.holon_children      # Dict of child objects
obj.knowledge           # JSON state structure
obj.message_history     # MessageHistory object

# Child management
child = obj.create_child("name")
obj.get_child("name")
obj.remove_child("name")

# Knowledge (JSON path operations)
obj.knowledge_set("path.to.value", data)
obj.knowledge_get("path.to.value")
obj.knowledge_delete("path.to.value")
obj.knowledge_move("old.path", "new.path")

# Child purpose management
obj.child_purpose_add("child_name", "Purpose text")
obj.child_purpose_clear("child_name")

# Messaging
obj.send_message(recipient_id, content)
obj.send_message([id1, id2], content)  # Broadcast
obj.get_received_messages()
obj.get_sent_messages()
```

## Dependencies

- [cattrs](https://catt.rs/) - Serialization
- [tiktoken](https://github.com/openai/tiktoken) - Token counting
- [python-toon](https://github.com/xaviviro/python-toon) - Token-optimized format

## Development

```bash
git clone https://github.com/NullCoward/HolonicEngine.git
cd HolonicEngine
pip install -e ".[dev]"
pytest
```

### Test Suite

```bash
# Run unit tests (158 tests)
pytest tests/ --ignore=tests/test_ai_integration.py

# Run with AI integration tests (requires API keys)
OPENAI_API_KEY=... ANTHROPIC_API_KEY=... pytest tests/
```

## License

MIT
