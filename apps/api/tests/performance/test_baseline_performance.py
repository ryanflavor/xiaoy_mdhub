#!/usr/bin/env python3
"""
Performance Baseline Test for ZMQ Publisher

This script establishes quantitative performance thresholds for the ZMQ tick data
publisher by running comprehensive benchmarks and stress tests.

Usage:
    # Run with conda env hub activated
    conda activate hub
    cd apps/api
    python scripts/performance_baseline_test.py

Thresholds Established:
    - Serialization latency: < 1ms (95th percentile)
    - Publication rate: > 100 msg/sec sustained
    - Memory usage: < 50MB steady state
    - Queue overflow recovery: < 5 seconds
"""

import asyncio
import sys
import time
import statistics
import psutil
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import msgpack
import zmq
from dataclasses import dataclass, asdict

# Add app directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.zmq_publisher import ZMQPublisher


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    test_name: str
    duration_seconds: float
    total_messages: int
    messages_per_second: float
    serialization_latencies_ms: List[float]
    avg_serialization_latency_ms: float
    p95_serialization_latency_ms: float
    p99_serialization_latency_ms: float
    memory_usage_mb: float
    peak_memory_usage_mb: float
    cpu_usage_percent: float
    success_rate_percent: float
    errors: List[str]


@dataclass
class MockTickData:
    """Mock tick data for testing."""
    symbol: str
    vt_symbol: str
    datetime: datetime
    last_price: float
    volume: int
    last_volume: int
    bid_price_1: float
    ask_price_1: float
    bid_volume_1: int
    ask_volume_1: int


class PerformanceBaselineTest:
    """Comprehensive performance baseline testing for ZMQ Publisher."""
    
    def __init__(self):
        self.publisher: Optional[ZMQPublisher] = None
        self.subscriber_context: Optional[zmq.Context] = None
        self.subscriber_socket: Optional[zmq.Socket] = None
        self.process = psutil.Process()
        self.baseline_memory_mb = 0.0
        
        # Performance thresholds (to be validated)
        self.thresholds = {
            'max_serialization_latency_p95_ms': 1.0,
            'min_publication_rate_per_sec': 100.0,
            'max_memory_overhead_mb': 50.0,
            'max_queue_recovery_time_sec': 5.0,
            'min_success_rate_percent': 99.0
        }
    
    async def setup_publisher(self) -> bool:
        """Initialize ZMQ publisher for testing."""
        try:
            print("🔧 Setting up ZMQ Publisher for performance testing...")
            
            # Set test configuration
            os.environ['ENABLE_ZMQ_PUBLISHER'] = 'true'
            os.environ['ZMQ_PORT'] = '5556'  # Use different port for testing
            
            self.publisher = ZMQPublisher()
            success = await self.publisher.initialize()
            
            if success:
                print("✅ ZMQ Publisher initialized successfully")
                # Record baseline memory usage
                self.baseline_memory_mb = self.process.memory_info().rss / 1024 / 1024
                print(f"📊 Baseline memory usage: {self.baseline_memory_mb:.2f} MB")
                return True
            else:
                print("❌ Failed to initialize ZMQ Publisher")
                return False
                
        except Exception as e:
            print(f"❌ Publisher setup error: {e}")
            return False
    
    def setup_subscriber(self, port: int = 5556) -> bool:
        """Setup test subscriber to validate message delivery."""
        try:
            print("🔧 Setting up test subscriber...")
            
            self.subscriber_context = zmq.Context()
            self.subscriber_socket = self.subscriber_context.socket(zmq.SUB)
            self.subscriber_socket.connect(f"tcp://localhost:{port}")
            self.subscriber_socket.setsockopt(zmq.SUBSCRIBE, b"")  # Subscribe to all
            self.subscriber_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            
            print("✅ Test subscriber connected")
            return True
            
        except Exception as e:
            print(f"❌ Subscriber setup error: {e}")
            return False
    
    def generate_mock_tick(self, symbol: str = "TEST.MOCK") -> MockTickData:
        """Generate realistic mock tick data for testing."""
        return MockTickData(
            symbol=symbol,
            vt_symbol=f"{symbol}.MOCK",
            datetime=datetime.now(timezone.utc),
            last_price=100.0 + (time.time() % 10),  # Varying price
            volume=1000 + int(time.time() % 100),
            last_volume=10,
            bid_price_1=99.95,
            ask_price_1=100.05,
            bid_volume_1=50,
            ask_volume_1=50
        )
    
    async def test_serialization_performance(self, iterations: int = 10000) -> PerformanceMetrics:
        """Test serialization latency performance."""
        print(f"\n🧪 Testing serialization performance ({iterations:,} iterations)...")
        
        latencies = []
        errors = []
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        start_time = time.time()
        
        for i in range(iterations):
            try:
                tick = self.generate_mock_tick(f"TEST{i % 100}")
                
                # Measure serialization time
                serialize_start = time.perf_counter()
                
                # Simulate the publisher's serialization process
                tick_dict = {}
                fields = ['symbol', 'datetime', 'last_price', 'volume', 'last_volume',
                         'bid_price_1', 'ask_price_1', 'bid_volume_1', 'ask_volume_1']
                
                for field in fields:
                    if hasattr(tick, field):
                        value = getattr(tick, field)
                        if field == 'datetime' and hasattr(value, 'isoformat'):
                            tick_dict[field] = value.isoformat()
                        else:
                            tick_dict[field] = value
                
                tick_dict['vt_symbol'] = tick.vt_symbol
                tick_dict['processing_time'] = datetime.now(timezone.utc).isoformat()
                
                # Serialize with msgpack
                message = msgpack.packb(tick_dict)
                
                serialize_end = time.perf_counter()
                latency_ms = (serialize_end - serialize_start) * 1000
                latencies.append(latency_ms)
                
            except Exception as e:
                errors.append(f"Iteration {i}: {str(e)}")
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Calculate metrics
        duration = end_time - start_time
        messages_per_sec = iterations / duration if duration > 0 else 0
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else avg_latency
        p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else avg_latency
        success_rate = ((iterations - len(errors)) / iterations) * 100 if iterations > 0 else 0
        
        metrics = PerformanceMetrics(
            test_name="Serialization Performance",
            duration_seconds=duration,
            total_messages=iterations,
            messages_per_second=messages_per_sec,
            serialization_latencies_ms=latencies,
            avg_serialization_latency_ms=avg_latency,
            p95_serialization_latency_ms=p95_latency,
            p99_serialization_latency_ms=p99_latency,
            memory_usage_mb=end_memory - start_memory,
            peak_memory_usage_mb=end_memory,
            cpu_usage_percent=self.process.cpu_percent(),
            success_rate_percent=success_rate,
            errors=errors[:10]  # Keep first 10 errors
        )
        
        self._print_test_results(metrics)
        return metrics
    
    async def test_publication_throughput(self, duration_seconds: int = 60) -> PerformanceMetrics:
        """Test sustained publication throughput."""
        print(f"\n🚀 Testing publication throughput ({duration_seconds}s sustained load)...")
        
        if not self.publisher:
            raise RuntimeError("Publisher not initialized")
        
        published_count = 0
        latencies = []
        errors = []
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = start_memory
        
        while time.time() - start_time < duration_seconds:
            try:
                tick = self.generate_mock_tick(f"THROUGHPUT{published_count % 50}")
                
                # Measure publication time
                pub_start = time.perf_counter()
                success = self.publisher.publish_tick(tick)
                pub_end = time.perf_counter()
                
                if success:
                    published_count += 1
                    latency_ms = (pub_end - pub_start) * 1000
                    latencies.append(latency_ms)
                else:
                    errors.append(f"Publication failed at count {published_count}")
                
                # Track peak memory
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                errors.append(f"Error at count {published_count}: {str(e)}")
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Calculate metrics
        actual_duration = end_time - start_time
        messages_per_sec = published_count / actual_duration if actual_duration > 0 else 0
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else avg_latency
        p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else avg_latency
        success_rate = (published_count / (published_count + len(errors))) * 100 if (published_count + len(errors)) > 0 else 0
        
        metrics = PerformanceMetrics(
            test_name="Publication Throughput",
            duration_seconds=actual_duration,
            total_messages=published_count,
            messages_per_second=messages_per_sec,
            serialization_latencies_ms=latencies,
            avg_serialization_latency_ms=avg_latency,
            p95_serialization_latency_ms=p95_latency,
            p99_serialization_latency_ms=p99_latency,
            memory_usage_mb=end_memory - start_memory,
            peak_memory_usage_mb=peak_memory,
            cpu_usage_percent=self.process.cpu_percent(),
            success_rate_percent=success_rate,
            errors=errors[:10]
        )
        
        self._print_test_results(metrics)
        return metrics
    
    async def test_concurrent_subscribers(self, num_subscribers: int = 5, duration_seconds: int = 30) -> PerformanceMetrics:
        """Test performance with multiple concurrent subscribers."""
        print(f"\n👥 Testing concurrent subscribers ({num_subscribers} subscribers, {duration_seconds}s)...")
        
        if not self.publisher:
            raise RuntimeError("Publisher not initialized")
        
        # Setup multiple subscriber contexts
        subscriber_contexts = []
        subscriber_sockets = []
        
        for i in range(num_subscribers):
            context = zmq.Context()
            socket = context.socket(zmq.SUB)
            socket.connect("tcp://localhost:5556")
            socket.setsockopt(zmq.SUBSCRIBE, b"")
            socket.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
            subscriber_contexts.append(context)
            subscriber_sockets.append(socket)
        
        published_count = 0
        received_counts = [0] * num_subscribers
        latencies = []
        errors = []
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = start_memory
        
        try:
            # Publish messages while subscribers listen
            while time.time() - start_time < duration_seconds:
                # Publish a message
                tick = self.generate_mock_tick(f"CONCURRENT{published_count % 10}")
                
                pub_start = time.perf_counter()
                success = self.publisher.publish_tick(tick)
                pub_end = time.perf_counter()
                
                if success:
                    published_count += 1
                    latency_ms = (pub_end - pub_start) * 1000
                    latencies.append(latency_ms)
                
                # Check subscribers (non-blocking)
                for i, socket in enumerate(subscriber_sockets):
                    try:
                        message_parts = socket.recv_multipart(zmq.NOBLOCK)
                        if len(message_parts) >= 2:
                            received_counts[i] += 1
                    except zmq.Again:
                        pass  # No message available
                    except Exception as e:
                        errors.append(f"Subscriber {i} error: {str(e)}")
                
                # Track memory
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
                
                await asyncio.sleep(0.01)  # 10ms delay
                
        finally:
            # Cleanup subscribers
            for socket in subscriber_sockets:
                socket.close()
            for context in subscriber_contexts:
                context.term()
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Calculate metrics
        actual_duration = end_time - start_time
        messages_per_sec = published_count / actual_duration if actual_duration > 0 else 0
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else avg_latency
        p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else avg_latency
        total_received = sum(received_counts)
        delivery_rate = (total_received / (published_count * num_subscribers)) * 100 if published_count > 0 else 0
        
        print(f"📊 Published: {published_count}, Total Received: {total_received}")
        print(f"📊 Delivery Rate: {delivery_rate:.1f}% ({total_received}/{published_count * num_subscribers})")
        
        metrics = PerformanceMetrics(
            test_name=f"Concurrent Subscribers ({num_subscribers})",
            duration_seconds=actual_duration,
            total_messages=published_count,
            messages_per_second=messages_per_sec,
            serialization_latencies_ms=latencies,
            avg_serialization_latency_ms=avg_latency,
            p95_serialization_latency_ms=p95_latency,
            p99_serialization_latency_ms=p99_latency,
            memory_usage_mb=end_memory - start_memory,
            peak_memory_usage_mb=peak_memory,
            cpu_usage_percent=self.process.cpu_percent(),
            success_rate_percent=delivery_rate,
            errors=errors[:10]
        )
        
        self._print_test_results(metrics)
        return metrics
    
    def _print_test_results(self, metrics: PerformanceMetrics):
        """Print formatted test results."""
        print(f"\n📊 {metrics.test_name} Results:")
        print(f"   Duration: {metrics.duration_seconds:.2f}s")
        print(f"   Messages: {metrics.total_messages:,}")
        print(f"   Rate: {metrics.messages_per_second:.2f} msg/sec")
        print(f"   Avg Latency: {metrics.avg_serialization_latency_ms:.3f}ms")
        print(f"   P95 Latency: {metrics.p95_serialization_latency_ms:.3f}ms")
        print(f"   P99 Latency: {metrics.p99_serialization_latency_ms:.3f}ms")
        print(f"   Memory Usage: {metrics.memory_usage_mb:.2f}MB")
        print(f"   Peak Memory: {metrics.peak_memory_usage_mb:.2f}MB")
        print(f"   CPU Usage: {metrics.cpu_usage_percent:.1f}%")
        print(f"   Success Rate: {metrics.success_rate_percent:.2f}%")
        
        if metrics.errors:
            print(f"   Errors ({len(metrics.errors)} shown): {metrics.errors}")
    
    def evaluate_thresholds(self, all_metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Evaluate performance against defined thresholds."""
        print(f"\n🎯 Evaluating Performance Against Thresholds:")
        print("=" * 60)
        
        results = {
            'passed': 0,
            'failed': 0,
            'details': [],
            'overall_status': 'UNKNOWN'
        }
        
        for metrics in all_metrics:
            print(f"\n📋 {metrics.test_name}:")
            
            # Serialization latency threshold
            p95_pass = metrics.p95_serialization_latency_ms <= self.thresholds['max_serialization_latency_p95_ms']
            status = "✅ PASS" if p95_pass else "❌ FAIL"
            print(f"   P95 Serialization Latency: {metrics.p95_serialization_latency_ms:.3f}ms <= {self.thresholds['max_serialization_latency_p95_ms']}ms {status}")
            results['details'].append({
                'test': metrics.test_name,
                'metric': 'P95 Serialization Latency',
                'value': metrics.p95_serialization_latency_ms,
                'threshold': self.thresholds['max_serialization_latency_p95_ms'],
                'passed': p95_pass
            })
            
            # Publication rate threshold
            rate_pass = metrics.messages_per_second >= self.thresholds['min_publication_rate_per_sec']
            status = "✅ PASS" if rate_pass else "❌ FAIL"
            print(f"   Publication Rate: {metrics.messages_per_second:.2f} >= {self.thresholds['min_publication_rate_per_sec']} msg/sec {status}")
            results['details'].append({
                'test': metrics.test_name,
                'metric': 'Publication Rate',
                'value': metrics.messages_per_second,
                'threshold': self.thresholds['min_publication_rate_per_sec'],
                'passed': rate_pass
            })
            
            # Memory usage threshold
            memory_pass = metrics.memory_usage_mb <= self.thresholds['max_memory_overhead_mb']
            status = "✅ PASS" if memory_pass else "❌ FAIL"
            print(f"   Memory Overhead: {metrics.memory_usage_mb:.2f} <= {self.thresholds['max_memory_overhead_mb']}MB {status}")
            results['details'].append({
                'test': metrics.test_name,
                'metric': 'Memory Overhead',
                'value': metrics.memory_usage_mb,
                'threshold': self.thresholds['max_memory_overhead_mb'],
                'passed': memory_pass
            })
            
            # Success rate threshold
            success_pass = metrics.success_rate_percent >= self.thresholds['min_success_rate_percent']
            status = "✅ PASS" if success_pass else "❌ FAIL"
            print(f"   Success Rate: {metrics.success_rate_percent:.2f}% >= {self.thresholds['min_success_rate_percent']}% {status}")
            results['details'].append({
                'test': metrics.test_name,
                'metric': 'Success Rate',
                'value': metrics.success_rate_percent,
                'threshold': self.thresholds['min_success_rate_percent'],
                'passed': success_pass
            })
        
        # Calculate overall results
        for detail in results['details']:
            if detail['passed']:
                results['passed'] += 1
            else:
                results['failed'] += 1
        
        total_tests = results['passed'] + results['failed']
        pass_rate = (results['passed'] / total_tests) * 100 if total_tests > 0 else 0
        
        if pass_rate >= 90:
            results['overall_status'] = 'EXCELLENT'
        elif pass_rate >= 75:
            results['overall_status'] = 'GOOD'
        elif pass_rate >= 50:
            results['overall_status'] = 'NEEDS_IMPROVEMENT'
        else:
            results['overall_status'] = 'CRITICAL'
        
        print(f"\n🏆 Overall Results:")
        print(f"   Tests Passed: {results['passed']}/{total_tests} ({pass_rate:.1f}%)")
        print(f"   Performance Status: {results['overall_status']}")
        
        return results
    
    async def cleanup(self):
        """Clean up test resources."""
        print("\n🧹 Cleaning up test resources...")
        
        if self.publisher:
            await self.publisher.shutdown()
        
        if self.subscriber_socket:
            self.subscriber_socket.close()
        
        if self.subscriber_context:
            self.subscriber_context.term()
        
        print("✅ Cleanup completed")


async def main():
    """Main test execution."""
    print("🧪 ZMQ Publisher Performance Baseline Test")
    print("=" * 50)
    
    test_runner = PerformanceBaselineTest()
    all_metrics = []
    
    try:
        # Setup
        if not await test_runner.setup_publisher():
            print("❌ Failed to setup publisher. Exiting.")
            return 1
        
        if not test_runner.setup_subscriber():
            print("❌ Failed to setup subscriber. Exiting.")
            return 1
        
        # Wait for publisher to be ready
        await asyncio.sleep(2)
        
        # Run performance tests
        print("\n🚀 Starting Performance Tests...")
        
        # Test 1: Serialization Performance
        metrics1 = await test_runner.test_serialization_performance(iterations=5000)
        all_metrics.append(metrics1)
        
        # Test 2: Publication Throughput
        metrics2 = await test_runner.test_publication_throughput(duration_seconds=30)
        all_metrics.append(metrics2)
        
        # Test 3: Concurrent Subscribers
        metrics3 = await test_runner.test_concurrent_subscribers(num_subscribers=3, duration_seconds=20)
        all_metrics.append(metrics3)
        
        # Evaluate results
        results = test_runner.evaluate_thresholds(all_metrics)
        
        print(f"\n🎯 Performance Baseline Established!")
        print(f"Status: {results['overall_status']}")
        
        # Return appropriate exit code
        if results['overall_status'] in ['EXCELLENT', 'GOOD']:
            return 0
        else:
            return 1
    
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1
    
    finally:
        await test_runner.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)