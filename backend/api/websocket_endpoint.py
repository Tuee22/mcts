"""
Unified WebSocket endpoint for the Corridors game API.
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from .websocket_unified import unified_ws_manager, WSMessage, WSResponse

logger = logging.getLogger(__name__)


async def websocket_endpoint(
    websocket: WebSocket, user_id: Optional[str] = None
) -> None:
    """
    Unified WebSocket endpoint that handles all game-related communication.

    Query parameters:
    - user_id: Optional user identifier for the connection
    """
    connection_id = None

    try:
        # Connect to the unified manager
        connection_id = await unified_ws_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connection established: {connection_id}")

        # Message handling loop
        while True:
            try:
                # Receive message from client
                message_text = await websocket.receive_text()
                message_data = json.loads(message_text)

                logger.debug(
                    f"Received message from {connection_id}: {message_data.get('type', 'unknown')}"
                )

                # Handle the message
                response = await unified_ws_manager.handle_message(
                    connection_id, message_data
                )

                # Send response if this was a request-response message
                if response:
                    response_json = json.dumps(response.model_dump(), default=str)
                    await websocket.send_text(response_json)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {connection_id}: {e}")
                error_response = WSResponse(
                    id="unknown",
                    type="error",
                    success=False,
                    error="Invalid JSON format",
                )
                await websocket.send_text(
                    json.dumps(error_response.model_dump(), default=str)
                )

            except Exception as e:
                logger.error(f"Error handling message from {connection_id}: {e}")
                error_response = WSResponse(
                    id="unknown", type="error", success=False, error=str(e)
                )
                await websocket.send_text(
                    json.dumps(error_response.model_dump(), default=str)
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")

    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")

    finally:
        # Clean up connection
        if connection_id:
            await unified_ws_manager.disconnect(connection_id)
