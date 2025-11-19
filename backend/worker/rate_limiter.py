"""
Token bucket rate limiter for external API calls.
"""
import time
import threading
from typing import Dict


class TokenBucketRateLimiter:
    """
    Thread-safe token bucket rate limiter.
    
    Args:
        rate: Number of requests allowed per second
        burst: Maximum burst size (defaults to rate)
    """
    
    def __init__(self, rate: float, burst: float = None):
        self.rate = rate
        self.burst = burst if burst is not None else rate
        self.tokens = self.burst
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, tokens: int = 1, block: bool = True, timeout: float = None) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            block: Whether to block until tokens are available
            timeout: Maximum time to wait (seconds), None = wait forever
        
        Returns:
            True if tokens acquired, False otherwise
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                now = time.time()
                elapsed = now - self.last_update
                
                # Add tokens based on time elapsed
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            if not block:
                return False
            
            if timeout is not None:
                elapsed_wait = time.time() - start_time
                if elapsed_wait >= timeout:
                    return False
            
            # Sleep briefly before retrying
            time.sleep(0.01)
    
    def wait(self, tokens: int = 1, timeout: float = None):
        """Block until tokens are available (convenience method)."""
        return self.acquire(tokens=tokens, block=True, timeout=timeout)


class RateLimiterRegistry:
    """Registry of rate limiters for different services."""
    
    def __init__(self):
        self.limiters: Dict[str, TokenBucketRateLimiter] = {}
        self.lock = threading.Lock()
    
    def get_limiter(self, service: str, rate: float, burst: float = None) -> TokenBucketRateLimiter:
        """Get or create a rate limiter for a service."""
        with self.lock:
            if service not in self.limiters:
                self.limiters[service] = TokenBucketRateLimiter(rate, burst)
            return self.limiters[service]


# Global registry
_rate_limiter_registry = RateLimiterRegistry()


def get_rate_limiter(service: str, rate: float, burst: float = None) -> TokenBucketRateLimiter:
    """Get a rate limiter for a service."""
    return _rate_limiter_registry.get_limiter(service, rate, burst)

