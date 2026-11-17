import asyncio
import functools
import logging
import random
from typing import Any, Callable, Tuple, Type

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 0.5,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator for asynchronous functions implementing Exponential Backoff with Full Jitter.
    Retries transient failures gracefully before raising an exception.
    """
    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as exc:
                    attempt += 1
                    if attempt > max_retries:
                        logger.error(
                            f"Function '{func.__name__}' failed after {max_retries} retries. Raising: {exc}"
                        )
                        raise

                    delay = base_delay * (backoff_factor ** (attempt - 1))
                    if jitter:
                        delay = random.uniform(0, delay)

                    logger.warning(
                        f"Attempt {attempt}/{max_retries} for '{func.__name__}' failed with {exc.__class__.__name__}: {exc}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)

        return wrapper

    return decorator
