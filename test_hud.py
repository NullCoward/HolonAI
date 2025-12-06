"""
Test script to see what a serialized Holon HUD looks like.
"""

import json
import sys
sys.path.insert(0, '.')

from holonic_engine import Holon

# Simulate some data sources
def get_current_user():
    return {
        "id": 42,
        "name": "Alice",
        "role": "developer",
        "team": "backend"
    }

def get_pending_tasks():
    return [
        {"id": 1, "title": "Review PR #127", "priority": "high", "due": "today"},
        {"id": 2, "title": "Write unit tests", "priority": "medium", "due": "tomorrow"},
        {"id": 3, "title": "Update docs", "priority": "low", "due": "friday"},
    ]

# Define actions
def create_task(title: str, priority: str = "medium", assignee: str | None = None) -> dict:
    """Create a new task in the task management system."""
    return {"id": 99, "title": title, "priority": priority, "assignee": assignee}

def complete_task(task_id: int) -> bool:
    """Mark a task as completed."""
    return True

def reassign_task(task_id: int, new_assignee: str) -> bool:
    """Reassign a task to a different team member."""
    return True

def send_notification(user_id: int, message: str, urgent: bool = False) -> bool:
    """Send a notification to a user."""
    return True


# Build the Holon with token limit
holon = (
    Holon(name="TaskAssistant")

    # Set token limit for GPT-4o
    .with_token_limit(4000, model="gpt-4o")

    # Purpose: unkeyed list of instructions
    .add_purpose("You are a task management assistant for a software development team")
    .add_purpose("Help users organize, prioritize, and track their work")
    .add_purpose("Be concise and action-oriented in your responses")
    .add_purpose("When in doubt, ask clarifying questions before taking action")

    # Self: keyed dictionary of state
    .add_self(get_current_user, key="user")
    .add_self(get_pending_tasks, key="tasks")
    .add_self({"timezone": "America/New_York", "theme": "dark"}, key="preferences")
    .add_self({"sprint": "2024-Q1-W3", "team_velocity": 42}, key="context")

    # Actions: available operations
    .add_action(create_task, purpose="Create a new task for any team member")
    .add_action(complete_task, purpose="Mark an existing task as done")
    .add_action(reassign_task, purpose="Move a task to a different team member")
    .add_action(send_notification, purpose="Send a notification to alert someone")
)

# Serialize and display
print("=" * 70)
print("                         HOLON HUD")
print("=" * 70)
print()

hud = holon.to_dict()
print(json.dumps(hud, indent=2))

print()
print("=" * 70)
print("                      TOKEN USAGE")
print("=" * 70)
print()

usage = holon.token_usage
print(f"  Model:          {usage['model']}")
print(f"  Token Count:    {usage['count']}")
print(f"  Token Limit:    {usage['limit']}")
print(f"  Remaining:      {usage['remaining']}")
print(f"  Usage:          {usage['percentage']}%")
print(f"  Over Limit:     {usage['over_limit']}")

print()
print("=" * 70)
print(f"Holon: {holon.name}")
print("=" * 70)
