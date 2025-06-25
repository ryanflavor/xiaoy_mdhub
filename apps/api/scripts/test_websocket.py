#!/usr/bin/env python3
"""
Manual WebSocket test script for testing the WebSocket endpoint.

Usage:
    python scripts/test_websocket.py [--url ws://localhost:8000/ws] [--token your_token]
"""

import asyncio
import json
import sys
import argparse
from datetime import datetime
import websockets
from typing import Optional


async def test_websocket_connection(url: str, token: Optional[str] = None):
    """Test WebSocket connection and message handling."""
    # Add token to URL if provided
    if token:
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}token={token}"
    
    print(f"Connecting to: {url}")
    
    try:
        async with websockets.connect(url) as websocket:
            print("✓ Connected successfully!")
            
            # Receive initial connection message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"✓ Received connection message: {data}")
            
            if data.get("event_type") == "connection" and data.get("client_id"):
                print(f"  Client ID: {data['client_id']}")
            
            # Send a ping message
            ping_message = {
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send(json.dumps(ping_message))
            print(f"✓ Sent ping: {ping_message}")
            
            # Set up message listener
            print("\nListening for messages (press Ctrl+C to stop)...")
            print("-" * 50)
            
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(message)
                    
                    # Format and display message
                    event_type = data.get("event_type") or data.get("type", "unknown")
                    timestamp = data.get("timestamp", "")
                    
                    print(f"\n[{timestamp}] {event_type.upper()}")
                    
                    if event_type == "gateway_status_change":
                        print(f"  Gateway: {data.get('gateway_id')}")
                        print(f"  Status: {data.get('previous_status')} → {data.get('current_status')}")
                    
                    elif event_type == "system_log":
                        print(f"  Level: {data.get('level')}")
                        print(f"  Source: {data.get('source')}")
                        print(f"  Message: {data.get('message')}")
                    
                    elif event_type == "gateway_recovery_status":
                        print(f"  Gateway: {data.get('gateway_id')}")
                        print(f"  Status: {data.get('recovery_status')}")
                        print(f"  Attempt: {data.get('attempt')}")
                    
                    elif event_type == "pong":
                        print("  ✓ Received pong response")
                    
                    else:
                        # Print full message for unknown types
                        print(f"  Data: {json.dumps(data, indent=2)}")
                    
                    print("-" * 50)
                    
            except asyncio.TimeoutError:
                print("\nNo messages received for 60 seconds")
            except KeyboardInterrupt:
                print("\n\nClosing connection...")
                
    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)
    
    print("✓ Connection closed")


async def trigger_test_events():
    """Trigger test events through the API (requires running server)."""
    import aiohttp
    
    print("\nTriggering test events...")
    
    async with aiohttp.ClientSession() as session:
        # You can add API calls here to trigger events
        # For example, marking a gateway as unhealthy
        pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test WebSocket connection")
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/ws",
        help="WebSocket URL (default: ws://localhost:8000/ws)"
    )
    parser.add_argument(
        "--token",
        default="test_token",
        help="Authentication token (default: test_token)"
    )
    parser.add_argument(
        "--no-token",
        action="store_true",
        help="Connect without authentication token"
    )
    
    args = parser.parse_args()
    
    # Run the test
    token = None if args.no_token else args.token
    asyncio.run(test_websocket_connection(args.url, token))


if __name__ == "__main__":
    main()