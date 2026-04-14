from __future__ import annotations

from yoyo.modules.llm.runtime import LLMRuntime


_RUNTIME = LLMRuntime()


def get_llm_runtime() -> LLMRuntime:
    return _RUNTIME
