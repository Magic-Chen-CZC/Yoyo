from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

from redis.asyncio import Redis

from yoyo.core.config import get_settings

_REDIS_BACKOFF_UNTIL = 0.0
_REDIS_BACKOFF_SECONDS = 60.0
_BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def classify_live_info_type(query: str) -> str:
    normalized = _normalize_text(query)
    if _contains_any(
        normalized,
        (
            "临时关闭",
            "临时闭馆",
            "闭馆",
            "关闭",
            "停开",
            "暂停开放",
            "公告",
            "notice",
            "closure",
            "closed",
            "temporarily closed",
        ),
    ):
        return "closure_notice"
    if _contains_any(
        normalized,
        ("预约", "预订", "订票", "门票", "票", "购票", "ticket", "reservation", "booking"),
    ):
        return "ticketing"
    if _contains_any(normalized, ("几点", "时间", "营业时间", "开放时间", "hours", "time")):
        return "hours"
    if _contains_any(
        normalized,
        ("开放", "开门", "营业", "能去", "可以去", "open", "opening", "available today"),
    ):
        return "opening"
    return "general"


def build_live_info_cache_key(
    *,
    query: str,
    subject: str | None,
    info_type: str | None = None,
    date_text: str | None = None,
) -> str:
    resolved_info_type = info_type or classify_live_info_type(query)
    resolved_date = date_text or datetime.now(_BEIJING_TZ).date().isoformat()
    subject_slug = _slug(subject or "current-attraction")
    parts = ["qa", "live_info", "v1", resolved_date, subject_slug, resolved_info_type]
    if resolved_info_type == "general":
        parts.append(_short_hash(_normalize_text(query)))
    return ":".join(parts)


def live_info_cache_ttl_seconds(info_type: str, status: str | None) -> int:
    settings = get_settings()
    if status in {"degraded", "unavailable"}:
        return max(1, settings.live_info_cache_failure_ttl_seconds)
    if info_type == "closure_notice":
        return max(1, settings.live_info_cache_notice_ttl_seconds)
    return max(1, settings.live_info_cache_ttl_seconds)


async def get_cached_live_info(cache_key: str) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.live_info_cache_enabled or _redis_in_backoff():
        return None
    try:
        raw = await _redis_client(settings.redis_url).get(cache_key)
    except Exception:
        _mark_redis_backoff()
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    payload["cache_hit"] = True
    payload["cache_key"] = cache_key
    return payload


async def set_cached_live_info(cache_key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    settings = get_settings()
    if not settings.live_info_cache_enabled or _redis_in_backoff():
        return
    try:
        await _redis_client(settings.redis_url).set(
            cache_key,
            json.dumps(payload, ensure_ascii=False),
            ex=ttl_seconds,
        )
    except Exception:
        _mark_redis_backoff()


@lru_cache
def _redis_client(redis_url: str) -> Redis:
    return Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=0.2,
        socket_timeout=0.2,
    )


def _redis_in_backoff() -> bool:
    return time.monotonic() < _REDIS_BACKOFF_UNTIL


def _mark_redis_backoff() -> None:
    global _REDIS_BACKOFF_UNTIL
    _REDIS_BACKOFF_UNTIL = time.monotonic() + _REDIS_BACKOFF_SECONDS


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _slug(value: str) -> str:
    normalized = _normalize_text(value)
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", normalized).strip("-")
    if not slug:
        return "unknown"
    return slug[:80]


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
