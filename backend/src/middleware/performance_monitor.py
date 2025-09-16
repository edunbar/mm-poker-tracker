"""Performance monitoring middleware for analytics endpoints."""

import time
import logging
from functools import wraps
from typing import Callable, Any

# Performance metrics storage
_performance_metrics = {
    'analytics_query_times': [],
    'summary_query_times': [],
    'cache_hit_rates': {
        'analytics': {'hits': 0, 'misses': 0},
        'summaries': {'hits': 0, 'misses': 0}
    }
}

def monitor_performance(query_type: str):
    """Decorator to monitor query performance."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Store execution time
            if query_type in _performance_metrics:
                _performance_metrics[f'{query_type}_query_times'].append(execution_time)
                # Keep only last 100 measurements
                if len(_performance_metrics[f'{query_type}_query_times']) > 100:
                    _performance_metrics[f'{query_type}_query_times'].pop(0)

            # Log slow queries
            if execution_time > 1.0:  # Log queries taking more than 1 second
                logging.warning(f"Slow {query_type} query: {execution_time:.3f}s")
            else:
                logging.debug(f"{query_type} query completed in {execution_time:.3f}s")

            return result
        return wrapper
    return decorator

def record_cache_hit(cache_type: str):
    """Record a cache hit."""
    if cache_type in _performance_metrics['cache_hit_rates']:
        _performance_metrics['cache_hit_rates'][cache_type]['hits'] += 1

def record_cache_miss(cache_type: str):
    """Record a cache miss."""
    if cache_type in _performance_metrics['cache_hit_rates']:
        _performance_metrics['cache_hit_rates'][cache_type]['misses'] += 1

def get_performance_stats() -> dict:
    """Get current performance statistics."""
    stats = {}

    # Calculate average query times
    for query_type in ['analytics', 'summary']:
        times = _performance_metrics.get(f'{query_type}_query_times', [])
        if times:
            stats[f'{query_type}_avg_time'] = sum(times) / len(times)
            stats[f'{query_type}_max_time'] = max(times)
            stats[f'{query_type}_min_time'] = min(times)
            stats[f'{query_type}_sample_count'] = len(times)
        else:
            stats[f'{query_type}_avg_time'] = 0
            stats[f'{query_type}_max_time'] = 0
            stats[f'{query_type}_min_time'] = 0
            stats[f'{query_type}_sample_count'] = 0

    # Calculate cache hit rates
    for cache_type, metrics in _performance_metrics['cache_hit_rates'].items():
        total = metrics['hits'] + metrics['misses']
        if total > 0:
            hit_rate = metrics['hits'] / total * 100
            stats[f'{cache_type}_cache_hit_rate'] = f"{hit_rate:.1f}%"
            stats[f'{cache_type}_cache_total_requests'] = total
        else:
            stats[f'{cache_type}_cache_hit_rate'] = "N/A"
            stats[f'{cache_type}_cache_total_requests'] = 0

    return stats

def reset_performance_stats():
    """Reset all performance statistics."""
    global _performance_metrics
    _performance_metrics = {
        'analytics_query_times': [],
        'summary_query_times': [],
        'cache_hit_rates': {
            'analytics': {'hits': 0, 'misses': 0},
            'summaries': {'hits': 0, 'misses': 0}
        }
    }
    logging.info("Performance statistics reset")