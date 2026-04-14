# retrieval.py 负责读取景点知识。
# 当前阶段采用 SQL-first 思路：优先消费已构建好的 attraction context，必要时回退到旧 POI catalog 兼容结构。
from yoyo.modules.knowledge.schemas import AttractionContext
from yoyo.modules.poi.catalog import POI_CATALOG


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
    }
