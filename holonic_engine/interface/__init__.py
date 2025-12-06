"""
Human-Holon Interface - A Flask-based web interface for interacting with HolonicObjects.

The interface itself is a HolonicObject with GUID "00000000-0000-0000-0000-000000000000"
that does not heartbeat but provides human interaction capabilities.
"""

from .app import create_app, InterfaceHolon

__all__ = ["create_app", "InterfaceHolon"]
