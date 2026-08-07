from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable

from backend.core.config import settings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


@lru_cache(maxsize=1)
def get_openai_client():
    if not settings.openai_api_key or OpenAI is None:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def call_with_timeout(function: Callable[[], Any], timeout_seconds: float = 12.0) -> Any | None:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(function)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        return None
    except Exception:
        return None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
