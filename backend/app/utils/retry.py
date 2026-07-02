"""Generic async retry decorator with exponential backoff."""

import asyncio
import functools
from typing import Callable, Tuple, Type


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    multiplier: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator that retries an async function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default 3).
        base_delay: Initial delay in seconds (default 1.0).
        max_delay: Maximum delay cap in seconds (default 10.0).
        multiplier: Backoff multiplier (default 2.0).
        retryable_exceptions: Tuple of exception types that trigger retries.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (multiplier**attempt), max_delay)
                        await asyncio.sleep(delay)
            raise last_exception

        return wrapper

    return decorator
