from __future__ import annotations

from typing import Any

from yoyo.db.models.attraction import Attraction
from yoyo.modules.knowledge.schemas import AttractionContext
from yoyo.modules.knowledge.seed_postgres import _BASE_ATTRACTIONS


def build_rag_documents_from_attraction_contexts(
    attractions: list[AttractionContext],
) -> list[dict[str, object]]:
    documents: list[dict[str, object]] = []
    for attraction in attractions:
        chunks = [
            ("history", attraction.history),
            ("practical_notes", " ".join(attraction.practical_notes)),
            ("photo_spot_notes", " ".join(attraction.photo_spot_notes)),
            ("family_notes", " ".join(attraction.family_friendly_notes)),
        ]
        for index, (doc_type, text) in enumerate(chunks, start=1):
            normalized = (text or "").strip()
            if not normalized:
                continue
            documents.append(
                {
                    "id": f"{attraction.id}-{doc_type}-{index}",
                    "text": f"{attraction.name}\n\n{normalized}",
                    "metadata": {
                        "poi_id": attraction.id,
                        "poi_name": attraction.name,
                        "doc_type": doc_type,
                        "source": attraction.source,
                        "language": "en",
                    },
                }
            )
    return documents



def build_rag_documents_from_rows(rows: list[Attraction]) -> list[dict[str, object]]:
    contexts = [
        AttractionContext(
            id=row.id,
            name=row.name,
            aliases=list(row.aliases_json or []),
            category=row.category,
            latitude=row.latitude,
            longitude=row.longitude,
            recommended_duration_minutes=row.recommended_duration_minutes,
            tags=list(row.tags_json or []),
            short_intro=row.short_intro,
            history=row.history,
            highlights=list(row.highlights_json or []),
            visitor_tips=list(row.visitor_tips_json or []),
            practical_notes=list(row.practical_notes_json or []),
            family_friendly_notes=list(row.family_friendly_notes_json or []),
            photo_spot_notes=list(row.photo_spot_notes_json or []),
            source="postgresql",
        )
        for row in rows
    ]
    return build_rag_documents_from_attraction_contexts(contexts)



def build_rag_documents_from_seed() -> list[dict[str, object]]:
    contexts = [
        AttractionContext(
            id=item["id"],
            name=item["name"],
            aliases=list(item["aliases"]),
            category=item["category"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            recommended_duration_minutes=item["recommended_duration_minutes"],
            tags=list(item["tags"]),
            short_intro=item["short_intro"],
            history=item["history"],
            highlights=list(item["highlights"]),
            visitor_tips=list(item["visitor_tips"]),
            practical_notes=list(item["practical_notes"]),
            family_friendly_notes=list(item["family_friendly_notes"]),
            photo_spot_notes=list(item["photo_spot_notes"]),
            source="seed_postgres",
        )
        for item in _BASE_ATTRACTIONS
    ]
    return build_rag_documents_from_attraction_contexts(contexts)
