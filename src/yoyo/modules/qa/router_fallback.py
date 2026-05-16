from __future__ import annotations

import json

from yoyo.core.config import get_settings
from yoyo.modules.llm.factory import get_llm_runtime
from yoyo.modules.llm.schemas import GenerationOptions, LLMRequest, PromptMessage
from yoyo.modules.qa.schemas import IntentRouterFallbackResult, NavigationSlotResult, QAIntent, WeatherSlotResult

_ALLOWED_INTENTS: tuple[QAIntent, ...] = (
    "translation",
    "live_info",
    "weather_info",
    "navigation_text",
    "trip_assistant",
    "attraction_explain",
    "manual_route_edit_redirect",
    "smalltalk",
    "out_of_scope",
)


async def resolve_router_fallback(
    *,
    query: str,
    raw_query: str | None,
    pivot_query: str | None,
    language: str,
    market: str | None,
    dialogue_history: list[dict[str, object]],
    rule_result: dict[str, object],
    session_context: dict[str, object],
    pending_clarification: dict[str, object] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[IntentRouterFallbackResult | None, dict[str, object]]:
    settings = get_settings()
    runtime = get_llm_runtime()
    selected_provider = provider or settings.qa_router_fallback_provider
    selected_model = model or settings.qa_router_fallback_model
    history = dialogue_history[-3:]
    clarification_prompt = ""
    if pending_clarification is not None:
        clarification_prompt = (
            "当前可能存在一个待处理的上一轮澄清 pending_clarification。"
            "你仍然必须先判断用户最新这句话的真实意图，不要因为有 pending_clarification 就强行判成导航。"
            "如果用户最新这句话是在选择 pending_clarification.candidates 里的一个地点，则 intent 必须是 navigation_text，"
            "并额外返回 clarification_action='selected' 和 selected_index。selected_index 必须是已有候选编号，不能新增候选，不能编坐标。"
            "如果用户最新这句话明显切换到了天气、开放信息、景点讲解、翻译、闲聊或改路线等新任务，则按新任务返回 intent，"
            "并返回 clarification_action='not_a_selection'。"
            "如果用户看起来还在回答澄清，但无法稳定判断选哪一个，则 intent 返回 navigation_text，"
            "clarification_action='needs_clarification'，selected_index=null。"
            "只有存在 pending_clarification 时，才允许额外返回 clarification_action 和 selected_index。"
        )
    request = LLMRequest(
        provider=selected_provider,
        model=selected_model,
        messages=[
            PromptMessage(
                role="system",
                content=(
                    "你是一个北京旅游 QA 产品的意图路由分类器。你的任务不是回答用户，而是把用户最新这句话准确归到且只归到一个意图。"
                    "可选意图只有：translation、live_info、weather_info、navigation_text、trip_assistant、attraction_explain、manual_route_edit_redirect、smalltalk、out_of_scope。"
                    "你只能返回 JSON。默认只能包含 intent、confidence、reason 三个字段；只有当 intent=weather_info 时，才额外允许返回 weather_location_name 字段。不要输出任何额外文本。"
                    "意图定义如下：translation=用户明确要求翻译、改写成另一种语言或双语展示；"
                    "live_info=用户询问今天/当前/同日的开放、预约、检票、营业安排、临时公告等官方运营信息；"
                    "weather_info=用户询问景点或区域的天气、降雨、温度、天气预报；"
                    "navigation_text=用户明确要求从起点到终点的文字路线、怎么走、路线步骤、步行或驾车导航；"
                    "trip_assistant=用户询问接下来怎么安排、下一站去哪、怎么走更轻松，但没有明确要求点到点导航或修改现有路线；"
                    "attraction_explain=用户询问景点意义、历史、看点、文化价值、为什么值得去，包括更深的建筑、象征、仪式、政治表达、空间秩序等解释；"
                    "manual_route_edit_redirect=用户明确要求修改、替换、删除、重排、缩短或放松现有路线或站点安排；"
                    "smalltalk=用户在寒暄、打招呼、简单自我介绍式闲聊，或轻量聊天如‘你叫什么名字’、‘你在吗’、‘你好呀’；"
                    "out_of_scope=非旅游任务、没有足够上下文的弱 follow-up，或当前不支持的旅游邻接话题，包括拥挤度、人流量、排队热度，以及泛交通拥堵状态。"
                    "冲突优先级：1）明确翻译请求优先归 translation；2）今天/当前/开放/预约/营业/临时公告等实时信号优先归 live_info；3）天气、下雨、温度、预报等优先归 weather_info；"
                    "4）明确从 A 到 B 怎么走、文字导航、路线步骤优先归 navigation_text；5）明确改路线、换点、删点、重排、轻松一点等诉求优先归 manual_route_edit_redirect；6）只有在没有明确点到点导航或改路线诉求时，‘接下来怎么安排/下一站去哪’才归 trip_assistant；"
                    "7）拥挤度、排队、人流量、泛交通拥堵统一归 out_of_scope，不要误判成 live_info 或 weather_info。"
                    "8）SQL / RAG 分工要牢记：景点简介、稳定事实、实用提醒、会话路线状态属于下游 SQL-first 能力；更深的历史、象征、建筑、中轴线背景属于下游 RAG 补充能力。不要因为用户问得更深、问法更学术、句子更长，就改判成 out_of_scope，仍应保持 attraction_explain。"
                    "9）若用户问的是天气，应判 weather_info；若用户问的是交通拥堵/人流拥挤，不属于 weather_info 或 live_info，应判 out_of_scope。"
                    "10）像‘为什么重要’、‘请深入解释’、‘作为一种政治表达/象征系统来看’、‘不仅仅是建筑’这类深解释问法，只要对象仍是北京景点或景区空间，应保持 attraction_explain。"
                    "11）当且仅当 intent=weather_info 时，请顺手抽取 weather_location_name：优先取 query/raw_query/pivot_query 中用户显式提到的城市、区域或景点；若用户未明说，再把 session_context 仅作为弱提示。若仍无法稳定判断，则返回 null。不要让 session_context 覆盖用户显式地点。"
                    "只有当最新一句明显是省略表达、单看当前句无法判断时，才参考 history；如果当前句本身已经自足，以当前句为准。"
                    f"{clarification_prompt}"
                    "confidence 必须是 0 到 1 之间的数字；reason 必须简短具体。"
                ),
            ),
            PromptMessage(
                role="user",
                content=(
                    f"language={language}\n"
                    f"market={market or ''}\n"
                    f"query={query}\n"
                    f"raw_query={raw_query or ''}\n"
                    f"pivot_query={pivot_query or ''}\n"
                    f"history={json.dumps(history, ensure_ascii=False)}\n"
                    f"rule_result={json.dumps(rule_result, ensure_ascii=False)}\n"
                    f"session_context={json.dumps(session_context, ensure_ascii=False)}\n"
                    f"pending_clarification={json.dumps(pending_clarification or {}, ensure_ascii=False)}"
                ),
            ),
        ],
        options=GenerationOptions(max_tokens=96, temperature=0.0, timeout_seconds=8.0),
        metadata={"prompt_version": "qa-router-fallback-zh-v1"},
    )
    response = await runtime.generate(request)
    metadata = {
        "llm": {
            "provider": response.provider,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "usage": response.usage.model_dump(),
            "prompt_version": request.metadata.get("prompt_version"),
            "error": response.error.model_dump() if response.error else None,
        }
    }
    if response.error is not None or not response.text.strip():
        return None, metadata
    try:
        payload = json.loads(response.text.strip())
    except json.JSONDecodeError:
        return None, metadata
    if not isinstance(payload, dict):
        return None, metadata
    intent = payload.get("intent")
    confidence = payload.get("confidence")
    reason = payload.get("reason")
    if intent not in _ALLOWED_INTENTS:
        return None, metadata
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        confidence_value = 0.5
    weather_location_name = payload.get("weather_location_name") if isinstance(payload.get("weather_location_name"), str) else None
    clarification_action = (
        payload.get("clarification_action")
        if payload.get("clarification_action") in {"selected", "needs_clarification", "not_a_selection"}
        else None
    )
    selected_index = _optional_int(payload.get("selected_index"))
    result = IntentRouterFallbackResult(
        intent=intent,
        confidence=max(0.0, min(1.0, confidence_value)),
        reason=reason if isinstance(reason, str) else None,
        used_translation_pivot=bool(pivot_query),
        pivot_query=pivot_query,
        weather_location_name=weather_location_name.strip() if weather_location_name and weather_location_name.strip() else None,
        clarification_action=clarification_action,
        selected_index=selected_index,
    )
    metadata["llm"]["structured_output_valid"] = True
    metadata["llm"]["structured_output"] = result.model_dump()
    return result, metadata


def _optional_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


async def resolve_weather_slot_fallback(
    *,
    query: str,
    raw_query: str | None,
    pivot_query: str | None,
    session_context: dict[str, object],
    rule_result: dict[str, object] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[WeatherSlotResult | None, dict[str, object]]:
    settings = get_settings()
    runtime = get_llm_runtime()
    selected_provider = provider or settings.qa_router_fallback_provider
    selected_model = model or settings.qa_router_fallback_model
    request = LLMRequest(
        provider=selected_provider,
        model=selected_model,
        messages=[
            PromptMessage(
                role="system",
                content=(
                    "你是北京旅游天气地点抽取器。你的任务不是回答用户，而是从用户天气问题里抽取最合适的查询地点。"
                    "你只能返回 JSON，且只能包含 location_name、reason 两个字段。"
                    "location_name 必须是单个字符串或 null，不要返回数组。"
                    "优先抽取用户在 query/raw_query/pivot_query 里显式提到的城市、区域或景点，例如北京、故宫、天安门。"
                    "session_context 只能作为弱提示，只有在用户这句话没有明确地点时才可参考 current_stop_name、next_stop_name、city_code 等上下文帮助判断。"
                    "不要让 session_context 覆盖或改写用户显式提到的地点。"
                    "如果用户没有明确地点，且结合上下文也无法稳定判断，就返回 null。"
                    "不要把天气现象、时间词、语气词当成地点。"
                ),
            ),
            PromptMessage(
                role="user",
                content=(
                    f"query={query}\n"
                    f"raw_query={raw_query or ''}\n"
                    f"pivot_query={pivot_query or ''}\n"
                    f"session_context={json.dumps(session_context, ensure_ascii=False)}\n"
                    f"rule_result={json.dumps(rule_result or {}, ensure_ascii=False)}"
                ),
            ),
        ],
        options=GenerationOptions(max_tokens=80, temperature=0.0, timeout_seconds=8.0),
        metadata={"prompt_version": "qa-weather-slot-fallback-zh-v1"},
    )
    response = await runtime.generate(request)
    metadata = {
        "llm": {
            "provider": response.provider,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "usage": response.usage.model_dump(),
            "prompt_version": request.metadata.get("prompt_version"),
            "error": response.error.model_dump() if response.error else None,
        }
    }
    if response.error is not None or not response.text.strip():
        return None, metadata
    try:
        payload = json.loads(response.text.strip())
    except json.JSONDecodeError:
        return None, metadata
    if not isinstance(payload, dict):
        return None, metadata
    location_name = payload.get("location_name") if isinstance(payload.get("location_name"), str) else None
    result = WeatherSlotResult(
        location_name=location_name.strip() if location_name and location_name.strip() else None,
        source="fallback",
        reason=payload.get("reason") if isinstance(payload.get("reason"), str) else None,
    )
    metadata["llm"]["structured_output_valid"] = True
    metadata["llm"]["structured_output"] = result.model_dump()
    return result, metadata


async def resolve_navigation_slot_fallback(
    *,
    query: str,
    raw_query: str | None,
    pivot_query: str | None,
    session_context: dict[str, object],
    candidate_places: dict[str, list[str]],
    rule_result: dict[str, object] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[NavigationSlotResult | None, dict[str, object]]:
    settings = get_settings()
    runtime = get_llm_runtime()
    selected_provider = provider or settings.qa_router_fallback_provider
    selected_model = model or settings.qa_router_fallback_model
    request = LLMRequest(
        provider=selected_provider,
        model=selected_model,
        messages=[
            PromptMessage(
                role="system",
                content=(
                    "你是北京旅游导航槽位提取器。你的任务不是回答用户，而是把用户的导航请求抽成 JSON。"
                    "你只能返回 JSON，且只能包含 origin、destinations、mode、mode_source、transit_preference、source、request_kind、reason 八个字段。"
                    "request_kind 只能是：next_stop、destination_only、explicit_route、multi_leg、unknown。"
                    "mode 只能是 walking、driving 或 transit。mode_source 只能是 explicit 或 fallback；用户明确说步行、走路、开车、打车、公交、地铁、公共交通、换乘时返回 explicit，否则返回 fallback。source 固定返回 fallback。"
                    "transit_preference 只能是 bus、subway、public_transport 或 null；用户明确说公交/公交车时返回 bus，明确说地铁/几号线时返回 subway，只说公共交通/换乘/坐车时返回 public_transport。"
                    "destinations 必须是字符串数组，可为空。"
                    "请重点覆盖：下一站怎么去；到X怎么走/去X怎么走；从A到B怎么走；从A到B再到C/去A再去B。"
                    "如果用户没有明确起点，但像‘到故宫怎么走’这类句子明显是目的地型请求，可把 origin 置空，由下游用 session current stop 补。"
                    "如果用户说‘这里/这儿/当前位置/我这儿’，origin 返回‘当前位置’，不要猜具体景点名。"
                    "如果是多地点，destinations 按用户表达顺序输出。"
                    "如果内容更像改路线、删点、换点、重排，不要伪造导航槽位，返回 unknown 和空 destinations。"
                    "候选地点表仅用于归一化；若能明确对应候选 canonical 名，优先输出 canonical 名。"
                    "不要凭空决定同名地点属于哪个城市；不确定时保留用户原文，由下游北京地点解析器处理。"
                ),
            ),
            PromptMessage(
                role="user",
                content=(
                    f"query={query}\n"
                    f"raw_query={raw_query or ''}\n"
                    f"pivot_query={pivot_query or ''}\n"
                    f"session_context={json.dumps(session_context, ensure_ascii=False)}\n"
                    f"rule_result={json.dumps(rule_result or {}, ensure_ascii=False)}\n"
                    f"candidate_places={json.dumps(candidate_places, ensure_ascii=False)}"
                ),
            ),
        ],
        options=GenerationOptions(max_tokens=180, temperature=0.0, timeout_seconds=8.0),
        metadata={"prompt_version": "qa-navigation-slot-fallback-zh-v1"},
    )
    response = await runtime.generate(request)
    metadata = {
        "llm": {
            "provider": response.provider,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "usage": response.usage.model_dump(),
            "prompt_version": request.metadata.get("prompt_version"),
            "error": response.error.model_dump() if response.error else None,
        }
    }
    if response.error is not None or not response.text.strip():
        return None, metadata
    try:
        payload = json.loads(response.text.strip())
    except json.JSONDecodeError:
        return None, metadata
    if not isinstance(payload, dict):
        return None, metadata
    destinations = payload.get("destinations")
    if not isinstance(destinations, list):
        destinations = []
    mode = payload.get("mode") if payload.get("mode") in {"walking", "driving", "transit"} else "walking"
    mode_source = payload.get("mode_source") if payload.get("mode_source") in {"explicit", "fallback"} else "fallback"
    transit_preference = (
        payload.get("transit_preference")
        if payload.get("transit_preference") in {"bus", "subway", "public_transport"}
        else None
    )
    if mode != "transit":
        transit_preference = None
    request_kind = payload.get("request_kind") if payload.get("request_kind") in {"next_stop", "destination_only", "explicit_route", "multi_leg", "unknown"} else "unknown"
    result = NavigationSlotResult(
        origin=payload.get("origin") if isinstance(payload.get("origin"), str) else None,
        destinations=[item for item in destinations if isinstance(item, str) and item.strip()],
        mode=mode,
        mode_source=mode_source,
        transit_preference=transit_preference,
        source="fallback",
        request_kind=request_kind,
        reason=payload.get("reason") if isinstance(payload.get("reason"), str) else None,
    )
    metadata["llm"]["structured_output_valid"] = True
    metadata["llm"]["structured_output"] = result.model_dump()
    return result, metadata
