# HolonAI Architecture

## Overview

HolonAI is a library for building AI agent systems using the **Holon** abstraction — a portable AI context capsule that bundles everything an AI needs to understand and act.

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
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Role | Contains |
|-----------|------|----------|
| **HolonPurpose** | The interpretive lens | Goals, constraints, persona — defines HOW to interpret |
| **HolonSelf** | The current state | Data, context, nested Holons — defines WHAT to interpret |
| **HolonActions** | Available responses | Callable bindings — defines WHAT can be done |

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

Both `HolonPurpose` and `HolonSelf` support **dynamic bindings** — references to code objects that resolve at runtime:

```python
holon = Holon()
holon.add_self(lambda: get_current_user(), key="user", bind=True)
holon.add_self(lambda: db.get_pending_tasks(), key="tasks", bind=True)
```

When the Holon is serialized, bindings resolve to their current values, enabling real-time state capture.

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

Names are auto-derived in `module.path.function` format, or can be overridden.
