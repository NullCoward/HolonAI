# Quickstart

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

## Basic Usage

### Creating a Holon

```python
from holon_ai import Holon

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

holon.add_self(get_pending_tasks, key="pending_tasks")
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

# Add actions with explicit names (signature and docstring auto-extracted)
holon.add_action(create_task, name="create_task", purpose="Create a new task for the user")
holon.add_action(complete_task, name="complete_task", purpose="Mark an existing task as done")
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

## Token Management

Track and limit token usage for your Holons:

```python
# Set a token limit with model for correct encoding
holon = (
    Holon(name="Agent")
    .with_token_limit(4000, model="gpt-4o")
    .add_purpose("You are a helpful assistant")
    .add_self(get_context, key="context")
    .add_action(do_something, name="do_something")
)

# Check token usage
print(f"Tokens used: {holon.token_count}")
print(f"Tokens remaining: {holon.tokens_remaining}")
print(f"Over limit: {holon.is_over_limit}")

# Get full breakdown
usage = holon.token_usage
# {
#   "count": 520,
#   "limit": 4000,
#   "remaining": 3480,
#   "percentage": 13.0,
#   "over_limit": False,
#   "model": "gpt-4o"
# }

# Use in conditionals
if holon.is_over_limit:
    print("Warning: Context too large, consider trimming")
```

### Supported Models

| Model | Encoding Used |
|-------|---------------|
| gpt-4o, gpt-4o-mini | o200k_base |
| gpt-4, gpt-4-turbo, gpt-3.5-turbo | cl100k_base |
| claude-3-* | cl100k_base (approximation) |

## Nested Holons

Holons can contain other Holons for hierarchical structures:

```python
# Child Holon for a specific subsystem
db_holon = (
    Holon(name="DatabaseContext")
    .add_purpose("Database operation context")
    .add_self({"connection": "active", "pool_size": 10}, key="status")
    .add_action(query_database, name="query_database")
    .add_action(update_record, name="update_record")
)

# Parent Holon contains the child
main_holon = (
    Holon(name="AppContext")
    .add_purpose("You are the main application assistant")
    .add_self(db_holon, key="database")  # Nested Holon
    .add_self(get_current_user, key="user")
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

# 2. Build the Holon with token limit
holon = (
    Holon(name="ExecutiveAssistant")
    .with_token_limit(8000, model="gpt-4o")
    .add_purpose("You are an executive assistant")
    .add_purpose("Help schedule meetings and manage communications")
    .add_self({"name": "Alice", "title": "CEO"}, key="executive")
    .add_self(lambda: fetch_calendar(), key="calendar")
    .add_action(send_email, name="send_email", purpose="Send an email on behalf of the executive")
    .add_action(schedule_meeting, name="schedule_meeting", purpose="Schedule a new meeting")
)

# 3. Check tokens before sending
print(f"Using {holon.token_count} tokens ({holon.token_usage['percentage']}% of limit)")

# 4. Serialize and send to AI
prompt = serialize_for_ai(holon)
ai_response = your_ai_client.complete(prompt + "\n\nUser: Schedule a meeting with Bob tomorrow at 2pm")

# 5. Execute the AI's chosen actions
actions = parse_ai_response(ai_response)
results = holon.dispatch_many(actions)
```

## API Reference

### Holon

```python
Holon(
    name: str | None = None,
    token_limit: int | None = None,
    model: str | None = None
)
```

**Methods:**
- `.add_purpose(item, *, key=None)` - Add to purpose
- `.add_self(item, *, key=None)` - Add to self state
- `.add_action(action, *, name=None, purpose=None)` - Add an action (use `name=` for predictable action names)
- `.with_token_limit(limit, model=None)` - Set token limit (fluent)
- `.to_dict(*, nested=False)` - Serialize to dict
- `.to_json(**kwargs)` - Serialize to JSON string
- `.dispatch(action_name, **kwargs)` - Execute single action
- `.dispatch_many(action_calls)` - Execute multiple actions

**Note:** When adding actions, always provide an explicit `name=` parameter. Without it, the action name defaults to the full module path (e.g., `myapp.tasks.create_task`), which may not match what the AI returns.

**Properties:**
- `.token_count` - Current token count (dynamic)
- `.tokens_remaining` - Tokens left before limit
- `.is_over_limit` - True if over limit
- `.token_usage` - Full usage breakdown dict
