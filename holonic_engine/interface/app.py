"""
Flask application for Human-Holon Interface.

The interface is itself a HolonicObject (GUID 0) that provides web-based
interaction with the holonic system.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from flask import Flask, render_template, request, jsonify

from ..agent import HolonicObject


# Special GUID for the interface holon
INTERFACE_GUID = "00000000-0000-0000-0000-000000000000"


class InterfaceHolon(HolonicObject):
    """
    The Human-Holon Interface as a HolonicObject.

    This holon has GUID 0 and does not heartbeat. It serves as the
    bridge between human users and the holonic system.
    """

    def __init__(self, **kwargs):
        # Set the special GUID before parent init
        super().__init__(**kwargs)
        # Override the ID to be the interface GUID
        object.__setattr__(self, 'id', INTERFACE_GUID)

        # Set interface-specific purpose
        self._purpose_bindings.update({
            "role": "Human-Holon Interface",
            "description": "Bridge between human users and the holonic system",
        })

        # Track connected holons for viewing
        self._connected_holons: dict[str, HolonicObject] = {}

    def connect_holon(self, holon: HolonicObject) -> None:
        """Connect a holon to this interface for viewing/interaction."""
        self._connected_holons[holon.id] = holon

    def disconnect_holon(self, holon_id: str) -> bool:
        """Disconnect a holon from this interface."""
        if holon_id in self._connected_holons:
            del self._connected_holons[holon_id]
            return True
        return False

    def get_connected_holon(self, holon_id: str) -> HolonicObject | None:
        """Get a connected holon by ID."""
        return self._connected_holons.get(holon_id)

    def list_connected_holons(self) -> list[dict[str, Any]]:
        """List all connected holons with basic info."""
        return [
            {
                "id": h.id,
                "token_bank": h.token_bank,
                "children_count": len(h.holon_children),
            }
            for h in self._connected_holons.values()
        ]


def create_app(interface: InterfaceHolon | None = None) -> Flask:
    """
    Create the Flask application for the Human-Holon Interface.

    Args:
        interface: The InterfaceHolon instance. If None, creates a new one.

    Returns:
        Configured Flask application
    """
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # Create or use provided interface holon
    if interface is None:
        interface = InterfaceHolon()

    app.config['INTERFACE'] = interface

    # =========================================================================
    # Routes
    # =========================================================================

    @app.route('/')
    def index():
        """Main interface page."""
        return render_template('index.html', interface=interface)

    @app.route('/api/interface')
    def api_interface():
        """Get interface holon state."""
        return jsonify({
            "id": interface.id,
            "purpose": interface._resolve_purpose(),
            "self_state": interface._resolve_self(),
            "connected_holons": interface.list_connected_holons(),
        })

    @app.route('/api/holons')
    def api_list_holons():
        """List all connected holons."""
        return jsonify(interface.list_connected_holons())

    @app.route('/api/holon/<holon_id>')
    def api_get_holon(holon_id: str):
        """Get a holon's full state."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        return jsonify({
            "id": holon.id,
            "purpose": holon._resolve_purpose(),
            "self_state": holon._resolve_self(),
            "knowledge": holon.knowledge,
            "actions": [
                {"name": a.name, "purpose": a.purpose}
                for a in holon.actions
            ],
            "token_bank": holon.token_bank,
            "heart_rate_secs": holon.heart_rate_secs,
            "last_heartbeat": holon.last_heartbeat.isoformat() if holon.last_heartbeat else None,
            "next_heartbeat": holon.next_heartbeat.isoformat(),
            "children": [
                {
                    "id": c.id,
                    "token_bank": c.token_bank,
                }
                for c in holon.holon_children
            ],
            "parent_id": holon.holon_parent.id if holon.holon_parent else None,
        })

    @app.route('/api/holon/<holon_id>/hud')
    def api_get_holon_hud(holon_id: str):
        """Get a holon's HUD (serialized for AI)."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        return jsonify(holon.to_dict())

    @app.route('/api/holon/<holon_id>/purpose', methods=['GET', 'PUT'])
    def api_holon_purpose(holon_id: str):
        """Get or update a holon's purpose."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        if request.method == 'GET':
            return jsonify(holon._resolve_purpose())

        # PUT - update purpose
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        path = data.get('path', '')
        value = data.get('value')

        if path:
            holon.purpose_set(path, value)
        else:
            # Replace entire purpose
            holon._purpose_bindings.clear()
            if isinstance(value, dict):
                holon._purpose_bindings.update(value)

        return jsonify({"success": True, "purpose": holon._resolve_purpose()})

    @app.route('/api/holon/<holon_id>/self', methods=['GET', 'PUT'])
    def api_holon_self(holon_id: str):
        """Get or update a holon's self state."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        if request.method == 'GET':
            return jsonify(holon._resolve_self())

        # PUT - update self (only custom bindings, not defaults)
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        path = data.get('path', '')
        value = data.get('value')

        if path:
            holon.self_set(path, value)

        return jsonify({"success": True, "self_state": holon._resolve_self()})

    @app.route('/api/holon/<holon_id>/knowledge', methods=['GET', 'PUT', 'DELETE'])
    def api_holon_knowledge(holon_id: str):
        """Get, update, or delete knowledge."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        if request.method == 'GET':
            path = request.args.get('path', '')
            if path:
                try:
                    return jsonify({"value": holon.knowledge_get(path)})
                except KeyError:
                    return jsonify({"error": "Path not found"}), 404
            return jsonify(holon.knowledge)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        path = data.get('path', '')

        if request.method == 'DELETE':
            if not path:
                return jsonify({"error": "Path required for delete"}), 400
            try:
                holon.knowledge_delete(path)
                return jsonify({"success": True})
            except KeyError:
                return jsonify({"error": "Path not found"}), 404

        # PUT
        value = data.get('value')
        if path:
            holon.knowledge_set(path, value)
        else:
            holon.knowledge.clear()
            if isinstance(value, dict):
                holon.knowledge.update(value)

        return jsonify({"success": True, "knowledge": holon.knowledge})

    @app.route('/api/holon/<holon_id>/action/<action_name>', methods=['POST'])
    def api_execute_action(holon_id: str, action_name: str):
        """Execute an action on a holon."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        params = request.get_json() or {}

        try:
            result = holon.dispatch(action_name, **params)
            return jsonify({"success": True, "result": result})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/api/holon/<holon_id>/messages')
    def api_holon_messages(holon_id: str):
        """Get a holon's message history."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        messages = holon.get_messages()
        return jsonify([
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "recipient_ids": m.recipient_ids,
                "content": m.content,
                "tokens_attached": m.tokens_attached,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in messages
        ])

    @app.route('/api/holon/<holon_id>/message', methods=['POST'])
    def api_send_message(holon_id: str):
        """Send a message from a holon."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        recipient_ids = data.get('recipient_ids', [])
        content = data.get('content', '')
        tokens = data.get('tokens', 0)

        message = holon.send_message(recipient_ids, content, tokens)
        return jsonify({
            "success": True,
            "message": {
                "id": message.id,
                "sender_id": message.sender_id,
                "recipient_ids": message.recipient_ids,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
            }
        })

    @app.route('/api/holon/<holon_id>/children')
    def api_holon_children(holon_id: str):
        """Get a holon's children with full details."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        return jsonify([
            {
                "id": c.id,
                "purpose": c._resolve_purpose(),
                "knowledge": c.knowledge,
                "token_bank": c.token_bank,
            }
            for c in holon.holon_children
        ])

    @app.route('/api/holon/<holon_id>/child', methods=['POST'])
    def api_create_child(holon_id: str):
        """Create a new child holon."""
        holon = interface.get_connected_holon(holon_id)
        if holon is None:
            return jsonify({"error": "Holon not found"}), 404

        data = request.get_json() or {}
        template_id = data.get('template_id')

        try:
            child = holon.create_child(template_id=template_id)
            # Auto-connect the child to interface
            interface.connect_holon(child)
            return jsonify({
                "success": True,
                "child": {
                    "id": child.id,
                    "token_bank": child.token_bank,
                }
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    return app


def run_interface(
    interface: InterfaceHolon | None = None,
    host: str = "127.0.0.1",
    port: int = 5000,
    debug: bool = True,
) -> None:
    """
    Run the Human-Holon Interface web server.

    Args:
        interface: The InterfaceHolon instance. If None, creates a new one.
        host: Host to bind to
        port: Port to listen on
        debug: Enable Flask debug mode
    """
    app = create_app(interface)
    app.run(host=host, port=port, debug=debug)
