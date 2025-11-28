# HolonAI

A Python library for building AI agent systems using the **Holon** abstraction.

## What is a Holon?

A Holon is a portable AI context capsule that bundles everything an AI needs to understand and act:

```
┌─────────────────────────────────────────────────────────────────┐
│                            HOLON                                │
├─────────────────────────────────────────────────────────────────┤
│  HolonPurpose ─────── The lens (HOW to interpret)               │
│  HolonSelf ────────── The state (WHAT to interpret)             │
│  HolonActions ─────── The responses (WHAT can be done)          │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install holon-ai

# With TOON serialization support (30-60% token savings)
pip install holon-ai[toon]
```

Or install from source:

```bash
pip install -e .
```

## Quick Example

```python
from holon_ai import Holon, serialize_for_ai, parse_ai_response

# Define actions
def create_task(title: str, priority: str = "medium") -> dict:
    """Create a new task."""
    return {"title": title, "priority": priority}

# Build the Holon
holon = (
    Holon(name="TaskManager")
    .add_purpose("You are a task management assistant")
    .add_self({"user": "alice"}, key="context")
    .add_self(lambda: get_tasks(), key="tasks", bind=True)  # Dynamic binding
    .add_action(create_task, purpose="Create a new task")
)

# Serialize for AI (TOON or JSON)
prompt = serialize_for_ai(holon)

# Parse AI response and dispatch actions
ai_response = '{"actions": [{"action": "create_task", "params": {"title": "Review PR"}}]}'
results = holon.dispatch_many(parse_ai_response(ai_response))
```

## Documentation

- [Architecture](docs/architecture.md) - Core concepts and design
- [Serialization](docs/serialization.md) - JSON and TOON pipeline
- [Quickstart](docs/quickstart.md) - Getting started guide

## Key Features

- **Dynamic Bindings** - Bind to live code objects that resolve at runtime
- **Nested Holons** - Compose hierarchical agent structures
- **Auto-derived Metadata** - Function signatures and docstrings extracted automatically
- **TOON Serialization** - Token-optimized format for 30-60% cost savings
- **Fluent API** - Chainable builder pattern

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
