"""Timing utilities for Agent RAG."""

import functools
import time
from typing import Any, Callable, Optional, TypeVar

from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class Timer:
    """Context manager for timing code blocks."""

    def __init__(self, name: Optional[str] = None, log: bool = True) -> None:
        self.name = name
        self.log = log
        self.start_time: float = 0
        self.end_time: float = 0
        self.elapsed: float = 0

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        if self.log:
            name = self.name or "Block"
            logger.debug(f"{name} took {self.elapsed:.3f}s")


def timed(
    name: Optional[str] = None,
    log: bool = True,
    log_args: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to time function execution.

    Args:
        name: Optional name for the timer (defaults to function name)
        log: Whether to log the timing
        log_args: Whether to log function arguments

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            timer_name = name or func.__name__

            if log_args:
                args_str = ", ".join(
                    [repr(a) for a in args] +
                    [f"{k}={v!r}" for k, v in kwargs.items()]
                )
                logger.debug(f"Starting {timer_name}({args_str})")

            with Timer(timer_name, log=log) as timer:
                result = func(*args, **kwargs)

            return result

        return wrapper  # type: ignore

    return decorator


class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""

    def __init__(
        self,
        rate: float,
        capacity: float,
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            rate: Tokens per second
            capacity: Maximum tokens (burst capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()

    def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire tokens, blocking if necessary.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Time waited in seconds
        """
        waited = 0.0

        while True:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return waited

            # Calculate wait time
            wait_time = (tokens - self.tokens) / self.rate
            time.sleep(wait_time)
            waited += wait_time

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False
