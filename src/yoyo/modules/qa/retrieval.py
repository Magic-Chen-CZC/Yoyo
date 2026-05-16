# retrieval.py 负责读取景点知识。
# 当前阶段采用 SQL-first 思路：优先消费已构建好的 attraction context，必要时回退到旧 POI catalog 兼容结构。
from yoyo.modules.knowledge.schemas import AttractionContext
from yoyo.modules.poi.catalog import POI_CATALOG


SQL_PRIMARY_FIELDS: tuple[str, ...] = (
    "summary",
    "history",
    "tips",
    "highlights",
    "practical_notes",
    "family_friendly_notes",
    "photo_spot_notes",
)

RAG_SUPPORT_FIELDS: tuple[str, ...] = (
    "history_background",
    "symbolism",
    "architecture",
    "city_axis_context",
    "deeper_cultural_context",
)



def get_attraction_explanation(
    current_stop_name: str | None,
    attraction: AttractionContext | None = None,
) -> dict[str, object] | None:
    if attraction is not None:
        return {
            "id": attraction.id,
            "name": attraction.name,
            "aliases": attraction.aliases,
            "category": attraction.category,
            "summary": attraction.short_intro,
            "history": attraction.history,
            "tips": attraction.visitor_tips,
            "highlights": attraction.highlights,
            "source_type": attraction.source,
            "evidence": {
                "short_intro": attraction.short_intro,
                "history": attraction.history,
                "practical_notes": attraction.practical_notes,
            },
            "sql_primary_fields": list(SQL_PRIMARY_FIELDS),
            "rag_support_fields": list(RAG_SUPPORT_FIELDS),
        }

    if current_stop_name is None:
        return None

    poi = POI_CATALOG.get(current_stop_name)
    if poi is None:
        return None

    return {
        "name": poi["name"],
        "summary": poi["short_intro"],
        "history": poi["history"],
        "tips": poi["tips"],
        "sql_primary_fields": list(SQL_PRIMARY_FIELDS),
        "rag_support_fields": list(RAG_SUPPORT_FIELDS),
    }
