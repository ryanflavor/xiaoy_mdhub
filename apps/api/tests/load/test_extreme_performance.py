#!/usr/bin/env python3
"""
Extreme Performance Test for 5000 msg/sec Target

Tests ZMQ Publisher at extreme load to validate if 5000 msg/sec is achievable.
"""

import asyncio
import sys
import os
import time
import statistics
from datetime import datetime, timezone
from typing import List

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.zmq_publisher import ZMQPublisher


class MockTickData:
    """Optimized mock tick data for extreme testing."""
    def __init__(self, i: int):
        self.symbol = f"T{i%10}"
        self.vt_symbol = f"T{i%10}.EXTR"
        self.datetime = datetime.now(timezone.utc)
        self.last_price = 100.0 + (i % 100) * 0.01
        self.volume = 1000 + i % 1000
        self.last_volume = 10
        self.bid_price_1 = self.last_price - 0.05
        self.ask_price_1 = self.last_price + 0.05
        self.bid_volume_1 = 50
        self.ask_volume_1 = 50


async def test_extreme_throughput(target_rate: int = 5000, duration_seconds: int = 10):
    """Test extreme throughput capability."""
    print(f"🚀 Extreme Performance Test - Target: {target_rate:,} msg/sec")
    print("=" * 60)
    
    # Environment setup
    os.environ['ENABLE_ZMQ_PUBLISHER'] = 'true'
    os.environ['ZMQ_PORT'] = '5558'
    os.environ['ZMQ_PERFORMANCE_MODE'] = 'production'
    
    publisher = None
    
    try:
        # Initialize publisher
        print("🔧 Initializing ZMQ Publisher for extreme testing...")
        publisher = ZMQPublisher()
        success = await publisher.initialize()
        
        if not success:
            print("❌ Failed to initialize publisher")
            return False
        
        print("✅ Publisher initialized")
        
        # Pre-generate tick data to avoid allocation overhead
        print(f"📦 Pre-generating {target_rate * duration_seconds:,} tick objects...")
        tick_data = [MockTickData(i) for i in range(target_rate * duration_seconds)]
        print("✅ Tick data generated")
        
        # Extreme throughput test
        print(f"\n🏃‍♂️ Running extreme throughput test:")
        print(f"   Target: {target_rate:,} msg/sec for {duration_seconds} seconds")
        print(f"   Total messages: {target_rate * duration_seconds:,}")
        
        published_count = 0
        failed_count = 0
        latencies = []
        start_time = time.time()
        last_log_time = start_time
        
        # Calculate target delay between messages
        target_delay = 1.0 / target_rate  # seconds between messages
        
        tick_index = 0
        while time.time() - start_time < duration_seconds and tick_index < len(tick_data):
            loop_start = time.time()
            
            # Publish tick
            pub_start = time.perf_counter()
            success = publisher.publish_tick(tick_data[tick_index])
            pub_end = time.perf_counter()
            
            if success:
                published_count += 1
                latency_ms = (pub_end - pub_start) * 1000
                latencies.append(latency_ms)
            else:
                failed_count += 1
            
            tick_index += 1
            
            # Log progress every second
            current_time = time.time()
            if current_time - last_log_time >= 1.0:
                elapsed = current_time - start_time
                current_rate = published_count / elapsed if elapsed > 0 else 0
                print(f"   Progress: {elapsed:.1f}s | Published: {published_count:,} | Rate: {current_rate:.0f} msg/sec")
                last_log_time = current_time
            
            # Rate limiting (only if we're ahead of schedule)
            loop_time = time.time() - loop_start
            if loop_time < target_delay:
                await asyncio.sleep(target_delay - loop_time)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Calculate final metrics
        actual_rate = published_count / actual_duration if actual_duration > 0 else 0
        success_rate = (published_count / (published_count + failed_count)) * 100 if (published_count + failed_count) > 0 else 0
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else avg_latency
        p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else avg_latency
        
        # Results
        print(f"\n📊 Extreme Performance Test Results:")
        print(f"   Duration: {actual_duration:.2f}s")
        print(f"   Target Rate: {target_rate:,} msg/sec")
        print(f"   Actual Rate: {actual_rate:.0f} msg/sec")
        print(f"   Achievement: {(actual_rate/target_rate)*100:.1f}% of target")
        print(f"   Published: {published_count:,} messages")
        print(f"   Failed: {failed_count:,} messages") 
        print(f"   Success Rate: {success_rate:.2f}%")
        print(f"   Avg Latency: {avg_latency:.3f}ms")
        print(f"   P95 Latency: {p95_latency:.3f}ms")
        print(f"   P99 Latency: {p99_latency:.3f}ms")
        
        # Assessment
        print(f"\n🎯 Assessment:")
        if actual_rate >= target_rate * 0.9:  # 90% of target
            print(f"   ✅ EXCELLENT - Achieved {(actual_rate/target_rate)*100:.1f}% of {target_rate:,} msg/sec target")
            status = "CAPABLE"
        elif actual_rate >= target_rate * 0.7:  # 70% of target
            print(f"   ⚠️  GOOD - Achieved {(actual_rate/target_rate)*100:.1f}% of {target_rate:,} msg/sec target")
            print(f"   📈 Optimization may reach full target")
            status = "NEAR_CAPABLE"
        elif actual_rate >= target_rate * 0.5:  # 50% of target
            print(f"   ⚠️  MODERATE - Achieved {(actual_rate/target_rate)*100:.1f}% of {target_rate:,} msg/sec target")
            print(f"   🔧 Significant optimization required")
            status = "NEEDS_OPTIMIZATION"
        else:
            print(f"   ❌ INSUFFICIENT - Only achieved {(actual_rate/target_rate)*100:.1f}% of {target_rate:,} msg/sec target")
            print(f"   🚨 Architecture changes may be required")
            status = "INSUFFICIENT"
        
        return {
            'status': status,
            'target_rate': target_rate,
            'actual_rate': actual_rate,
            'achievement_percent': (actual_rate/target_rate)*100,
            'published_count': published_count,
            'success_rate': success_rate,
            'avg_latency_ms': avg_latency,
            'p95_latency_ms': p95_latency,
            'p99_latency_ms': p99_latency
        }
        
    except Exception as e:
        print(f"❌ Extreme test failed: {e}")
        return {'status': 'ERROR', 'error': str(e)}
        
    finally:
        if publisher:
            print("\n🧹 Cleaning up...")
            await publisher.shutdown()


async def test_burst_capability():
    """Test short burst capability at maximum rate."""
    print(f"\n⚡ Burst Capability Test (No Rate Limiting)")
    print("=" * 40)
    
    os.environ['ZMQ_PORT'] = '5559'
    publisher = ZMQPublisher()
    
    try:
        await publisher.initialize()
        
        # Generate test data
        burst_size = 1000
        tick_data = [MockTickData(i) for i in range(burst_size)]
        
        # Maximum speed burst test
        print(f"🚀 Publishing {burst_size:,} messages at maximum speed...")
        
        start_time = time.perf_counter()
        published = 0
        
        for tick in tick_data:
            if publisher.publish_tick(tick):
                published += 1
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        burst_rate = published / duration if duration > 0 else 0
        
        print(f"📊 Burst Results:")
        print(f"   Duration: {duration:.3f}s")
        print(f"   Published: {published:,} messages")
        print(f"   Burst Rate: {burst_rate:.0f} msg/sec")
        print(f"   5K Target: {burst_rate >= 5000}")
        
        return burst_rate
        
    finally:
        await publisher.shutdown()


async def main():
    """Main test execution."""
    print("🧪 ZMQ Publisher Extreme Performance Analysis")
    print("Testing capability for 5,000 msg/sec requirement")
    print("=" * 60)
    
    # Test 1: Burst capability
    burst_rate = await test_burst_capability()
    
    # Test 2: Sustained 5K msg/sec
    result_5k = await test_extreme_throughput(target_rate=5000, duration_seconds=10)
    
    # Test 3: Sustained at current proven rate
    result_1k = await test_extreme_throughput(target_rate=1000, duration_seconds=10)
    
    # Summary
    print(f"\n🏆 FINAL ASSESSMENT FOR 5,000 MSG/SEC REQUIREMENT:")
    print("=" * 60)
    
    print(f"💥 Burst Capability: {burst_rate:.0f} msg/sec")
    
    if 'actual_rate' in result_5k:
        print(f"🎯 Sustained 5K Test: {result_5k['actual_rate']:.0f} msg/sec ({result_5k['achievement_percent']:.1f}%)")
        print(f"✅ 1K Baseline Test: {result_1k['actual_rate']:.0f} msg/sec ({result_1k['achievement_percent']:.1f}%)")
        
        if result_5k['status'] in ['CAPABLE', 'NEAR_CAPABLE']:
            print(f"\n✅ CONCLUSION: 5,000 msg/sec requirement is {'ACHIEVABLE' if result_5k['status'] == 'CAPABLE' else 'LIKELY ACHIEVABLE'}")
        else:
            print(f"\n⚠️  CONCLUSION: 5,000 msg/sec requirement needs optimization")
            print(f"   Current capability: ~{result_5k['actual_rate']:.0f} msg/sec")
            print(f"   Gap: {5000 - result_5k['actual_rate']:.0f} msg/sec")


if __name__ == "__main__":
    asyncio.run(main())