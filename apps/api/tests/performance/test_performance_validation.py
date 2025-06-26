#!/usr/bin/env python3
"""
Test Performance Validation Integration

Quick test to verify that the ZMQ Publisher performance validation
is working correctly with the established thresholds.

Usage:
    conda activate hub
    cd apps/api
    python scripts/test_performance_validation.py
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timezone

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.zmq_publisher import ZMQPublisher
from app.config.performance_thresholds import validate_performance_metric


class MockTickData:
    """Mock tick data for testing."""
    def __init__(self):
        self.symbol = "TEST"
        self.vt_symbol = "TEST.MOCK"
        self.datetime = datetime.now()
        self.last_price = 100.0
        self.volume = 1000
        self.last_volume = 10
        self.bid_price_1 = 99.95
        self.ask_price_1 = 100.05
        self.bid_volume_1 = 50
        self.ask_volume_1 = 50


async def test_performance_validation():
    """Test the performance validation integration."""
    print("🧪 Testing ZMQ Publisher Performance Validation Integration")
    print("=" * 60)
    
    # Set environment for testing
    os.environ['ENABLE_ZMQ_PUBLISHER'] = 'true'
    os.environ['ZMQ_PORT'] = '5557'  # Different port for testing
    
    publisher = None
    
    try:
        # Initialize publisher
        print("🔧 Initializing ZMQ Publisher...")
        publisher = ZMQPublisher()
        success = await publisher.initialize()
        
        if not success:
            print("❌ Failed to initialize publisher")
            return False
        
        print("✅ Publisher initialized successfully")
        
        # Test performance metrics validation
        print("\n📊 Testing performance metric validation...")
        
        # Test excellent performance (baseline values)
        print("\n1. Testing EXCELLENT performance metrics:")
        result1 = validate_performance_metric('serialization_p95_latency_ms', 0.004)
        print(f"   Serialization: {result1['status']} - {result1['message']}")
        
        result2 = validate_performance_metric('publication_rate_per_sec', 1030.0)
        print(f"   Publication Rate: {result2['status']} - {result2['message']}")
        
        # Test warning level performance
        print("\n2. Testing WARNING level performance:")
        result3 = validate_performance_metric('serialization_p95_latency_ms', 0.085)
        print(f"   Serialization: {result3['status']} - {result3['message']}")
        
        result4 = validate_performance_metric('publication_rate_per_sec', 420.0)
        print(f"   Publication Rate: {result4['status']} - {result4['message']}")
        
        # Test some tick publishing with performance monitoring
        print("\n🚀 Testing tick publishing with performance monitoring...")
        
        for i in range(100):  # Publish 100 ticks
            tick = MockTickData()
            tick.symbol = f"TEST{i % 5}"
            tick.vt_symbol = f"TEST{i % 5}.MOCK"
            
            success = publisher.publish_tick(tick)
            if not success:
                print(f"⚠️  Failed to publish tick {i}")
            
            # Small delay to avoid overwhelming
            await asyncio.sleep(0.001)
        
        print(f"✅ Published 100 test ticks")
        
        # Wait for performance log
        print("\n⏳ Waiting for performance metrics (30s interval)...")
        await asyncio.sleep(31)  # Wait for performance log
        
        # Check if we have performance alerts
        if hasattr(publisher, 'performance_alerts') and publisher.performance_alerts:
            print(f"\n📢 Performance alerts generated: {len(publisher.performance_alerts)}")
            for alert in publisher.performance_alerts[-3:]:  # Show last 3
                print(f"   Alert: {alert['serialization']['status']} serialization, {alert['publication_rate']['status']} publication rate")
        else:
            print(f"\n✅ No performance alerts (performance within thresholds)")
        
        print(f"\n✅ Performance validation test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
        
    finally:
        if publisher:
            print("\n🧹 Cleaning up...")
            await publisher.shutdown()


if __name__ == "__main__":
    result = asyncio.run(test_performance_validation())
    sys.exit(0 if result else 1)