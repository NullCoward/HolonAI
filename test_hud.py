"""
Test script to see what a serialized Holon HUD looks like.
"""

import json
import sys
sys.path.insert(0, '.')

from holonic_engine import Holon, HolonicObject

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


# Build a HolonicObject (which IS-A Holon with hierarchy capabilities)
obj = (
    HolonicObject()
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

# Purpose: JSON structure with dot.path access
obj.purpose_set("role", "You are a task management assistant for a software development team")
obj.purpose_set("guidelines.help", "Help users organize, prioritize, and track their work")
obj.purpose_set("guidelines.style", "Be concise and action-oriented in your responses")
obj.purpose_set("guidelines.clarify", "When in doubt, ask clarifying questions before taking action")

# Serialize and display
print("=" * 70)
print("                         HOLON HUD")
print("=" * 70)
print()

hud = obj.to_dict()
print(json.dumps(hud, indent=2))

print()
print("=" * 70)
print("                     HOLONIC OBJECT DEMO")
print("=" * 70)
print()

print(f"Object ID: {obj.id}")

# Set some knowledge
obj.knowledge_set("config.max_tasks", 10)
obj.knowledge_set("config.notifications_enabled", True)
print(f"Knowledge: {json.dumps(obj.knowledge, indent=2)}")

# Create child objects
worker1 = obj.create_child()
worker2 = obj.create_child()

# Set purpose on children using dot.path
obj.child_purpose_set(worker1.id, "role", "Handle high-priority tasks")
obj.child_purpose_set(worker2.id, "role", "Handle documentation tasks")

print(f"\nChildren: {[c.id for c in obj.holon_children]}")
print(f"Worker1 purpose: {worker1.purpose_get()}")
print(f"Worker2 purpose: {worker2.purpose_get()}")

# Send a message
msg = obj.send_message([worker1.id, worker2.id], {"type": "task_update", "count": 3})
print(f"\nSent message: {msg.content}")
print(f"Worker1 received messages: {len(worker1.get_received_messages())}")
print(f"Worker2 received messages: {len(worker2.get_received_messages())}")

print()
print("=" * 70)
