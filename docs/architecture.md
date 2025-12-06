# HolonicEngine Architecture

## Overview

HolonicEngine is a library for building AI agent systems using the **Holon** abstraction — a portable AI context capsule that bundles everything an AI needs to understand and act.

Built with [attrs](https://www.attrs.org/) for clean class definitions and [cattrs](https://catt.rs/) for flexible serialization.

## Core Concept

A **Holon** combines three components:

```
┌─────────────────────────────────────────────────────────────────┐
│                            HOLON                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │    HolonPurpose     │         │     HolonSelf       │        │
│  │   "The Lens"        │────────▶│   "The State"       │        │
│  ├─────────────────────┤ frames  ├─────────────────────┤        │
│  │                     │         │                     │        │
│  │ HOW to interpret    │         │ WHAT to interpret   │        │
│  │                     │         │                     │        │
│  │ • goals             │         │ • current data      │        │
│  │ • constraints       │         │ • context refs      │        │
│  │ • persona/role      │         │ • world state       │        │
│  └─────────────────────┘         └─────────────────────┘        │
│            │                              │                     │
│            │         AI REASONING         │                     │
│            └──────────────┬───────────────┘                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────┐            │
│  │              HolonActions                       │            │
│  │             "The Responses"                     │            │
│  ├─────────────────────────────────────────────────┤            │
│  │ WHAT can be done                                │            │
│  │                                                 │            │
│  │ ┌──────────────┐ ┌──────────────┐               │            │
│  │ │ HolonAction  │ │ HolonAction  │ ...           │            │
│  │ │  callback    │ │  callback    │               │            │
│  │ └──────────────┘ └──────────────┘               │            │
│  └─────────────────────────────────────────────────┘            │
│                                                                 │
│  Token Management:                                              │
│  • token_limit: int | None                                      │
│  • token_count: int (dynamic)                                   │
│  • model: str | None (for encoding selection)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Role | Contains |
|-----------|------|----------|
| **HolonPurpose** | The interpretive lens | Goals, constraints, persona — defines HOW to interpret |
| **HolonSelf** | The current state | Data, context, nested Holons — defines WHAT to interpret |
| **HolonActions** | Available responses | Callable bindings — defines WHAT can be done |

## Token Management

Each Holon can track and limit its token usage:

```python
holon = (
    Holon(name="Agent")
    .with_token_limit(4000, model="gpt-4o")
    .add_purpose("...")
    .add_self(data, key="data")
)

# Dynamic properties
holon.token_count      # Current tokens (recalculated on access)
holon.tokens_remaining # Tokens left before limit
holon.is_over_limit    # True if over limit
holon.token_usage      # Full breakdown dict
```

Token counting uses [tiktoken](https://github.com/openai/tiktoken) with model-aware encodings:

| Model | Encoding |
|-------|----------|
| gpt-4o, gpt-4o-mini | o200k_base |
| gpt-4, gpt-4-turbo, gpt-3.5-turbo | cl100k_base |

## Holon Composition

Holons can be nested — a Holon's `Self` can contain other Holons, creating hierarchical structures:

```
┌─────────────────────────────────────────────────────────────────┐
│  TOP-LEVEL HOLON                                                │
├─────────────────────────────────────────────────────────────────┤
│  Purpose: "You are the orchestrator..."                         │
│                                                                 │
│  Self: [                                                        │
│    some_data,                                                   │
│    ┌─────────────────────────────────────┐                      │
│    │  NESTED HOLON (child)               │                      │
│    │  ├─ Purpose: [...]                  │                      │
│    │  ├─ Self: [...]                     │                      │
│    │  └─ Actions: [...]                  │                      │
│    └─────────────────────────────────────┘                      │
│    another_object,                                              │
│    [list_of_holons...]                                          │
│  ]                                                              │
│                                                                 │
│  Actions: [...]                                                 │
└─────────────────────────────────────────────────────────────────┘
```

When serialized, nested Holons are inlined without redundant framing.

## Dynamic Bindings

Both `HolonPurpose` and `HolonSelf` support **dynamic bindings** — callables are automatically invoked at serialization time:

```python
holon = Holon()
holon.add_self(get_current_user, key="user")      # callable → invoked at serialize
holon.add_self(db.get_pending_tasks, key="tasks") # callable → invoked at serialize
holon.add_self({"static": "data"}, key="config")  # dict → stored as-is
```

When the Holon is serialized, callables resolve to their current values, enabling real-time state capture. Non-callable values are stored directly.

## Smart Serialization

Serialization automatically chooses the best format:

| Item Type | Serialized As |
|-----------|---------------|
| All unkeyed items | List |
| All keyed items | Dict |
| Mixed items | List with embedded dicts |

```python
# Unkeyed → list
holon.add_purpose("Be helpful")
holon.add_purpose("Be concise")
# → "purpose": ["Be helpful", "Be concise"]

# Keyed → dict
holon.add_self(user, key="user")
holon.add_self(tasks, key="tasks")
# → "self": {"user": {...}, "tasks": [...]}
```

## HolonAction Structure

Each action exposes metadata for AI consumption:

```
┌─────────────────────────────────────────────────────────────────┐
│                         HolonAction                             │
├─────────────────────────────────────────────────────────────────┤
│  name: str            ← auto-derived from func path or override │
│  purpose: str | None  ← optional description for AI             │
│  callback: Callable   ← the function reference                  │
│  signature: auto      ← derived from callback                   │
│    • parameters       (name, type, default)                     │
│    • return type                                                │
│    • docstring                                                  │
└─────────────────────────────────────────────────────────────────┘
```

Names are auto-derived in `module.path.function` format, but should be overridden with explicit `name=` for predictable action dispatching:

```python
# Recommended: explicit name for predictable dispatching
holon.add_action(create_task, name="create_task", purpose="Create a task")

# Without name=, becomes: myapp.tasks.create_task (full module path)
```

## Library Architecture

```
holonic_engine/
├── holon.py        # Holon class with token management
├── client.py       # AI client integration (OpenAI, Anthropic, structured outputs)
├── containers.py   # HolonPurpose, HolonSelf, HolonActions, HolonBinding
├── action.py       # HolonAction, ActionSignature, ActionParameter
├── converter.py    # cattrs-based serialization
├── serialization.py# JSON/TOON output utilities
└── tokens.py       # tiktoken integration
```

Serialization rules are centralized in `converter.py`, separate from the model classes — following the cattrs philosophy of keeping un/structuring logic decoupled.

## AI Client Integration

HolonicEngine supports two modes of AI client configuration:

### Generic Client (`with_client`)
Accepts any OpenAI or Anthropic client instance. Maximum flexibility for custom configurations.

### Internal OpenAI (`with_openai`)
Creates an internal OpenAI client with **structured outputs** enabled by default. Uses OpenAI's `response_format` with JSON schema to guarantee valid action responses:

```python
# Guarantees responses match this schema:
{
    "actions": [
        {"action": "action_name", "params": {...}}
    ]
}
```

This eliminates JSON parsing errors — the AI is constrained at the token generation level to produce valid output.
