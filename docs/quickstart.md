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

### Creating and Executing a Holon

```python
from openai import OpenAI
from holonic_engine import Holon

# Define your actions
def create_task(title: str, priority: str = "medium") -> dict:
    """Create a new task with the given title and priority."""
    task = {"title": title, "priority": priority, "status": "pending"}
    db.insert("tasks", task)
    return task

def complete_task(task_id: int) -> bool:
    """Mark a task as completed."""
    return db.update("tasks", task_id, {"status": "completed"})

# Build the Holon with an AI client
holon = (
    Holon(name="TaskManager")
    .with_client(OpenAI(), model="gpt-4o")
    .add_purpose("You are a task management assistant")
    .add_purpose("Help users organize and prioritize their work")
    .add_self({"user": "alice", "role": "developer"}, key="context")
    .add_action(create_task, name="create_task", purpose="Create a new task")
    .add_action(complete_task, name="complete_task", purpose="Mark a task as done")
)

# Execute - serializes, calls AI, parses response, dispatches actions
result = holon.execute("Create a high priority task to review PR #42")

# Access the results
print(result.results)        # Results from executed actions
print(result.ai_response)    # Raw AI response
print(result.actions_called) # What actions the AI chose
```

### Using with Anthropic

```python
from anthropic import Anthropic
from holonic_engine import Holon

holon = (
    Holon(name="Assistant")
    .with_client(Anthropic(), model="claude-sonnet-4-20250514")
    .add_purpose("You are a helpful assistant")
    .add_action(my_action, name="do_thing")
)

result = holon.execute("Help me with something")
```

### Using Internal OpenAI (Recommended)

For the simplest setup with the best reliability, use `with_openai()` which creates
an internal OpenAI client and enables **structured outputs** by default:

```python
from holonic_engine import Holon

# Uses OPENAI_API_KEY environment variable
holon = (
    Holon(name="Assistant")
    .with_openai(model="gpt-4o")  # Structured outputs enabled by default!
    .add_purpose("You are a helpful assistant")
    .add_action(my_action, name="do_thing")
)

result = holon.execute("Do something")
```

**Why use structured outputs?**

OpenAI's structured outputs use `response_format` with a JSON schema to *guarantee*
valid action responses. This eliminates JSON parsing errors entirely — the AI is
constrained to always return properly formatted `{"actions": [...]}` responses.

```python
# With explicit API key:
holon.with_openai(api_key="sk-...", model="gpt-4o-mini")

# Disable structured outputs if needed (falls back to prompting):
holon.with_openai(model="gpt-4o", structured_output=False)
```

> **Note**: Structured outputs are only available with OpenAI models. The generic
> `with_client()` method does not enable them (to preserve compatibility with
> user-configured clients).

### Adding Dynamic Bindings

```python
# Bind to live data that resolves at execution time
def get_pending_tasks():
    return db.query("SELECT * FROM tasks WHERE status = 'pending'")

holon.add_self(get_pending_tasks, key="pending_tasks")
```

## ExecutionResult

The `execute()` method returns an `ExecutionResult` with:

```python
result = holon.execute("Do something")

result.prompt          # The serialized prompt sent to AI
result.ai_response     # Raw response from the AI
result.actions_called  # List of {"action": "name", "params": {...}}
result.results         # List of results from each action
result.success         # True if no exceptions in results
result.first_result    # Shortcut to results[0]

# Iterate over action/result pairs
for action, res in result:
    print(f"{action['action']}: {res}")
```

## Token Management

Track and limit token usage for your Holons:

```python
holon = (
    Holon(name="Agent")
    .with_client(OpenAI(), model="gpt-4o")
    .with_token_limit(4000)
    .add_purpose("You are a helpful assistant")
    .add_self(get_context, key="context")
    .add_action(do_something, name="do_something")
)

# Check token usage before execution
print(f"Tokens used: {holon.token_count}")
print(f"Tokens remaining: {holon.tokens_remaining}")
print(f"Over limit: {holon.is_over_limit}")

if not holon.is_over_limit:
    result = holon.execute("Do the thing")
```

### Supported Models

| Model | Encoding Used |
|-------|---------------|
| gpt-4o, gpt-4o-mini | o200k_base |
| gpt-4, gpt-4-turbo, gpt-3.5-turbo | cl100k_base |
| claude-* | cl100k_base (approximation) |

## Nested Holons

Holons can contain other Holons for hierarchical structures:

```python
# Child Holon for a specific subsystem
db_holon = (
    Holon(name="DatabaseContext")
    .add_purpose("Database operation context")
    .add_self({"connection": "active", "pool_size": 10}, key="status")
    .add_action(query_database, name="query_database")
)

# Parent Holon contains the child
main_holon = (
    Holon(name="AppContext")
    .with_client(OpenAI(), model="gpt-4o")
    .add_purpose("You are the main application assistant")
    .add_self(db_holon, key="database")  # Nested Holon
    .add_self(get_current_user, key="user")
)
```

## Complete Example

```python
from openai import OpenAI
from holonic_engine import Holon

# 1. Define your actions
def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email to the specified recipient."""
    print(f"Sending email to {to}: {subject}")
    return True

def schedule_meeting(title: str, attendees: list[str], time: str) -> dict:
    """Schedule a meeting with the given attendees."""
    return {"meeting_id": 123, "title": title, "attendees": attendees}

# 2. Build the Holon
holon = (
    Holon(name="ExecutiveAssistant")
    .with_client(OpenAI(), model="gpt-4o", max_tokens=1000)
    .with_token_limit(8000)
    .add_purpose("You are an executive assistant")
    .add_purpose("Help schedule meetings and manage communications")
    .add_self({"name": "Alice", "title": "CEO"}, key="executive")
    .add_self(lambda: fetch_calendar(), key="calendar")
    .add_action(send_email, name="send_email", purpose="Send an email")
    .add_action(schedule_meeting, name="schedule_meeting", purpose="Schedule a meeting")
)

# 3. Execute
result = holon.execute("Schedule a meeting with Bob tomorrow at 2pm")

print(f"Actions called: {len(result.actions_called)}")
for action, res in result:
    print(f"  {action['action']}: {res}")
```

## API Reference

### Holon

```python
Holon(name: str | None = None)
```

**Methods:**
- `.with_client(client, *, model, max_tokens=4096)` - Configure AI client (OpenAI or Anthropic)
- `.with_openai(*, model="gpt-4o", api_key=None, max_tokens=4096, structured_output=True)` - Configure internal OpenAI client with structured outputs
- `.with_token_limit(limit, model=None)` - Set token limit
- `.add_purpose(item, *, key=None)` - Add to purpose
- `.add_self(item, *, key=None)` - Add to self state
- `.add_action(action, *, name=None, purpose=None)` - Add an action
- `.execute(user_message=None)` - Execute the full AI pipeline
- `.dispatch(action_name, **kwargs)` - Execute single action manually
- `.dispatch_many(action_calls)` - Execute multiple actions manually

**Properties:**
- `.token_count` - Current token count (dynamic)
- `.tokens_remaining` - Tokens left before limit
- `.is_over_limit` - True if over limit
- `.token_usage` - Full usage breakdown dict

### ExecutionResult

```python
ExecutionResult(
    prompt: str,
    ai_response: str,
    actions_called: list[dict],
    results: list[Any]
)
```

**Properties:**
- `.success` - True if no exceptions in results
- `.first_result` - First result or None

**Methods:**
- `__iter__()` - Iterate over (action, result) pairs
- `__len__()` - Number of actions executed

## Manual Serialization (Advanced)

For advanced use cases, you can manually serialize and dispatch:

```python
from holonic_engine import serialize_for_ai, parse_ai_response

# Serialize to prompt
prompt = serialize_for_ai(holon, format="toon")

# Call your own AI client
ai_response = my_custom_ai_call(prompt)

# Parse and dispatch
actions = parse_ai_response(ai_response)
results = holon.dispatch_many(actions)
```
