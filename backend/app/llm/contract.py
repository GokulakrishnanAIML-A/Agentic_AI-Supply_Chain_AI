from __future__ import annotations

import time
from typing import Any, Callable, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class LLMMetric(BaseModel):
    node: str
    used_llm: bool
    latency_ms: float
    fallback_reason: str | None = None


class LLMResult(BaseModel, Generic[T]):
    value: T
    used_llm: bool
    latency_ms: float
    fallback_reason: str | None = None


def call_structured(
    schema: type[T],
    system: str,
    user: str,
    fallback: Callable[[], T],
    *,
    timeout_s: float = 8.0,
    retries: int = 1,
) -> LLMResult[T]:
    """Uniform structured LLM invocation with strict schema validation, latency measurement,
    and guaranteed deterministic fallback.
    """
    from app.core.config import settings
    from app.llm.factory import get_llm

    start_time = time.perf_counter()
    provider = settings.effective_llm_provider

    if provider == "mock" or not settings.resolved_gemini_key:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        val = fallback()
        return LLMResult(
            value=val,
            used_llm=False,
            latency_ms=round(elapsed, 2),
            fallback_reason="mock_provider_active",
        )

    llm = get_llm()
    last_err: str | None = None

    for attempt in range(retries + 1):
        try:
            raw_dict = llm.complete_json(system, user)
            if hasattr(schema, "model_validate"):
                validated = schema.model_validate(raw_dict)
            elif isinstance(raw_dict, dict):
                validated = schema(**raw_dict)
            else:
                validated = schema(raw_dict)
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return LLMResult(
                value=validated,
                used_llm=True,
                latency_ms=round(elapsed, 2),
                fallback_reason=None,
            )
        except Exception as exc:
            last_err = str(exc)

    elapsed = (time.perf_counter() - start_time) * 1000.0
    val = fallback()
    return LLMResult(
        value=val,
        used_llm=False,
        latency_ms=round(elapsed, 2),
        fallback_reason=f"error: {last_err}",
    )
