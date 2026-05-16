from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from yoyo.modules.knowledge.prompt_projection import project_attraction_for_prompt, project_profile_for_prompt
from yoyo.modules.knowledge.schemas import AttractionContext, HybridContext, ProfileContext


class QAPlaygroundConfig(BaseModel):
    session_override: dict[str, Any] = Field(default_factory=dict)
    profile_override: dict[str, Any] = Field(default_factory=dict)
    attraction_override: dict[str, Any] = Field(default_factory=dict)
    dialogue_history: list[dict[str, Any]] | None = None


class QAPlaygroundAppliedState(BaseModel):
    enabled: bool = False
    session_override_applied: bool = False
    profile_override_applied: bool = False
    attraction_override_applied: bool = False
    dialogue_history_override_applied: bool = False


def parse_playground_config(request_context: dict[str, Any]) -> QAPlaygroundConfig:
    raw = request_context.get("qa_playground")
    if not isinstance(raw, dict):
        return QAPlaygroundConfig()
    try:
        return QAPlaygroundConfig.model_validate(raw)
    except ValidationError:
        return QAPlaygroundConfig()


def merge_session_context_with_playground(
    session_context: dict[str, Any],
    request_context: dict[str, Any],
) -> tuple[dict[str, Any], QAPlaygroundAppliedState]:
    config = parse_playground_config(request_context)
    applied = QAPlaygroundAppliedState(enabled=_has_any_override(config))
    if not config.session_override:
        return session_context, applied
    merged = {**session_context, **config.session_override}
    applied.session_override_applied = True
    return merged, applied


def resolve_dialogue_history_for_playground(
    dialogue_history: list[dict[str, Any]],
    request_context: dict[str, Any],
    applied: QAPlaygroundAppliedState | None = None,
) -> list[dict[str, Any]]:
    config = parse_playground_config(request_context)
    if config.dialogue_history is None:
        return dialogue_history
    sanitized: list[dict[str, Any]] = []
    for item in config.dialogue_history:
        role = str(item.get("role") or "user").strip() or "user"
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        sanitized.append({"role": role, "content": content})
    if applied is not None:
        applied.dialogue_history_override_applied = True
    return sanitized


def apply_hybrid_context_playground_overrides(
    hybrid_context: HybridContext,
    request_context: dict[str, Any],
    *,
    session_context: dict[str, Any],
    dialogue_history: list[dict[str, Any]],
    fallback_user_id: str | None = None,
    applied: QAPlaygroundAppliedState | None = None,
) -> HybridContext:
    config = parse_playground_config(request_context)
    updated = _update_hybrid_context(
        hybrid_context,
        {
            "session_context": session_context,
            "dialogue_history": dialogue_history,
        },
    )

    if config.profile_override:
        base_profile = updated.profile.model_dump() if updated.profile is not None else {}
        base_profile.setdefault("user_id", fallback_user_id or "playground-user")
        merged_profile = {
            **base_profile,
            **config.profile_override,
            "source": "playground_override",
        }
        profile = ProfileContext.model_validate(merged_profile)
        updated = _update_hybrid_context(
            updated,
            {
                "profile": profile,
                "prompt_safe_profile": project_profile_for_prompt(profile),
            },
        )
        if applied is not None:
            applied.profile_override_applied = True

    if config.attraction_override:
        base_attraction = updated.attraction.model_dump() if updated.attraction is not None else {}
        base_attraction.setdefault("id", "playground-attraction")
        base_attraction.setdefault("name", str(config.attraction_override.get("name") or "Playground Attraction"))
        base_attraction.setdefault("category", str(config.attraction_override.get("category") or "landmark"))
        merged_attraction = {
            **base_attraction,
            **config.attraction_override,
            "source": "playground_override",
        }
        attraction = AttractionContext.model_validate(merged_attraction)
        updated = _update_hybrid_context(
            updated,
            {
                "attraction": attraction,
                "prompt_safe_attraction": project_attraction_for_prompt(attraction),
            },
        )
        if applied is not None:
            applied.attraction_override_applied = True

    return updated


def _has_any_override(config: QAPlaygroundConfig) -> bool:
    return bool(
        config.session_override
        or config.profile_override
        or config.attraction_override
        or config.dialogue_history is not None
    )



def _update_hybrid_context(hybrid_context: HybridContext, update: dict[str, Any]) -> HybridContext:
    if hasattr(hybrid_context, "model_copy"):
        return hybrid_context.model_copy(update=update)
    for key, value in update.items():
        setattr(hybrid_context, key, value)
    return hybrid_context
