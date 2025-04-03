import websockets
import asyncio
import json
import sys

async def test_websocket():
    uri = "ws://startup-hub:8000/"
    try:
        print(f"Attempting to connect to {uri}")
        async with websockets.connect(uri) as websocket:
            print("Successfully connected to WebSocket!")
            # Send a test message
            await websocket.send(json.dumps({"type": "ping"}))
            # Wait for response
            response = await websocket.recv()
            print(f"Received response: {response}")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"Invalid status code: {e.status_code}")
        print(f"Response headers: {e.headers}")
        print(f"Response body: {e.body if hasattr(e, 'body') else 'No body'}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection closed: {e.code} - {e.reason}")
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'status_code'):
            print(f"Status code: {e.status_code}")
        if hasattr(e, 'headers'):
            print(f"Response headers: {e.headers}")
        if hasattr(e, 'body'):
            print(f"Response body: {e.body}")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 