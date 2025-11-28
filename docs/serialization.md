# Serialization Pipeline

HolonAI uses a two-stage serialization process optimized for AI consumption.

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
           ▼  serialize
  ┌──────────────────┐
  │       JSON       │     Intermediate format
  │  (intermediate)  │     • Debuggable
  │                  │     • Standard
  │                  │     • Interoperable
  └────────┬─────────┘
           │
           ▼  convert
  ┌──────────────────┐
  │       TOON       │     Token-optimized format
  │ (AI-optimized)   │     • 30-60% fewer tokens
  │                  │     • LLM-native structure
  └────────┬─────────┘
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
holon = Holon()
# ... add purpose, self, actions ...

# Serialize for AI (uses TOON if available, falls back to JSON)
prompt = serialize_for_ai(holon)

# Send to AI, get response...
ai_response = call_ai(prompt)

# Parse and dispatch
action_calls = parse_ai_response(ai_response)
results = holon.dispatch_many(action_calls)
```

## Installation

TOON support is optional:

```bash
# Basic installation (JSON only)
pip install holon-ai

# With TOON support
pip install holon-ai[toon]
```
