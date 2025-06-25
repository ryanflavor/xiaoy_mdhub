#!/usr/bin/env python3
"""
Performance and load testing for database operations.

This script tests the performance of database operations under various loads
and validates that the system meets performance requirements.
"""

import asyncio
import time
import statistics
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import db_manager
from app.services.database_service import database_service


class PerformanceMetrics:
    """Class to track performance metrics."""
    
    def __init__(self):
        self.operation_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
    
    def record_operation(self, operation: str, duration: float, error: bool = False):
        """Record an operation's performance."""
        if operation not in self.operation_times:
            self.operation_times[operation] = []
            self.error_counts[operation] = 0
        
        if not error:
            self.operation_times[operation].append(duration)
        else:
            self.error_counts[operation] += 1
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        times = self.operation_times.get(operation, [])
        if not times:
            return {"count": 0, "errors": self.error_counts.get(operation, 0)}
        
        return {
            "count": len(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "p95": times[int(len(times) * 0.95)] if len(times) > 20 else max(times),
            "p99": times[int(len(times) * 0.99)] if len(times) > 100 else max(times),
            "errors": self.error_counts.get(operation, 0)
        }


async def test_single_operation_performance():
    """Test performance of individual database operations."""
    print("🏃 Testing Single Operation Performance")
    print("=" * 50)
    
    metrics = PerformanceMetrics()
    
    # Test data
    test_account = {
        "id": "perf_test_account",
        "gateway_type": "ctp",
        "settings": {
            "userID": "perf_user",
            "password": "perf_password",
            "brokerID": "9999",
            "mdAddress": "tcp://perf.test.com:41213"
        },
        "priority": 1,
        "is_enabled": True,
        "description": "Performance test account"
    }
    
    # Test CREATE operation
    print("1. Testing CREATE operation performance...")
    for i in range(10):
        test_account["id"] = f"perf_test_account_{i}"
        
        start_time = time.time()
        try:
            result = await database_service.create_account(test_account)
            duration = time.time() - start_time
            metrics.record_operation("create", duration, error=result is None)
        except Exception as e:
            duration = time.time() - start_time
            metrics.record_operation("create", duration, error=True)
    
    create_stats = metrics.get_stats("create")
    print(f"   CREATE: {create_stats['count']} ops, avg: {create_stats['mean']*1000:.2f}ms, max: {create_stats['max']*1000:.2f}ms")
    
    # Test READ operation
    print("2. Testing READ operation performance...")
    for i in range(50):  # More reads to test performance
        start_time = time.time()
        try:
            result = await database_service.get_account(f"perf_test_account_{i % 10}")
            duration = time.time() - start_time
            metrics.record_operation("read", duration, error=result is None)
        except Exception as e:
            duration = time.time() - start_time
            metrics.record_operation("read", duration, error=True)
    
    read_stats = metrics.get_stats("read")
    print(f"   READ: {read_stats['count']} ops, avg: {read_stats['mean']*1000:.2f}ms, max: {read_stats['max']*1000:.2f}ms")
    
    # Test UPDATE operation
    print("3. Testing UPDATE operation performance...")
    for i in range(10):
        start_time = time.time()
        try:
            result = await database_service.update_account(
                f"perf_test_account_{i}",
                {"priority": i + 10, "description": f"Updated account {i}"}
            )
            duration = time.time() - start_time
            metrics.record_operation("update", duration, error=result is None)
        except Exception as e:
            duration = time.time() - start_time
            metrics.record_operation("update", duration, error=True)
    
    update_stats = metrics.get_stats("update")
    print(f"   UPDATE: {update_stats['count']} ops, avg: {update_stats['mean']*1000:.2f}ms, max: {update_stats['max']*1000:.2f}ms")
    
    # Test LIST operation
    print("4. Testing LIST operation performance...")
    for i in range(20):
        start_time = time.time()
        try:
            result = await database_service.get_all_accounts()
            duration = time.time() - start_time
            metrics.record_operation("list", duration, error=len(result) == 0)
        except Exception as e:
            duration = time.time() - start_time
            metrics.record_operation("list", duration, error=True)
    
    list_stats = metrics.get_stats("list")
    print(f"   LIST: {list_stats['count']} ops, avg: {list_stats['mean']*1000:.2f}ms, max: {list_stats['max']*1000:.2f}ms")
    
    # Test DELETE operation
    print("5. Testing DELETE operation performance...")
    for i in range(10):
        start_time = time.time()
        try:
            result = await database_service.delete_account(f"perf_test_account_{i}")
            duration = time.time() - start_time
            metrics.record_operation("delete", duration, error=not result)
        except Exception as e:
            duration = time.time() - start_time
            metrics.record_operation("delete", duration, error=True)
    
    delete_stats = metrics.get_stats("delete")
    print(f"   DELETE: {delete_stats['count']} ops, avg: {delete_stats['mean']*1000:.2f}ms, max: {delete_stats['max']*1000:.2f}ms")
    
    # Performance validation
    performance_thresholds = {
        "create": 100,  # 100ms max for CREATE
        "read": 50,     # 50ms max for READ  
        "update": 100,  # 100ms max for UPDATE
        "list": 200,    # 200ms max for LIST
        "delete": 100   # 100ms max for DELETE
    }
    
    print("\n6. Performance validation against thresholds...")
    all_passed = True
    for operation, threshold_ms in performance_thresholds.items():
        stats = metrics.get_stats(operation)
        if stats.get("max", 0) * 1000 > threshold_ms:
            print(f"❌ {operation.upper()}: {stats['max']*1000:.2f}ms exceeds {threshold_ms}ms threshold")
            all_passed = False
        else:
            print(f"✅ {operation.upper()}: {stats['max']*1000:.2f}ms within {threshold_ms}ms threshold")
    
    return all_passed, metrics


async def test_concurrent_operations():
    """Test concurrent database operations."""
    print("\n🔄 Testing Concurrent Operations")
    print("=" * 50)
    
    async def create_account_batch(batch_id: int, batch_size: int):
        """Create a batch of accounts concurrently."""
        results = []
        for i in range(batch_size):
            account_data = {
                "id": f"concurrent_test_{batch_id}_{i}",
                "gateway_type": "ctp" if i % 2 == 0 else "sopt",
                "settings": {
                    "userID": f"concurrent_user_{batch_id}_{i}",
                    "password": "test_password",
                    "brokerID": "9999" if i % 2 == 0 else None,
                    "username": f"sopt_user_{i}" if i % 2 == 1 else None,
                    "token": "sopt_token" if i % 2 == 1 else None
                },
                "priority": i + 1,
                "is_enabled": True,
                "description": f"Concurrent test account {batch_id}_{i}"
            }
            
            try:
                result = await database_service.create_account(account_data)
                results.append(result is not None)
            except Exception as e:
                results.append(False)
        
        return results
    
    # Test concurrent creation
    print("1. Testing concurrent account creation...")
    batch_size = 5
    num_batches = 4
    
    start_time = time.time()
    
    # Create batches concurrently
    tasks = [create_account_batch(batch_id, batch_size) for batch_id in range(num_batches)]
    batch_results = await asyncio.gather(*tasks)
    
    creation_time = time.time() - start_time
    
    total_created = sum(sum(batch) for batch in batch_results)
    total_attempted = batch_size * num_batches
    
    print(f"   Created {total_created}/{total_attempted} accounts in {creation_time:.2f}s")
    print(f"   Average: {creation_time/total_attempted*1000:.2f}ms per account")
    
    if total_created < total_attempted * 0.95:  # 95% success rate
        print("❌ Concurrent creation success rate too low")
        return False
    else:
        print("✅ Concurrent creation successful")
    
    # Test concurrent reads
    print("\n2. Testing concurrent reads...")
    
    async def read_accounts_batch():
        """Read accounts concurrently."""
        read_results = []
        for batch_id in range(num_batches):
            for i in range(batch_size):
                account_id = f"concurrent_test_{batch_id}_{i}"
                try:
                    result = await database_service.get_account(account_id)
                    read_results.append(result is not None)
                except Exception:
                    read_results.append(False)
        return read_results
    
    start_time = time.time()
    
    # Run multiple concurrent read operations
    read_tasks = [read_accounts_batch() for _ in range(3)]
    read_results = await asyncio.gather(*read_tasks)
    
    read_time = time.time() - start_time
    
    total_reads = sum(len(batch) for batch in read_results)
    successful_reads = sum(sum(batch) for batch in read_results)
    
    print(f"   Completed {successful_reads}/{total_reads} reads in {read_time:.2f}s")
    print(f"   Average: {read_time/total_reads*1000:.2f}ms per read")
    
    if successful_reads < total_reads * 0.95:
        print("❌ Concurrent read success rate too low")
        return False
    else:
        print("✅ Concurrent reads successful")
    
    # Cleanup
    print("\n3. Cleaning up test data...")
    cleanup_count = 0
    for batch_id in range(num_batches):
        for i in range(batch_size):
            account_id = f"concurrent_test_{batch_id}_{i}"
            try:
                result = await database_service.delete_account(account_id)
                if result:
                    cleanup_count += 1
            except Exception:
                pass
    
    print(f"   Cleaned up {cleanup_count} test accounts")
    
    return True


async def test_large_dataset_performance():
    """Test performance with larger datasets."""
    print("\n📊 Testing Large Dataset Performance")
    print("=" * 50)
    
    # Create 100 test accounts
    print("1. Creating 100 test accounts...")
    
    creation_times = []
    successful_creates = 0
    
    for i in range(100):
        account_data = {
            "id": f"large_test_account_{i:03d}",
            "gateway_type": "ctp" if i % 3 == 0 else "sopt",
            "settings": {
                "userID": f"large_user_{i:03d}" if i % 3 == 0 else None,
                "password": "test_password" if i % 3 == 0 else None,
                "brokerID": "9999" if i % 3 == 0 else None,
                "username": f"sopt_user_{i:03d}" if i % 3 != 0 else None,
                "token": "sopt_token" if i % 3 != 0 else None,
                "serverAddress": "tcp://test.com:7709" if i % 3 != 0 else None
            },
            "priority": (i % 10) + 1,
            "is_enabled": i % 4 != 0,  # 75% enabled
            "description": f"Large dataset test account {i:03d}"
        }
        
        start_time = time.time()
        try:
            result = await database_service.create_account(account_data)
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            if result:
                successful_creates += 1
        except Exception as e:
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
    
    avg_creation_time = statistics.mean(creation_times) * 1000
    max_creation_time = max(creation_times) * 1000
    
    print(f"   Created {successful_creates}/100 accounts")
    print(f"   Average creation time: {avg_creation_time:.2f}ms")
    print(f"   Max creation time: {max_creation_time:.2f}ms")
    
    # Test listing performance with large dataset
    print("\n2. Testing list performance with large dataset...")
    
    list_times = []
    for i in range(10):
        start_time = time.time()
        try:
            accounts = await database_service.get_all_accounts()
            list_time = time.time() - start_time
            list_times.append(list_time)
        except Exception:
            list_time = time.time() - start_time
            list_times.append(list_time)
    
    avg_list_time = statistics.mean(list_times) * 1000
    max_list_time = max(list_times) * 1000
    
    print(f"   Average list time: {avg_list_time:.2f}ms")
    print(f"   Max list time: {max_list_time:.2f}ms")
    
    # Test filtering performance
    print("\n3. Testing filtering performance...")
    
    filter_times = []
    for gateway_type in ["ctp", "sopt"]:
        for i in range(5):
            start_time = time.time()
            try:
                filtered_accounts = await database_service.get_accounts_by_gateway_type(gateway_type)
                filter_time = time.time() - start_time
                filter_times.append(filter_time)
            except Exception:
                filter_time = time.time() - start_time
                filter_times.append(filter_time)
    
    avg_filter_time = statistics.mean(filter_times) * 1000
    
    print(f"   Average filter time: {avg_filter_time:.2f}ms")
    
    # Cleanup
    print("\n4. Cleaning up large dataset...")
    cleanup_count = 0
    for i in range(100):
        try:
            result = await database_service.delete_account(f"large_test_account_{i:03d}")
            if result:
                cleanup_count += 1
        except Exception:
            pass
    
    print(f"   Cleaned up {cleanup_count}/100 accounts")
    
    # Performance validation
    performance_ok = True
    if avg_creation_time > 200:  # 200ms threshold
        print("❌ Average creation time too high")
        performance_ok = False
    
    if avg_list_time > 500:  # 500ms threshold for large dataset
        print("❌ List performance too slow with large dataset")
        performance_ok = False
    
    if avg_filter_time > 300:  # 300ms threshold for filtering
        print("❌ Filter performance too slow")
        performance_ok = False
    
    if performance_ok:
        print("✅ Large dataset performance acceptable")
    
    return performance_ok


async def main():
    """Main performance test function."""
    print("🚀 Starting Performance & Load Testing")
    print("=" * 60)
    
    # Initialize database
    db_initialized = await db_manager.initialize()
    if not db_initialized:
        print("❌ Database initialization failed")
        sys.exit(1)
    
    try:
        # Run performance tests
        single_op_passed, metrics = await test_single_operation_performance()
        concurrent_passed = await test_concurrent_operations()
        large_dataset_passed = await test_large_dataset_performance()
        
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE TEST SUMMARY")
        print("=" * 60)
        
        # Summary statistics
        for operation in ["create", "read", "update", "list", "delete"]:
            stats = metrics.get_stats(operation)
            if stats.get("count", 0) > 0:
                print(f"{operation.upper():>8}: {stats['mean']*1000:6.2f}ms avg, {stats['max']*1000:6.2f}ms max, {stats['count']:3d} ops")
        
        all_tests_passed = single_op_passed and concurrent_passed and large_dataset_passed
        
        if all_tests_passed:
            print("\n🎉 ALL PERFORMANCE TESTS PASSED!")
            print("✅ Single operations within performance thresholds")
            print("✅ Concurrent operations successful")
            print("✅ Large dataset performance acceptable")
            sys.exit(0)
        else:
            print("\n❌ Some performance tests failed!")
            if not single_op_passed:
                print("❌ Single operation performance issues")
            if not concurrent_passed:
                print("❌ Concurrent operation issues")
            if not large_dataset_passed:
                print("❌ Large dataset performance issues")
            sys.exit(1)
    
    finally:
        await db_manager.shutdown()


if __name__ == "__main__":
    # Set up test environment
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_performance.db")
    os.environ.setdefault("ENABLE_DATABASE", "true")
    
    asyncio.run(main())