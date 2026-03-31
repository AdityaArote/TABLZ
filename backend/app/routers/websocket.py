"""
TABLZ — WebSocket router: handles connections, auth, message routing, and token refresh.
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket_manager import ws_manager
from app.core.security import decode_access_token
from app.deps import get_db

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{restaurant_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    restaurant_id: str,
):
    """
    WebSocket endpoint for real-time updates.

    Auth: JWT in first message or query param.
    Events received: order.created, order.status_changed, table.status_changed, etc.
    Events sent: reauth (token refresh).
    Protocol:
      1. Client connects to /ws/{restaurant_id}
      2. Client sends {"type": "auth", "token": "jwt_here"}
      3. Server validates and starts broadcasting events
      4. Server sends heartbeat every 30s
      5. Server sends token_expiring_soon at t-2min
      6. Client sends {"type": "reauth", "token": "new_jwt"}
    """
    # Accept connection
    await ws_manager.connect(websocket, restaurant_id)

    # Start heartbeat in background
    heartbeat_task = asyncio.create_task(
        ws_manager.handle_heartbeat(websocket, restaurant_id)
    )

    authenticated = False

    try:
        # Wait for auth message
        auth_timeout = 10  # seconds to authenticate
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=auth_timeout)
            message = json.loads(raw)

            if message.get("type") == "auth":
                token = message.get("token", "")
                payload = decode_access_token(token)
                if payload and payload.get("restaurant_id") == restaurant_id:
                    authenticated = True
                    await ws_manager.send_personal(
                        websocket, "auth_success", {"message": "Authenticated"}
                    )
                else:
                    await ws_manager.send_personal(
                        websocket, "auth_failed", {"message": "Invalid token"}
                    )
                    await websocket.close(code=4001)
                    return
            else:
                await ws_manager.send_personal(
                    websocket, "auth_required", {"message": "Send auth message first"}
                )
                await websocket.close(code=4001)
                return
        except asyncio.TimeoutError:
            await ws_manager.send_personal(
                websocket, "auth_timeout", {"message": "Auth timeout"}
            )
            await websocket.close(code=4001)
            return

        # Main message loop
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)

            msg_type = message.get("type", "")

            if msg_type == "reauth":
                # Token refresh: validate new token
                new_token = message.get("token", "")
                payload = decode_access_token(new_token)
                if payload and payload.get("restaurant_id") == restaurant_id:
                    await ws_manager.send_personal(
                        websocket, "reauth_success", {"message": "Re-authenticated"}
                    )
                else:
                    await ws_manager.send_personal(
                        websocket, "reauth_failed", {"message": "Invalid token"}
                    )

            elif msg_type == "pong":
                # Heartbeat response — client is alive
                pass

            else:
                # Unknown message type — ignore
                pass

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        heartbeat_task.cancel()
        await ws_manager.disconnect(websocket, restaurant_id)
