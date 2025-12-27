"""Concurrency utilities for Agent RAG."""

import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable, TypeVar, Optional
import threading

T = TypeVar("T")


def run_in_parallel(
    functions_with_args: list[tuple[Callable[..., T], tuple[Any, ...]]],
    max_workers: Optional[int] = None,
    timeout: Optional[float] = None,
    allow_failures: bool = False,
) -> list[T | None]:
    """
    Run multiple functions in parallel using a thread pool.

    Args:
        functions_with_args: List of (function, args) tuples to execute
        max_workers: Maximum number of worker threads
        timeout: Timeout in seconds for each function
        allow_failures: If True, return None for failed functions instead of raising

    Returns:
        List of results in the same order as input functions
    """
    if not functions_with_args:
        return []

    if max_workers is None:
        max_workers = min(len(functions_with_args), 10)

    results: list[T | None] = [None] * len(functions_with_args)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index: dict[concurrent.futures.Future[T], int] = {}

        for i, (func, args) in enumerate(functions_with_args):
            future = executor.submit(func, *args)
            future_to_index[future] = i

        for future in concurrent.futures.as_completed(
            future_to_index.keys(),
            timeout=timeout,
        ):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as e:
                if allow_failures:
                    results[index] = None
                else:
                    raise e

    return results


def run_with_timeout(
    func: Callable[..., T],
    args: tuple[Any, ...] = (),
    kwargs: Optional[dict[str, Any]] = None,
    timeout: float = 30.0,
    default: Optional[T] = None,
) -> T | None:
    """
    Run a function with a timeout.

    Args:
        func: Function to execute
        args: Positional arguments
        kwargs: Keyword arguments
        timeout: Timeout in seconds
        default: Default value to return on timeout

    Returns:
        Function result or default on timeout
    """
    kwargs = kwargs or {}
    result: list[T | None] = [default]
    exception: list[Exception | None] = [None]

    def target() -> None:
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Thread is still running, return default
        return default

    if exception[0] is not None:
        raise exception[0]

    return result[0]


class BackgroundTask:
    """A task that runs in the background."""

    def __init__(
        self,
        func: Callable[..., T],
        args: tuple[Any, ...] = (),
        kwargs: Optional[dict[str, Any]] = None,
    ) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self._result: T | None = None
        self._exception: Exception | None = None
        self._done = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "BackgroundTask":
        """Start the background task."""
        def target() -> None:
            try:
                self._result = self.func(*self.args, **self.kwargs)
            except Exception as e:
                self._exception = e
            finally:
                self._done.set()

        self._thread = threading.Thread(target=target)
        self._thread.daemon = True
        self._thread.start()
        return self

    def wait(self, timeout: Optional[float] = None) -> T | None:
        """Wait for the task to complete and return the result."""
        self._done.wait(timeout=timeout)

        if self._exception is not None:
            raise self._exception

        return self._result

    @property
    def is_done(self) -> bool:
        """Check if the task is done."""
        return self._done.is_set()

    @property
    def result(self) -> T | None:
        """Get the result (raises if not done or failed)."""
        if not self.is_done:
            raise RuntimeError("Task is not done yet")
        if self._exception is not None:
            raise self._exception
        return self._result
