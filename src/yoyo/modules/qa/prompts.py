from __future__ import annotations

from yoyo.modules.knowledge.prompt_projection import describe_guide_style
from yoyo.modules.knowledge.schemas import HybridContext
from yoyo.modules.llm.schemas import GenerationOptions, LLMRequest, PromptMessage


PROMPT_VERSION = "qa-zh-v4"


def build_qa_generation_request(
    *,
    provider: str,
    model: str,
    intent: str,
    query: str,
    language: str,
    hybrid_context: HybridContext,
) -> LLMRequest:
    system_prompt = _build_system_prompt(intent, language)
    user_prompt = _build_user_prompt(intent, query, hybrid_context, language)
    return LLMRequest(
        provider=provider,
        model=model,
        messages=[
            PromptMessage(role="system", content=system_prompt),
            PromptMessage(role="user", content=user_prompt),
        ],
        options=GenerationOptions(max_tokens=700, temperature=0.35, timeout_seconds=35.0),
        metadata={"prompt_version": f"{PROMPT_VERSION}-{intent}"},
    )


def _build_system_prompt(intent: str, language: str) -> str:
    base = (
        "你是北京旅游问答助手。"
        "优先根据提供的上下文回答，不要补造实时事实。"
        "支持能力：景点讲解、行程建议、旅行翻译、官方 live info、天气、文字导航。"
        "不支持：编程、通用百科、法律、医疗、金融、拥挤度、人流量、排队热度、泛交通拥堵，以及没有依据的其他实时事实。"
        "grounding 规则：SQL 优先用于景点简介、稳定事实、实用提醒、路线/会话状态；"
        "RAG 只用于补充 SQL 未直接覆盖的深层历史、象征、建筑、中轴线等背景信息；如 SQL 与 RAG 冲突，优先 SQL。"
        "如果 attraction_explain 没有 SQL/RAG 上下文，但 query 明确是北京景点问题，可以使用模型通用知识回答，并把 grounding 标为 model_knowledge。"
        "如果上下文不够，就明确说明，不要硬补。"
        f"answer 字段面向用户使用 {language}。"
        "回答默认控制在 300 字以内；能用更短的话清楚回答时，优先短答。"
        "只有在历史背景、文化解释、深度知识类问题上，才可以适当写长一点。"
        "如果 answer 较长，必须分成 2 到 3 段，结构清楚，便于直接阅读；不要输出项目符号、markdown 标题或代码块。"
        "不要输出思考过程。"
        "只输出一个 JSON 对象，不要 markdown，不要额外文本。"
    )
    if intent == "translation":
        return base + (
            "translation 只处理旅行场景下的短句翻译、双语展示或简短改写。"
            "句子清楚就直接翻；不完整或歧义明显时再澄清。"
            "返回字段：answer, status, reason, mode。"
            "status 只能是 ok, clarification, degraded。"
            "mode 只能是 direct_translation, needs_phrase, degraded。"
        )
    if intent == "live_info":
        return base + (
            "live_info 只用于同日或近时段的官方运营信息，例如开放时间、预约、检票、临时关闭、官方公告。"
            "不要把景点介绍、天气、交通、拥挤度或一般游玩建议答成 live_info。"
            "信息不完整时要降低确定性，不要过度肯定。"
            "返回字段：answer, status, reason, not_confirmed, confidence。"
            "status 只能是 ok, degraded, unavailable。"
            "confidence 只能是 low, medium, high。"
        )
    if intent == "weather_info":
        return base + (
            "weather_info 只用于天气、降雨、温度、风力、湿度、天气预报这类问题。"
            "优先使用 weather 上下文中的已给定观测结果，不要编造未提供的天气事实。"
            "如果天气上下文缺失或不可用，要明确说明不确定。"
            "返回字段：answer, status, reason。"
            "status 只能是 ok, degraded, unavailable。"
        )
    if intent == "trip_assistant":
        return base + (
            "trip_assistant 用于当前路线推进、下一站建议、节奏建议、轻量安抚和旅行相邻的短对话支持。"
            "有 session context 时要优先引用 current_stop、next_stop、remaining route；没有就不要编造路线状态。"
            "如果用户要改路线、删点、换点、重排，只能给 redirect 语义，不能假装已执行。"
            "返回字段：answer, status, reason, route_focus, references_current_stop, references_next_stop。"
            "status 只能是 ok, degraded, clarification, redirect。"
            "route_focus 只能是 current_stop, next_stop, route_overview, manual_edit_redirect, general_guidance。"
            "reason 在正常回答时必须写 null。"
            "references_current_stop 和 references_next_stop 必须显式写 true 或 false，不要省略，不要写成字符串。"
            "answer 只能是给用户看的纯文本，不要写 Answer:、不要写字段解释、不要加 markdown 代码块。"
            "示例：{\"answer\":\"你现在在天安门广场，下一站是故宫。\",\"status\":\"ok\",\"reason\":null,\"route_focus\":\"next_stop\",\"references_current_stop\":true,\"references_next_stop\":true}。"
        )
    if intent == "attraction_explain":
        return base + (
            "attraction_explain 用于景点是什么、为什么值得去、看点、历史、文化价值、怎么逛更好。"
            "普通景点问法不要误转成 live_info；口语、短句、随口提问也仍然按 attraction_explain 处理。"
            "先用 SQL 给稳定介绍和实用提醒；只有当问题超出 SQL 直接字段时，才用 RAG 补更深背景。"
            "如果没有 attraction 或 RAG 上下文，但 query 明确是北京景点问题，可以用模型通用知识回答，避免伪造实时信息。"
            "返回字段：answer, status, reason, grounding, includes_history, includes_tips。"
            "status 只能是 ok, degraded, unavailable, clarification。"
            "grounding 只能是 sql, rag, sql_then_rag, model_knowledge, limited。"
        )
    return base


def _build_user_prompt(intent: str, query: str, hybrid_context: HybridContext, language: str) -> str:
    attraction = _project_attraction_context(hybrid_context.prompt_safe_attraction)
    profile = _project_profile_context(hybrid_context.prompt_safe_profile)
    session_context = _project_session_context(hybrid_context.session_context)
    history = _project_dialogue_history(hybrid_context.dialogue_history)
    style = describe_guide_style(profile.get("guide_style_preference")) if profile else "balanced"

    decision_rules = [
        "按声明的 intent 回答，不要自行改 intent。",
        "不要把普通景点问法改成 live_info。",
        "不要因为中文口语、短句或随口表达就判 out_of_scope。",
        "不要补造缺失的路线状态、景点事实或实时事实。",
        "只能使用下方上下文。",
    ]

    sections = [
        "任务",
        f"- intent: {intent}",
        f"- user_language: {language}",
        f"- query: {query}",
        "",
        "判定规则",
        *[f"- {rule}" for rule in decision_rules],
    ]

    if intent == "translation":
        sections.extend(
            [
                "",
                "辅助上下文",
                f"- profile: {profile or {}}",
                f"- recent_dialogue: {history}",
            ]
        )
    elif intent == "live_info":
        sections.extend(
            [
                "",
                "景点上下文",
                f"- attraction: {attraction or {}}",
                "",
                "官方信息上下文",
                f"- live_info: {_project_live_info_context(hybrid_context)}",
                "",
                "用户画像",
                f"- profile: {profile or {}}",
            ]
        )
    elif intent == "weather_info":
        sections.extend(
            [
                "",
                "天气上下文",
                f"- weather: {getattr(hybrid_context, 'weather', None).model_dump() if getattr(hybrid_context, 'weather', None) else {}}",
                "",
                "会话上下文",
                f"- session: {session_context}",
                "",
                "用户画像",
                f"- profile: {profile or {}}",
            ]
        )
    elif intent == "trip_assistant":
        sections.extend(
            [
                "",
                "会话上下文",
                f"- session: {session_context}",
                "",
                "景点上下文",
                f"- attraction: {attraction or {}}",
                "",
                "用户画像",
                f"- profile: {profile or {}}",
                "",
                "最近对话",
                f"- dialogue: {history}",
            ]
        )
    elif intent == "attraction_explain":
        sections.extend(
            [
                "",
                "景点上下文",
                f"- attraction: {attraction or {}}",
                "",
                "用户画像",
                f"- profile: {profile or {}}",
                "",
                "RAG 补充上下文",
                f"- rag_support: {_project_rag_context(hybrid_context)}",
                "",
                "最近对话",
                f"- dialogue: {history}",
            ]
        )
    else:
        sections.extend(
            [
                "",
                "通用上下文",
                f"- session: {session_context}",
                f"- attraction: {attraction or {}}",
                f"- profile: {profile or {}}",
                f"- dialogue: {history}",
            ]
        )

    sections.extend(
        [
            "",
            "表达风格",
            f"- guide_style: {style}",
            "",
            "输出要求",
            "- 只返回一个 JSON 对象。",
            "- 不要在 JSON 前后添加任何文字。",
            "- answer 面向用户，简洁、自然、可直接展示。",
            "- answer 默认控制在 300 字以内，能短答就不要拉长。",
            "- 历史背景、文化解释类问题可以适当长一些，但长回复必须自然分段。",
        ]
    )
    return "\n".join(sections)


def _project_attraction_context(attraction: dict[str, object]) -> dict[str, object]:
    if not attraction:
        return {}
    projected: dict[str, object] = {}
    for key, value in attraction.items():
        if key in {"aliases", "tags", "highlights", "visitor_tips", "practical_notes", "photo_spot_notes"} and isinstance(value, list):
            projected[key] = value[:4]
        elif key in {"short_intro", "history"} and isinstance(value, str):
            projected[key] = _truncate_text(value, 220)
        else:
            projected[key] = value
    return projected


def _project_profile_context(profile: dict[str, object]) -> dict[str, object]:
    if not profile:
        return {}
    projected: dict[str, object] = {}
    for key, value in profile.items():
        if isinstance(value, list):
            projected[key] = value[:4]
        else:
            projected[key] = value
    return projected


def _project_session_context(session_context: dict[str, object]) -> dict[str, object]:
    if not session_context:
        return {}
    priority_keys = [
        "guide_session_id",
        "itinerary_version_id",
        "current_stop_name",
        "next_stop_name",
        "stop_count",
        "current_stop_index",
        "remaining_stop_count",
        "session_status",
        "user_id",
    ]
    projected = {key: session_context[key] for key in priority_keys if key in session_context}
    return projected or session_context


def _project_dialogue_history(history: list[dict[str, object]]) -> list[dict[str, object]]:
    if not history:
        return []
    projected: list[dict[str, object]] = []
    for message in history[-10:]:

        projected.append(
            {
                "role": message.get("role"),
                "content": _truncate_text(str(message.get("content", "")), 120),
            }
        )
    return projected


def _project_live_info_context(hybrid_context: HybridContext) -> dict[str, object]:
    live_info = hybrid_context.live_info
    if live_info is None:
        return {}
    return {
        "summary": _truncate_text(live_info.summary, 220),
        "updated_at": live_info.updated_at,
        "confidence": live_info.confidence,
        "not_confirmed": live_info.not_confirmed,
        "status": live_info.status,
        "reason": live_info.reason,
        "sources": live_info.sources[:2],
    }


def _project_rag_context(hybrid_context: HybridContext) -> dict[str, object]:
    rag = hybrid_context.rag
    if rag is None:
        return {}
    chunks: list[dict[str, object]] = []
    for chunk in rag.chunks[:3]:
        chunks.append(
            {
                "source": chunk.source,
                "score": chunk.score,
                "doc_type": chunk.metadata.get("doc_type"),
                "language": chunk.metadata.get("language"),
                "text": _truncate_text(chunk.text, 220),
            }
        )
    return {
        "retrieval_mode": rag.retrieval_mode,
        "fallback_used": rag.fallback_used,
        "chunks": chunks,
    }


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}…"
