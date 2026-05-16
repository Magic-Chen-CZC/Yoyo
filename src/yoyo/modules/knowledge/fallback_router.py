from __future__ import annotations

from yoyo.modules.knowledge.schemas import AttractionContext


DEEP_RAG_ATTRACTION_TOKENS = {
    "axis",
    "axial",
    "architecture",
    "cosmology",
    "curation",
    "deeper",
    "not just architecture",
    "political theater",
    "ritual",
    "spatial order",
    "symbol",
    "symbolic",
    "symbolism",
    "urban order",
    "中轴线",
    "仪式",
    "建筑",
    "建筑秩序",
    "政治表达",
    "空间秩序",
    "策展",
    "象征",
    "象征意义",
}

DEEP_MODIFIERS = {
    "deeper",
    "deep",
    "unpack",
    "深入",
    "深层",
    "展开",
    "拆解",
}


def should_use_rag_fallback(
    *,
    intent: str,
    query: str,
    attraction: AttractionContext | None,
) -> bool:
    if intent != "attraction_explain":
        return False
    if attraction is None:
        return False
    lowered = query.lower()
    if any(token in lowered for token in DEEP_RAG_ATTRACTION_TOKENS):
        return True
    if any(token in lowered for token in DEEP_MODIFIERS) and any(
        token in lowered for token in ("history", "background", "meaning", "历史", "背景", "意义")
    ):
        return True
    return False
