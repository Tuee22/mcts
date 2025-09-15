#!/usr/bin/env python3
"""
Test the unified WebSocket endpoint.
"""
import asyncio
import json
import websockets
import sys


async def test_websocket():
    """Test the unified WebSocket endpoint."""
    print("Testing unified WebSocket endpoint...")

    try:
        # Connect to the WebSocket endpoint
        uri = "ws://localhost:8000/ws"
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket")

            # Test ping/pong
            ping_message = {"id": "test-ping-1", "type": "ping", "data": {}}

            await websocket.send(json.dumps(ping_message))
            print("✓ Ping sent")

            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"✓ Received response: {response_data['type']}")

            if response_data.get("type") == "connect":
                print("✓ Connection confirmed")

            # Wait for pong
            pong_response = await websocket.recv()
            pong_data = json.loads(pong_response)
            print(f"✓ Received pong: {pong_data['type']}")

            print("✓ SUCCESS: WebSocket tests passed!")

    except Exception as e:
        print(f"✗ WebSocket test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_websocket())
