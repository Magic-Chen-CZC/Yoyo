from __future__ import annotations

from yoyo.modules.integrations.amap.client import AmapRouteClient
from yoyo.modules.knowledge.schemas import WeatherContext


async def get_weather_context(location_name: str | None) -> WeatherContext:
    payload = await AmapRouteClient().get_weather(location_name)
    return WeatherContext(
        location_name=payload.get("location_name"),
        province=payload.get("province"),
        city=payload.get("city"),
        adcode=payload.get("adcode"),
        weather=payload.get("weather"),
        temperature_celsius=payload.get("temperature_celsius"),
        wind_direction=payload.get("wind_direction"),
        wind_power=payload.get("wind_power"),
        humidity=payload.get("humidity"),
        report_time=payload.get("report_time"),
        source=str(payload.get("source") or "amap"),
        status=str(payload.get("status") or "available"),
        reason=payload.get("reason"),
    )
