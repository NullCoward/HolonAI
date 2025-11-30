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
pip install git+https://github.com/NullCoward/HolonAI.git
```

Or install from source:

```bash
git clone https://github.com/NullCoward/HolonAI.git
cd HolonAI
pip install -e .
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
    .add_self(lambda: get_tasks(), key="tasks")  # Callables auto-resolve
    .add_action(create_task, name="create_task", purpose="Create a new task")
)

# Check tokens before sending
print(f"Using {holon.token_count} tokens ({holon.token_usage['percentage']}% of limit)")

# Serialize for AI (TOON format)
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

- **Dynamic Bindings** - Callables automatically resolve at serialization time
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

- [cattrs](https://catt.rs/) - Serialization
- [tiktoken](https://github.com/openai/tiktoken) - Token counting
- [python-toon](https://github.com/xaviviro/python-toon) - Token-optimized format

## Development

```bash
git clone https://github.com/NullCoward/HolonAI.git
cd HolonAI
pip install -e ".[dev]"
pytest
```

### Test Suite

The library includes comprehensive tests:

```bash
# Run unit tests (134 tests)
pytest tests/ --ignore=tests/test_ai_integration.py

# Run with AI integration tests (requires API keys)
OPENAI_API_KEY=... ANTHROPIC_API_KEY=... pytest tests/
```

Tests cover:
- Core Holon functionality
- Action handling and dispatch
- Container serialization
- Token counting
- AI integration (OpenAI + Anthropic)

## License

MIT
