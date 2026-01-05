"""
Performance Optimization Utilities
"""

import time
import functools
import logging
from typing import Callable, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


def cache_result(ttl: int = 300):
    """Cache function result with TTL"""
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_times = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = str(args) + str(kwargs)
            current_time = time.time()
            
            # Check if cached and not expired
            if cache_key in cache:
                if current_time - cache_times[cache_key] < ttl:
                    return cache[cache_key]
            
            # Execute and cache
            result = func(*args, **kwargs)
            cache[cache_key] = result
            cache_times[cache_key] = current_time
            
            return result
        
        return wrapper
    return decorator


def measure_time(func: Callable) -> Callable:
    """Measure function execution time"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(f"{func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper


class PerformanceMonitor:
    """Monitor system performance"""
    
    def __init__(self):
        self.metrics = {}
    
    def record_metric(self, name: str, value: float):
        """Record performance metric"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
    
    def get_average(self, name: str) -> float:
        """Get average metric value"""
        if name not in self.metrics or not self.metrics[name]:
            return 0.0
        return sum(self.metrics[name]) / len(self.metrics[name])

