# Serialization Pipeline

HolonAI uses a multi-stage serialization process optimized for AI consumption.

## Pipeline Overview

```
  ┌──────────────────┐
  │      HOLON       │
  │  (live bindings) │     At runtime, resolve all
  │                  │     bindings to current values
  │  Purpose ──▶ refs│
  │  Self ────▶ refs │
  │  Actions ─▶ refs │
  └────────┬─────────┘
           │
           ▼  serialize (cattrs)
  ┌──────────────────┐
  │       JSON       │     Intermediate format
  │  (intermediate)  │     • Debuggable
  │                  │     • Standard
  │                  │     • Interoperable
  └────────┬─────────┘
           │
           ├──────────────────────┐
           │                      │
           ▼  count (tiktoken)    ▼  convert (toon)
  ┌──────────────────┐   ┌──────────────────┐
  │   Token Count    │   │       TOON       │     Token-optimized
  │   520 tokens     │   │ (AI-optimized)   │     • 30-60% fewer tokens
  │   13% of limit   │   │                  │     • LLM-native structure
  └──────────────────┘   └────────┬─────────┘
                                  │
                                  ▼  send
                         ┌──────────────────┐
                         │        AI        │
                         └────────┬─────────┘
                                  │
                                  ▼  response
                         ┌──────────────────┐
                         │       JSON       │     Action call format
                         │  (action calls)  │
                         └────────┬─────────┘
                                  │
                                  ▼  dispatch
                         ┌──────────────────┐
                         │  Execute Action  │
                         │    callbacks     │
                         └──────────────────┘
```

## Smart Serialization

HolonAI automatically chooses the best format for your data:

| Item Type | Serialized As |
|-----------|---------------|
| All unkeyed items | List (clean, no synthetic keys) |
| All keyed items | Dict (key-value pairs) |
| Mixed items | List with embedded dicts |

```python
# Unkeyed → list
holon.add_purpose("Be helpful")
holon.add_purpose("Be concise")
# Serializes to: "purpose": ["Be helpful", "Be concise"]

# Keyed → dict
holon.add_self(user, key="user")
holon.add_self(tasks, key="tasks")
# Serializes to: "self": {"user": {...}, "tasks": [...]}
```

## TOON Format

[TOON (Token-Oriented Object Notation)](https://github.com/toon-format/toon) is a compact, human-readable encoding that minimizes tokens for LLM input.

### Key Features

- YAML-like indentation (no braces)
- CSV-style rows for uniform arrays: `[N]{fields}: val,val,val`
- Quotes only when necessary
- 30-60% token reduction vs JSON

### Example Conversion

**JSON (257 tokens):**
```json
{
  "context": {"task": "Our favorite hikes"},
  "friends": ["ana", "luis", "sam"],
  "hikes": [
    {"id": 1, "name": "Blue Lake Trail", "distance": 7.5}
  ]
}
```

**TOON (166 tokens):**
```
context:
  task: Our favorite hikes
friends[3]: ana,luis,sam
hikes[1]{id,name,distance}:
  1,Blue Lake Trail,7.5
```

## Token Counting

Track token usage with tiktoken integration:

```python
from holon_ai import Holon, count_tokens

holon = (
    Holon(name="Agent")
    .with_token_limit(4000, model="gpt-4o")
    .add_purpose("...")
    .add_self(data, key="data")
)

# Via Holon properties
print(holon.token_count)       # 520
print(holon.tokens_remaining)  # 3480
print(holon.is_over_limit)     # False
print(holon.token_usage)       # Full breakdown

# Standalone counting
count = count_tokens("Hello world", model="gpt-4o")
```

### Model Encodings

| Model | Encoding |
|-------|----------|
| gpt-4o, gpt-4o-mini | o200k_base |
| gpt-4, gpt-4-turbo, gpt-3.5-turbo | cl100k_base |
| claude-3-* | cl100k_base (approximation) |

## AI Response Format

The AI responds with JSON containing action calls:

```json
{
  "actions": [
    {
      "action": "db.users.create",
      "params": { "name": "Alice" }
    },
    {
      "action": "notify.send",
      "params": { "msg": "User created" }
    },
    {
      "action": "log.info",
      "params": { "event": "user_flow_complete" }
    }
  ]
}
```

Multiple actions can be returned in a single response.

## Usage

```python
from holon_ai import Holon, serialize_for_ai, parse_ai_response

# Create and populate a Holon
holon = (
    Holon(name="Agent")
    .with_token_limit(4000, model="gpt-4o")
    .add_purpose("...")
    .add_self(data, key="data")
    .add_action(my_function)
)

# Check tokens before sending
if holon.is_over_limit:
    print(f"Warning: {holon.token_count} exceeds limit of {holon.token_limit}")

# Serialize for AI (uses TOON if available, falls back to JSON)
prompt = serialize_for_ai(holon)

# Send to AI, get response...
ai_response = call_ai(prompt)

# Parse and dispatch
action_calls = parse_ai_response(ai_response)
results = holon.dispatch_many(action_calls)
```

## Installation

Optional dependencies for extended functionality:

```bash
# Basic installation (JSON only)
pip install holon-ai

# With TOON support (30-60% token savings)
pip install holon-ai[toon]

# With token counting
pip install holon-ai[tokens]

# With everything
pip install holon-ai[all]
```

## Architecture Notes

Serialization is handled by [cattrs](https://catt.rs/) with custom hooks registered in `converter.py`. This keeps serialization logic separate from model classes — you can customize or extend serialization without modifying the Holon class itself.

```python
from holon_ai import holon_converter

# The global converter instance
data = holon_converter.unstructure_holon(my_holon)
```
