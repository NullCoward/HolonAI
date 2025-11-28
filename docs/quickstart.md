# Quickstart

## Installation

```bash
pip install holon-ai

# With TOON serialization support (recommended)
pip install holon-ai[toon]
```

## Basic Usage

### Creating a Holon

```python
from holon_ai import Holon, HolonAction

# Create a Holon with fluent API
holon = (
    Holon(name="TaskManager")
    .add_purpose("You are a task management assistant")
    .add_purpose("Help users organize and prioritize their work")
    .add_self({"user": "alice", "role": "developer"}, key="context")
)
```

### Adding Dynamic Bindings

```python
# Bind to live data that resolves at serialization time
def get_pending_tasks():
    return db.query("SELECT * FROM tasks WHERE status = 'pending'")

holon.add_self(get_pending_tasks, key="pending_tasks", bind=True)
```

### Defining Actions

```python
def create_task(title: str, priority: str = "medium") -> dict:
    """Create a new task with the given title and priority."""
    task = {"title": title, "priority": priority, "status": "pending"}
    db.insert("tasks", task)
    return task

def complete_task(task_id: int) -> bool:
    """Mark a task as completed."""
    return db.update("tasks", task_id, {"status": "completed"})

# Add actions (signature and docstring auto-extracted)
holon.add_action(create_task, purpose="Create a new task for the user")
holon.add_action(complete_task, purpose="Mark an existing task as done")
```

### Serialization

```python
from holon_ai import serialize_for_ai

# Serialize to TOON (token-optimized) or JSON
prompt = serialize_for_ai(holon, format="toon")
print(prompt)
```

### Handling AI Responses

```python
from holon_ai import parse_ai_response

# AI returns action calls
ai_response = '''
{
  "actions": [
    {"action": "create_task", "params": {"title": "Review PR #42", "priority": "high"}},
    {"action": "complete_task", "params": {"task_id": 7}}
  ]
}
'''

# Parse and execute
action_calls = parse_ai_response(ai_response)
results = holon.dispatch_many(action_calls)
```

## Nested Holons

Holons can contain other Holons for hierarchical structures:

```python
# Child Holon for a specific subsystem
db_holon = (
    Holon(name="DatabaseContext")
    .add_purpose("Database operation context")
    .add_self({"connection": "active", "pool_size": 10}, key="status")
    .add_action(query_database)
    .add_action(update_record)
)

# Parent Holon contains the child
main_holon = (
    Holon(name="AppContext")
    .add_purpose("You are the main application assistant")
    .add_self(db_holon, key="database")  # Nested Holon
    .add_self(get_current_user, key="user", bind=True)
)
```

When serialized, the nested Holon is inlined within the parent's structure.

## Complete Example

```python
from holon_ai import Holon, serialize_for_ai, parse_ai_response

# 1. Define your actions
def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email to the specified recipient."""
    # ... implementation ...
    return True

def schedule_meeting(title: str, attendees: list[str], time: str) -> dict:
    """Schedule a meeting with the given attendees."""
    # ... implementation ...
    return {"meeting_id": 123, "title": title}

# 2. Build the Holon
holon = (
    Holon(name="ExecutiveAssistant")
    .add_purpose("You are an executive assistant")
    .add_purpose("Help schedule meetings and manage communications")
    .add_self({"name": "Alice", "title": "CEO"}, key="executive")
    .add_self(lambda: fetch_calendar(), key="calendar", bind=True)
    .add_action(send_email, purpose="Send an email on behalf of the executive")
    .add_action(schedule_meeting, purpose="Schedule a new meeting")
)

# 3. Serialize and send to AI
prompt = serialize_for_ai(holon)
ai_response = your_ai_client.complete(prompt + "\n\nUser: Schedule a meeting with Bob tomorrow at 2pm")

# 4. Execute the AI's chosen actions
actions = parse_ai_response(ai_response)
results = holon.dispatch_many(actions)
```
