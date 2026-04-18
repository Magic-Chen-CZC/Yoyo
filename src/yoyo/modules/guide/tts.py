from __future__ import annotations

import hashlib
from pathlib import Path

from yoyo.core.config import PROJECT_ROOT, get_settings
from yoyo.modules.knowledge.schemas import ProfileContext

try:
    import dashscope
except Exception:  # pragma: no cover
    dashscope = None  # type: ignore[assignment]


def _resolve_voice(profile: ProfileContext | None) -> str:
    settings = get_settings()
    guide_style = (profile.guide_style_preference if profile else "SJ") or "SJ"
    voice_map = {
        "NF": settings.tts_voice,
        "NT": settings.tts_voice,
        "SJ": settings.tts_voice,
        "SP": settings.tts_voice,
    }
    return voice_map.get(guide_style, settings.tts_voice)


def _segment_file_name(stop_id: str, segment_index: int, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{stop_id}-{segment_index}-{digest}.mp3"


def _storage_dir() -> Path:
    settings = get_settings()
    directory = PROJECT_ROOT / settings.tts_storage_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _extract_dashscope_audio_bytes(response: object) -> bytes:
    output = getattr(response, "output", None)
    if output is None and isinstance(response, dict):
        output = response.get("output")
    if output is None:
        return b""

    audio = None
    if isinstance(output, dict):
        audio = output.get("audio")
    else:
        try:
            audio = getattr(output, "audio", None)
        except Exception:
            audio = None

    if isinstance(audio, dict):
        for key in ("data", "audio", "audio_bytes"):
            value = audio.get(key)
            if isinstance(value, bytes):
                return value
            if isinstance(value, str) and value:
                return value.encode("utf-8")
        url = audio.get("url")
        if isinstance(url, str) and url:
            return url.encode("utf-8")
        return b""

    if audio is not None:
        for key in ("data", "audio", "audio_bytes", "url"):
            try:
                value = getattr(audio, key, None)
            except Exception:
                value = None
            if isinstance(value, bytes):
                return value
            if isinstance(value, str) and value:
                return value.encode("utf-8")
    return b""


async def synthesize_text_segment(
    *,
    stop_id: str,
    stop_name: str | None,
    segment_index: int,
    text: str,
    profile: ProfileContext | None,
) -> dict[str, object]:
    settings = get_settings()
    cleaned_text = text.strip()
    if not cleaned_text:
        return {
            "stop_id": stop_id,
            "stop_name": stop_name,
            "segment_index": segment_index,
            "status": "skipped",
            "url": None,
        }
    if not settings.tts_api_key:
        return {
            "stop_id": stop_id,
            "stop_name": stop_name,
            "segment_index": segment_index,
            "status": "unavailable",
            "url": None,
        }
    file_name = _segment_file_name(stop_id, segment_index, cleaned_text)
    output_path = _storage_dir() / file_name
    if output_path.exists():
        return {
            "stop_id": stop_id,
            "stop_name": stop_name,
            "segment_index": segment_index,
            "status": "ready",
            "url": str(output_path),
        }

    voice_id = _resolve_voice(profile)
    if dashscope is None:
        return {
            "stop_id": stop_id,
            "stop_name": stop_name,
            "segment_index": segment_index,
            "status": "unavailable",
            "url": None,
        }
    try:
        dashscope.base_http_api_url = settings.tts_base_url
        response = dashscope.MultiModalConversation.call(
            model=settings.tts_model,
            api_key=settings.tts_api_key,
            text=cleaned_text,
            voice=voice_id,
        )
        audio_bytes = _extract_dashscope_audio_bytes(response)
        if not audio_bytes:
            return {
                "stop_id": stop_id,
                "stop_name": stop_name,
                "segment_index": segment_index,
                "status": "unavailable",
                "url": None,
            }
        if audio_bytes.startswith(b"http://") or audio_bytes.startswith(b"https://"):
            output_path.write_text(audio_bytes.decode("utf-8"), encoding="utf-8")
        else:
            output_path.write_bytes(audio_bytes)
        if not output_path.exists() or output_path.stat().st_size == 0:
            return {
                "stop_id": stop_id,
                "stop_name": stop_name,
                "segment_index": segment_index,
                "status": "unavailable",
                "url": None,
            }
    except Exception:
        return {
            "stop_id": stop_id,
            "stop_name": stop_name,
            "segment_index": segment_index,
            "status": "unavailable",
            "url": None,
        }
    return {
        "stop_id": stop_id,
        "stop_name": stop_name,
        "segment_index": segment_index,
        "status": "ready",
        "url": str(output_path),
    }
