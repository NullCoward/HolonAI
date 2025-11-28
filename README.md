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
│                                                                 │
│  Token Management:                                              │
│  • token_limit, token_count, is_over_limit                      │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install holon-ai

# With TOON serialization (30-60% token savings)
pip install holon-ai[toon]

# With token counting
pip install holon-ai[tokens]

# With everything
pip install holon-ai[all]
```

Or install from source:

```bash
git clone https://github.com/NullCoward/HolonAIRedux.git
cd HolonAIRedux
pip install -e ".[all]"
```

## Quick Example

```python
from holon_ai import Holon, serialize_for_ai, parse_ai_response

# Define actions
def create_task(title: str, priority: str = "medium") -> dict:
    """Create a new task."""
    return {"title": title, "priority": priority}

# Build the Holon with token limit
holon = (
    Holon(name="TaskManager")
    .with_token_limit(4000, model="gpt-4o")
    .add_purpose("You are a task management assistant")
    .add_self({"user": "alice"}, key="context")
    .add_self(lambda: get_tasks(), key="tasks", bind=True)  # Dynamic binding
    .add_action(create_task, purpose="Create a new task")
)

# Check tokens before sending
print(f"Using {holon.token_count} tokens ({holon.token_usage['percentage']}% of limit)")

# Serialize for AI (TOON or JSON)
prompt = serialize_for_ai(holon)

# Parse AI response and dispatch actions
ai_response = '{"actions": [{"action": "create_task", "params": {"title": "Review PR"}}]}'
results = holon.dispatch_many(parse_ai_response(ai_response))
```

## Documentation

- [Architecture](docs/architecture.md) - Core concepts, token management, and design
- [Serialization](docs/serialization.md) - JSON, TOON, and token counting pipeline
- [Quickstart](docs/quickstart.md) - Getting started guide with full API reference

## Key Features

- **Dynamic Bindings** - Bind to live code objects that resolve at runtime
- **Nested Holons** - Compose hierarchical agent structures
- **Auto-derived Metadata** - Function signatures and docstrings extracted automatically
- **Token Management** - Track and limit token usage with tiktoken
- **TOON Serialization** - Token-optimized format for 30-60% cost savings
- **Smart Serialization** - Lists for unkeyed items, dicts for keyed items
- **Fluent API** - Chainable builder pattern
- **cattrs Integration** - Clean, extensible serialization architecture

## Token Management

```python
holon = (
    Holon(name="Agent")
    .with_token_limit(4000, model="gpt-4o")
    .add_purpose("...")
)

# Dynamic properties
holon.token_count       # Current tokens used
holon.tokens_remaining  # Tokens left before limit
holon.is_over_limit     # True if over limit
holon.token_usage       # Full breakdown dict
```

## Dependencies

- **Required**: [cattrs](https://catt.rs/) - Serialization
- **Optional**: [tiktoken](https://github.com/openai/tiktoken) - Token counting
- **Optional**: [toon](https://github.com/toon-format/toon-python) - Token-optimized format

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
