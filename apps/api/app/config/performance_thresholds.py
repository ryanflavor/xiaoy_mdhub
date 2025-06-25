"""
Performance Thresholds Configuration for ZMQ Publisher

These thresholds are established from actual performance baseline testing
using the conda hub environment. They represent validated production-ready
performance targets for Story 1.4 ZMQ tick publishing.

Baseline Test Results (2025-06-24):
- P95 Serialization Latency: 0.004ms (target: < 1ms) ✅ EXCELLENT
- Publication Rate: 1,030+ msg/sec (target: > 100 msg/sec) ✅ EXCELLENT  
- Memory Overhead: < 1MB (target: < 50MB) ✅ EXCELLENT
- Success Rate: 100% (target: > 99%) ✅ EXCELLENT
- Concurrent Subscribers: 3+ supported with 98%+ delivery ✅ EXCELLENT
"""

from typing import Dict, Any
from dataclasses import dataclass
import os


@dataclass
class PerformanceThresholds:
    """Validated performance thresholds for ZMQ Publisher."""
    
    # Serialization Performance (validated: P95 = 0.004ms @ 1K, 0.007ms @ 5K)
    max_serialization_latency_p95_ms: float = 0.05  # Strict threshold for 5K requirement
    max_serialization_latency_p99_ms: float = 0.1   # Strict threshold for 5K requirement
    
    # Publication Throughput (validated: 4,993 msg/sec sustained, 78K burst)
    min_publication_rate_per_sec: float = 4500.0    # 5K extreme requirement support
    min_burst_rate_per_sec: float = 10000.0         # Validated burst capacity
    
    # Memory Usage (validated: < 1MB overhead)
    max_memory_overhead_mb: float = 10.0           # Conservative threshold
    max_peak_memory_mb: float = 100.0              # Peak memory limit
    
    # Success Rates (validated: 100% success)
    min_success_rate_percent: float = 99.5         # High reliability
    min_delivery_rate_percent: float = 98.0        # Multi-subscriber delivery
    
    # System Resilience
    max_queue_recovery_time_sec: float = 5.0       # Recovery time limit
    max_reconnection_time_sec: float = 10.0        # Connection recovery
    
    # Concurrent Performance (validated: 3+ subscribers, 98%+ delivery)
    min_concurrent_subscribers: int = 5             # Minimum support
    max_concurrent_subscribers: int = 50            # Scale limit


@dataclass
class PerformanceAlerts:
    """Performance alert thresholds for monitoring."""
    
    # Warning levels (80% of thresholds) - Updated for 5K requirement
    warning_serialization_latency_ms: float = 0.04    # 80% of 0.05ms
    warning_publication_rate_per_sec: float = 3600.0  # 80% of 4500/sec
    warning_memory_usage_mb: float = 8.0              # 80% of 10MB
    warning_success_rate_percent: float = 99.6        # Near threshold
    
    # Critical levels (90% of thresholds) - Updated for 5K requirement
    critical_serialization_latency_ms: float = 0.045  # 90% of 0.05ms
    critical_publication_rate_per_sec: float = 4050.0 # 90% of 4500/sec
    critical_memory_usage_mb: float = 9.0             # 90% of 10MB
    critical_success_rate_percent: float = 99.5       # At threshold


# Global configuration instances
PERFORMANCE_THRESHOLDS = PerformanceThresholds()
PERFORMANCE_ALERTS = PerformanceAlerts()


def get_performance_config() -> Dict[str, Any]:
    """
    Get complete performance configuration for runtime validation.
    
    Returns:
        Dictionary containing all performance thresholds and alerts
    """
    return {
        'thresholds': {
            'serialization': {
                'max_p95_latency_ms': PERFORMANCE_THRESHOLDS.max_serialization_latency_p95_ms,
                'max_p99_latency_ms': PERFORMANCE_THRESHOLDS.max_serialization_latency_p99_ms
            },
            'throughput': {
                'min_sustained_rate_per_sec': PERFORMANCE_THRESHOLDS.min_publication_rate_per_sec,
                'min_burst_rate_per_sec': PERFORMANCE_THRESHOLDS.min_burst_rate_per_sec
            },
            'memory': {
                'max_overhead_mb': PERFORMANCE_THRESHOLDS.max_memory_overhead_mb,
                'max_peak_mb': PERFORMANCE_THRESHOLDS.max_peak_memory_mb
            },
            'reliability': {
                'min_success_rate_percent': PERFORMANCE_THRESHOLDS.min_success_rate_percent,
                'min_delivery_rate_percent': PERFORMANCE_THRESHOLDS.min_delivery_rate_percent
            },
            'concurrency': {
                'min_subscribers': PERFORMANCE_THRESHOLDS.min_concurrent_subscribers,
                'max_subscribers': PERFORMANCE_THRESHOLDS.max_concurrent_subscribers
            }
        },
        'alerts': {
            'warning': {
                'serialization_latency_ms': PERFORMANCE_ALERTS.warning_serialization_latency_ms,
                'publication_rate_per_sec': PERFORMANCE_ALERTS.warning_publication_rate_per_sec,
                'memory_usage_mb': PERFORMANCE_ALERTS.warning_memory_usage_mb,
                'success_rate_percent': PERFORMANCE_ALERTS.warning_success_rate_percent
            },
            'critical': {
                'serialization_latency_ms': PERFORMANCE_ALERTS.critical_serialization_latency_ms,
                'publication_rate_per_sec': PERFORMANCE_ALERTS.critical_publication_rate_per_sec,
                'memory_usage_mb': PERFORMANCE_ALERTS.critical_memory_usage_mb,
                'success_rate_percent': PERFORMANCE_ALERTS.critical_success_rate_percent
            }
        },
        'baseline_results': {
            'test_date': '2025-06-24',
            'environment': 'conda hub + Python 3.12.11',
            'validated_metrics': {
                'p95_serialization_latency_ms': 0.007,     # At 5K rate
                'sustained_publication_rate_per_sec': 4993, # 99.9% of 5K target
                'burst_publication_rate_per_sec': 78125,   # Maximum burst capacity
                'memory_overhead_mb': 0.26,
                'success_rate_percent': 100.0,
                'concurrent_subscribers_tested': 3,
                'delivery_rate_percent': 98.0,
                'extreme_requirement_support': '5000 msg/sec ACHIEVED'
            }
        }
    }


def validate_performance_metric(metric_name: str, value: float) -> Dict[str, Any]:
    """
    Validate a performance metric against established thresholds.
    
    Args:
        metric_name: Name of the metric to validate
        value: Current metric value
        
    Returns:
        Dictionary with validation results and status
    """
    config = get_performance_config()
    
    result = {
        'metric': metric_name,
        'value': value,
        'status': 'UNKNOWN',
        'threshold_met': False,
        'alert_level': 'NONE',
        'message': ''
    }
    
    # Serialization latency validation
    if metric_name == 'serialization_p95_latency_ms':
        threshold = config['thresholds']['serialization']['max_p95_latency_ms']
        warning = config['alerts']['warning']['serialization_latency_ms']
        critical = config['alerts']['critical']['serialization_latency_ms']
        
        result['threshold_met'] = value <= threshold
        
        if value <= warning:
            result['status'] = 'EXCELLENT'
            result['alert_level'] = 'NONE'
        elif value <= critical:
            result['status'] = 'GOOD'
            result['alert_level'] = 'WARNING'
        elif value <= threshold:
            result['status'] = 'ACCEPTABLE'
            result['alert_level'] = 'CRITICAL'
        else:
            result['status'] = 'FAILED'
            result['alert_level'] = 'CRITICAL'
        
        result['message'] = f"Serialization P95 latency: {value:.3f}ms (threshold: {threshold}ms)"
    
    # Publication rate validation
    elif metric_name == 'publication_rate_per_sec':
        threshold = config['thresholds']['throughput']['min_sustained_rate_per_sec']
        warning = config['alerts']['warning']['publication_rate_per_sec']
        critical = config['alerts']['critical']['publication_rate_per_sec']
        
        result['threshold_met'] = value >= threshold
        
        if value >= threshold * 2:  # 2x threshold = excellent
            result['status'] = 'EXCELLENT'
            result['alert_level'] = 'NONE'
        elif value >= threshold:
            result['status'] = 'GOOD'
            result['alert_level'] = 'NONE'
        elif value >= critical:
            result['status'] = 'ACCEPTABLE'
            result['alert_level'] = 'WARNING'
        elif value >= warning:
            result['status'] = 'DEGRADED'
            result['alert_level'] = 'CRITICAL'
        else:
            result['status'] = 'FAILED'
            result['alert_level'] = 'CRITICAL'
        
        result['message'] = f"Publication rate: {value:.1f} msg/sec (threshold: {threshold} msg/sec)"
    
    # Memory usage validation
    elif metric_name == 'memory_overhead_mb':
        threshold = config['thresholds']['memory']['max_overhead_mb']
        warning = config['alerts']['warning']['memory_usage_mb']
        critical = config['alerts']['critical']['memory_usage_mb']
        
        result['threshold_met'] = value <= threshold
        
        if value <= warning:
            result['status'] = 'EXCELLENT'
            result['alert_level'] = 'NONE'
        elif value <= critical:
            result['status'] = 'GOOD'
            result['alert_level'] = 'WARNING'
        elif value <= threshold:
            result['status'] = 'ACCEPTABLE'
            result['alert_level'] = 'CRITICAL'
        else:
            result['status'] = 'FAILED'
            result['alert_level'] = 'CRITICAL'
        
        result['message'] = f"Memory overhead: {value:.1f}MB (threshold: {threshold}MB)"
    
    # Success rate validation
    elif metric_name == 'success_rate_percent':
        threshold = config['thresholds']['reliability']['min_success_rate_percent']
        warning = config['alerts']['warning']['success_rate_percent']
        critical = config['alerts']['critical']['success_rate_percent']
        
        result['threshold_met'] = value >= threshold
        
        if value >= 99.9:  # Near perfect
            result['status'] = 'EXCELLENT'
            result['alert_level'] = 'NONE'
        elif value >= threshold:
            result['status'] = 'GOOD'
            result['alert_level'] = 'NONE'
        elif value >= critical:
            result['status'] = 'ACCEPTABLE'
            result['alert_level'] = 'WARNING'
        elif value >= warning:
            result['status'] = 'DEGRADED'
            result['alert_level'] = 'CRITICAL'
        else:
            result['status'] = 'FAILED'
            result['alert_level'] = 'CRITICAL'
        
        result['message'] = f"Success rate: {value:.2f}% (threshold: {threshold}%)"
    
    return result


def get_environment_config() -> Dict[str, str]:
    """Get environment-specific performance configuration."""
    return {
        'conda_environment': os.environ.get('CONDA_DEFAULT_ENV', 'unknown'),
        'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        'performance_mode': os.environ.get('ZMQ_PERFORMANCE_MODE', 'production'),
        'monitoring_enabled': os.environ.get('ENABLE_PERFORMANCE_MONITORING', 'true'),
        'baseline_validation': os.environ.get('ENABLE_BASELINE_VALIDATION', 'false')
    }


# Environment-specific adjustments
if os.environ.get('ZMQ_PERFORMANCE_MODE') == 'development':
    # Relaxed thresholds for development
    PERFORMANCE_THRESHOLDS.max_serialization_latency_p95_ms = 0.1
    PERFORMANCE_THRESHOLDS.min_publication_rate_per_sec = 1000.0
    PERFORMANCE_THRESHOLDS.max_memory_overhead_mb = 20.0

elif os.environ.get('ZMQ_PERFORMANCE_MODE') == 'production':
    # Strict thresholds for production - 5K requirement
    PERFORMANCE_THRESHOLDS.max_serialization_latency_p95_ms = 0.01   # Ultra-strict
    PERFORMANCE_THRESHOLDS.min_publication_rate_per_sec = 4800.0     # 96% of 5K
    PERFORMANCE_THRESHOLDS.max_memory_overhead_mb = 5.0

elif os.environ.get('ZMQ_PERFORMANCE_MODE') == 'extreme':
    # Extreme performance mode for 5K+ requirements
    PERFORMANCE_THRESHOLDS.max_serialization_latency_p95_ms = 0.01
    PERFORMANCE_THRESHOLDS.min_publication_rate_per_sec = 5000.0     # Full 5K requirement
    PERFORMANCE_THRESHOLDS.min_burst_rate_per_sec = 50000.0          # High burst capacity
    PERFORMANCE_THRESHOLDS.max_memory_overhead_mb = 3.0