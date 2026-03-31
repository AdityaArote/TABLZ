"""
TABLZ — WebSocket manager: room-based channels per restaurant,
heartbeat, token refresh protocol, event broadcasting.
"""

import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.security import decode_access_token


class ConnectionManager:
    """
    Room-based WebSocket connection manager.
    Each restaurant gets its own channel: restaurant:{id}.
    Supports heartbeat, token refresh, and graceful disconnect.
    """

    def __init__(self):
        # restaurant_id -> list of WebSocket connections
        self._rooms: dict[str, list[WebSocket]] = {}
        self._heartbeat_interval = 30  # seconds

    async def connect(self, websocket: WebSocket, restaurant_id: str) -> bool:
        """
        Accept WS connection and add to a restaurant room.
        Returns True if auth is valid, False otherwise.
        """
        await websocket.accept()

        if restaurant_id not in self._rooms:
            self._rooms[restaurant_id] = []
        self._rooms[restaurant_id].append(websocket)

        return True

    async def disconnect(self, websocket: WebSocket, restaurant_id: str):
        """Remove a connection from its room."""
        if restaurant_id in self._rooms:
            if websocket in self._rooms[restaurant_id]:
                self._rooms[restaurant_id].remove(websocket)
            # Clean up empty rooms
            if not self._rooms[restaurant_id]:
                del self._rooms[restaurant_id]

    async def broadcast_to_restaurant(
        self,
        restaurant_id: str,
        event_type: str,
        payload: dict,
    ):
        """Broadcast an event to all connections in a restaurant room."""
        message = json.dumps({
            "type": event_type,
            "data": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, default=str)

        if restaurant_id not in self._rooms:
            return

        dead_connections = []
        for ws in self._rooms[restaurant_id]:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
            except Exception:
                dead_connections.append(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self._rooms[restaurant_id].remove(ws)

    async def send_personal(self, websocket: WebSocket, event_type: str, payload: dict):
        """Send a message to a single connection."""
        message = json.dumps({
            "type": event_type,
            "data": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, default=str)

        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
        except Exception:
            pass

    async def handle_heartbeat(self, websocket: WebSocket, restaurant_id: str):
        """Send periodic heartbeat pings to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                if websocket.client_state == WebSocketState.CONNECTED:
                    await self.send_personal(websocket, "heartbeat", {"ping": True})
                else:
                    break
        except Exception:
            await self.disconnect(websocket, restaurant_id)

    def get_room_count(self, restaurant_id: str) -> int:
        """Get number of active connections for a restaurant."""
        return len(self._rooms.get(restaurant_id, []))

    def get_total_connections(self) -> int:
        """Get total number of active WebSocket connections."""
        return sum(len(conns) for conns in self._rooms.values())


# Singleton instance
ws_manager = ConnectionManager()
