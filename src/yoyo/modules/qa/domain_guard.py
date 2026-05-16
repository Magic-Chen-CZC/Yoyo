# domain guard 是 QA 的第一道门。
# 当前职责收窄为：只拒绝明显域外的问题，不做细 intent 路由。
from __future__ import annotations

from yoyo.modules.qa.rule_assets import HARD_DENY_KEYWORDS
from yoyo.modules.qa.schemas import DomainGuardResult

SUPPORTED_KEYWORDS = {
    "beijing",
    "forbidden city",
    "tiananmen",
    "jingshan",
    "temple of heaven",
    "summer palace",
    "zhengyangmen",
    "national museum",
    "bird's nest",
    "national stadium",
    "water cube",
    "great wall",
    "badaling",
    "mutianyu",
    "trip",
    "route",
    "itinerary",
    "attraction",
    "translate",
    "translation",
    "weather",
    "ticket",
    "guide",
    "museum",
    "park",
    "palace",
    "next stop",
    "opening hours",
    "reservation",
    "official",
    "北京",
    "故宫",
    "故宫博物院",
    "天安门",
    "景山",
    "景山公园",
    "天坛",
    "正阳门",
    "前门",
    "国家博物馆",
    "中国国家博物馆",
    "鸟巢",
    "国家体育场",
    "水立方",
    "八达岭长城",
    "慕田峪长城",
    "798",
    "798艺术区",
    "景点",
    "路线",
    "导览",
    "翻译",
    "下一站",
    "接下来",
    "先做什么",
    "历史",
    "讲讲",
    "介绍",
    "注意事项",
    "中轴线",
    "象征意义",
    "预约",
    "公告",
}

_DYNAMIC_TRAVEL_HINTS = {
    "weather",
    "rain",
    "traffic",
    "congestion",
    "crowd",
    "busy",
    "天气",
    "下雨",
    "交通",
    "堵",
    "拥挤",
    "人多",
}

_TRAVEL_ANCHORS = {
    "beijing",
    "trip",
    "route",
    "itinerary",
    "attraction",
    "forbidden city",
    "tiananmen",
    "jingshan",
    "temple of heaven",
    "zhengyangmen",
    "national museum",
    "bird's nest",
    "national stadium",
    "water cube",
    "great wall",
    "badaling",
    "mutianyu",
    "museum",
    "park",
    "palace",
    "ticket",
    "reservation",
    "opening hours",
    "official",
    "北京",
    "故宫",
    "故宫博物院",
    "天安门",
    "景山",
    "景山公园",
    "天坛",
    "正阳门",
    "前门",
    "国家博物馆",
    "中国国家博物馆",
    "鸟巢",
    "国家体育场",
    "水立方",
    "八达岭长城",
    "慕田峪长城",
    "798",
    "798艺术区",
    "景点",
    "路线",
    "行程",
    "门票",
    "预约",
    "公告",
}

_HARD_DENY_HINTS = set(HARD_DENY_KEYWORDS)


def evaluate_domain_support(query: str) -> DomainGuardResult:
    lowered = query.strip().lower()
    if not lowered:
        return DomainGuardResult(
            supported=False,
            hard_deny=True,
            deny_reason="empty_query",
            matched_signals=[],
        )

    matched_support = [keyword for keyword in SUPPORTED_KEYWORDS if keyword in lowered]
    matched_hard_deny = [keyword for keyword in _HARD_DENY_HINTS if keyword in lowered]
    has_dynamic_travel_need = any(keyword in lowered for keyword in _DYNAMIC_TRAVEL_HINTS)
    has_travel_anchor = any(keyword in lowered for keyword in _TRAVEL_ANCHORS)
    short_follow_up = lowered in {"it", "that one", "what about this one", "and next?", "那这个呢", "这个呢", "那接下来呢"}

    if matched_hard_deny:
        return DomainGuardResult(
            supported=False,
            hard_deny=True,
            deny_reason="hard_deny_non_travel_domain",
            matched_signals=matched_hard_deny[:6],
        )

    if matched_support:
        return DomainGuardResult(
            supported=True,
            hard_deny=False,
            deny_reason=None,
            matched_signals=matched_support[:6],
        )

    if has_dynamic_travel_need and has_travel_anchor:
        return DomainGuardResult(
            supported=True,
            hard_deny=False,
            deny_reason=None,
            matched_signals=["dynamic_travel_need", "travel_anchor"],
        )

    if short_follow_up:
        return DomainGuardResult(
            supported=True,
            hard_deny=False,
            deny_reason=None,
            matched_signals=["short_follow_up"],
        )

    return DomainGuardResult(
        supported=True,
        hard_deny=False,
        deny_reason=None,
        matched_signals=[],
    )



def is_supported_query(query: str) -> bool:
    return evaluate_domain_support(query).supported
