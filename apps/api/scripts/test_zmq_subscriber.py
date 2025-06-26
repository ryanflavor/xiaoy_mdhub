#!/usr/bin/env python3
"""
ZeroMQ Test Subscriber Script

This script demonstrates end-to-end connectivity by subscribing to the ZMQ publisher
and receiving tick data messages. It validates the complete data pipeline from
CTP ingestion to client consumption.

Usage:
    python scripts/test_zmq_subscriber.py [--port PORT] [--topic TOPIC] [--count COUNT]

Examples:
    # Subscribe to all topics on default port
    python scripts/test_zmq_subscriber.py
    
    # Subscribe to specific symbol
    python scripts/test_zmq_subscriber.py --topic rb2601.SHFE
    
    # Receive only 10 messages then exit
    python scripts/test_zmq_subscriber.py --count 10
"""

import argparse
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import zmq
import msgpack


class ZMQTestSubscriber:
    """Test subscriber for validating ZMQ tick data distribution."""
    
    def __init__(self, port: int = 5555, host: str = "localhost"):
        self.port = port
        self.host = host
        self.context: Optional[zmq.Context] = None
        self.socket: Optional[zmq.Socket] = None
        self.is_running = False
        self.message_count = 0
        self.start_time: Optional[datetime] = None
        
        # Statistics
        self.topics_received = set()
        self.latencies = []
        
    def connect(self) -> bool:
        """
        Connect to ZMQ publisher.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            print(f"Connecting to ZMQ publisher at tcp://{self.host}:{self.port}")
            
            # Create ZMQ context and socket
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.SUB)
            
            # Connect to publisher
            self.socket.connect(f"tcp://{self.host}:{self.port}")
            
            # Set socket options
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            
            print("Connected successfully!")
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def subscribe(self, topic: str = "") -> None:
        """
        Subscribe to specific topic or all topics.
        
        Args:
            topic: Topic to subscribe to (empty string for all topics)
        """
        if not self.socket:
            raise RuntimeError("Socket not connected")
        
        # Subscribe to topic
        self.socket.setsockopt(zmq.SUBSCRIBE, topic.encode('utf-8'))
        
        if topic:
            print(f"Subscribed to topic: {topic}")
        else:
            print("Subscribed to all topics")
    
    def run(self, max_messages: Optional[int] = None, topic_filter: str = "") -> None:
        """
        Run the subscriber to receive and validate messages.
        
        Args:
            max_messages: Maximum number of messages to receive (None for unlimited)
            topic_filter: Topic filter for subscription
        """
        if not self.connect():
            return
        
        try:
            # Subscribe to topics
            self.subscribe(topic_filter)
            
            self.is_running = True
            self.start_time = datetime.now(timezone.utc)
            
            print("\n" + "="*60)
            print("ZMQ Test Subscriber Started")
            print("="*60)
            print("Waiting for messages... (Press Ctrl+C to stop)")
            print()
            
            while self.is_running:
                try:
                    # Check if we've reached the message limit
                    if max_messages and self.message_count >= max_messages:
                        print(f"\nReached maximum message count ({max_messages}). Stopping...")
                        break
                    
                    # Receive message with timeout
                    message_parts = self.socket.recv_multipart(zmq.NOBLOCK)
                    
                    if len(message_parts) >= 2:
                        topic = message_parts[0].decode('utf-8')
                        message_data = message_parts[1]
                        
                        # Process the message
                        self._process_message(topic, message_data)
                    
                except zmq.Again:
                    # Timeout - no message received
                    time.sleep(0.1)
                    continue
                    
                except zmq.ZMQError as e:
                    print(f"ZMQ Error: {e}")
                    break
                    
        except KeyboardInterrupt:
            print("\nReceived interrupt signal. Stopping...")
        finally:
            self._shutdown()
            self._print_statistics()
    
    def _process_message(self, topic: str, message_data: bytes) -> None:
        """
        Process received message and validate format.
        
        Args:
            topic: Message topic
            message_data: Serialized message data
        """
        try:
            # Deserialize message using msgpack
            tick_data = msgpack.unpackb(message_data, raw=False)
            
            # Track statistics
            self.message_count += 1
            self.topics_received.add(topic)
            
            # Calculate latency if processing_time is available
            latency_ms = None
            if 'processing_time' in tick_data:
                try:
                    processing_time = datetime.fromisoformat(tick_data['processing_time'].replace('Z', '+00:00'))
                    current_time = datetime.now(timezone.utc)
                    latency_ms = (current_time - processing_time).total_seconds() * 1000
                    self.latencies.append(latency_ms)
                except:
                    pass  # Ignore latency calculation errors
            
            # Validate tick data format
            validation_result = self._validate_tick_data(tick_data)
            
            # Print message summary
            print(f"[{self.message_count:04d}] Topic: {topic}")
            print(f"       Symbol: {tick_data.get('symbol', 'N/A')}")
            print(f"       Price: {tick_data.get('last_price', 'N/A')}")
            print(f"       Volume: {tick_data.get('volume', 'N/A')}")
            print(f"       Time: {tick_data.get('datetime', 'N/A')}")
            
            if latency_ms is not None:
                print(f"       Latency: {latency_ms:.2f}ms")
            
            if not validation_result['valid']:
                print(f"       ⚠️  Validation Issues: {', '.join(validation_result['issues'])}")
            else:
                print(f"       ✅ Data Valid")
            
            print()
            
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def _validate_tick_data(self, tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate tick data format and completeness.
        
        Args:
            tick_data: Deserialized tick data
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        # Check essential fields
        essential_fields = ['symbol', 'last_price', 'volume']
        for field in essential_fields:
            if field not in tick_data:
                issues.append(f"Missing {field}")
            elif tick_data[field] is None:
                issues.append(f"Null {field}")
        
        # Check price validity
        if 'last_price' in tick_data:
            try:
                price = float(tick_data['last_price'])
                if price <= 0:
                    issues.append("Invalid price (<=0)")
            except (ValueError, TypeError):
                issues.append("Invalid price format")
        
        # Check volume validity
        if 'volume' in tick_data:
            try:
                volume = int(tick_data['volume'])
                if volume < 0:
                    issues.append("Invalid volume (<0)")
            except (ValueError, TypeError):
                issues.append("Invalid volume format")
        
        # Check datetime format
        if 'datetime' in tick_data:
            try:
                if isinstance(tick_data['datetime'], str):
                    datetime.fromisoformat(tick_data['datetime'].replace('Z', '+00:00'))
            except:
                issues.append("Invalid datetime format")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    def _shutdown(self) -> None:
        """Clean up ZMQ resources."""
        self.is_running = False
        
        if self.socket:
            self.socket.close()
            self.socket = None
        
        if self.context:
            self.context.term()
            self.context = None
    
    def _print_statistics(self) -> None:
        """Print subscription statistics."""
        if not self.start_time:
            return
        
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        print("\n" + "="*60)
        print("SUBSCRIPTION STATISTICS")
        print("="*60)
        print(f"Total Messages Received: {self.message_count}")
        print(f"Unique Topics: {len(self.topics_received)}")
        print(f"Topics Received: {', '.join(sorted(self.topics_received)) if self.topics_received else 'None'}")
        print(f"Duration: {duration:.2f} seconds")
        
        if self.message_count > 0 and duration > 0:
            rate = self.message_count / duration
            print(f"Average Rate: {rate:.2f} messages/second")
        
        if self.latencies:
            avg_latency = sum(self.latencies) / len(self.latencies)
            min_latency = min(self.latencies)
            max_latency = max(self.latencies)
            print(f"Average Latency: {avg_latency:.2f}ms")
            print(f"Min Latency: {min_latency:.2f}ms")
            print(f"Max Latency: {max_latency:.2f}ms")
        
        print("="*60)


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    print("\nReceived interrupt signal. Shutting down...")
    sys.exit(0)


def main():
    """Main entry point for the test subscriber."""
    parser = argparse.ArgumentParser(
        description="ZeroMQ Test Subscriber for Market Data Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Subscribe to all topics
  %(prog)s --topic rb2601.SHFE          # Subscribe to specific symbol
  %(prog)s --count 10                   # Receive 10 messages then exit
  %(prog)s --port 5556 --host 192.168.1.100  # Connect to remote host
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5555,
        help='ZMQ publisher port (default: 5555)'
    )
    
    parser.add_argument(
        '--host', '-H',
        type=str,
        default='localhost',
        help='ZMQ publisher host (default: localhost)'
    )
    
    parser.add_argument(
        '--topic', '-t',
        type=str,
        default='',
        help='Topic filter (empty for all topics)'
    )
    
    parser.add_argument(
        '--count', '-c',
        type=int,
        help='Maximum number of messages to receive'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run subscriber
    subscriber = ZMQTestSubscriber(port=args.port, host=args.host)
    
    try:
        subscriber.run(max_messages=args.count, topic_filter=args.topic)
    except Exception as e:
        print(f"Subscriber error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()