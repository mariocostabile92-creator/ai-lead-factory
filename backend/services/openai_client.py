from functools import lru_cache

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
