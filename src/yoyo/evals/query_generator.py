from __future__ import annotations

import itertools
import uuid
from pathlib import Path

import yaml

from yoyo.evals.schemas import EvalQuery


def load_query_templates(path: str | Path) -> dict:
    input_path = Path(path)
    with input_path.open("r", encoding="utf-8") as file:
        if input_path.suffix == ".json":
            import json

            return {"queries": json.load(file)}
        return yaml.safe_load(file)


def generate_queries(template_data: dict) -> list[EvalQuery]:
    explicit_queries = template_data.get("queries")
    if explicit_queries:
        return [
            EvalQuery(
                id=item.get("id", str(uuid.uuid4())),
                category=item["category"],
                language=item.get("language", "en"),
                prompt=item["prompt"],
                metadata=item.get("metadata", {}),
            )
            for item in explicit_queries
        ]

    categories = template_data["categories"]
    poi_names = template_data.get("poi_names", [])
    phrases = template_data.get("phrases", [])
    languages = template_data.get("languages", ["en"])

    queries: list[EvalQuery] = []
    for category, templates in categories.items():
        for language, template in itertools.product(languages, templates):
            if "{poi_name}" in template:
                for poi_name in poi_names:
                    queries.append(
                        EvalQuery(
                            id=str(uuid.uuid4()),
                            category=category,
                            language=language,
                            prompt=template.format(poi_name=poi_name),
                            metadata={"poi_name": poi_name},
                        )
                    )
            elif "{phrase}" in template:
                for phrase in phrases:
                    queries.append(
                        EvalQuery(
                            id=str(uuid.uuid4()),
                            category=category,
                            language=language,
                            prompt=template.format(phrase=phrase),
                            metadata={"phrase": phrase},
                        )
                    )
            else:
                queries.append(
                    EvalQuery(
                        id=str(uuid.uuid4()),
                        category=category,
                        language=language,
                        prompt=template,
                        metadata={},
                    )
                )

    return queries
