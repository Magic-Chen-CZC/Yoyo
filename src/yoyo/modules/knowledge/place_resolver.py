from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yoyo.modules.knowledge.attraction_retriever import DEFAULT_ATTRACTION_NAMES
from yoyo.modules.knowledge.navigation_place_registry_generated import (
    VISITBEIJING_NAVIGATION_PLACE_RECORDS,
)
from yoyo.modules.knowledge.schemas import NavigationPlace
from yoyo.modules.knowledge.seed_postgres import MOCK_SEED_BUNDLE
from yoyo.modules.knowledge.sql_retriever import filter_by_name


BEIJING_ADCODE_PREFIX = "110"
CURRENT_LOCATION_REFERENCES = ("这里", "这儿", "当前位置", "我这里", "我这儿", "当前定位", "定位点")
PLACE_AMBIGUITY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "commercial": (
        "餐厅",
        "饭店",
        "酒楼",
        "火锅",
        "烤鸭",
        "咖啡",
        "咖啡馆",
        "茶馆",
        "酒吧",
        "小吃",
        "小吃街",
        "美食",
        "美食街",
        "商户",
        "店铺",
        "门店",
        "分店",
        "旗舰店",
        "专卖店",
        "便利店",
        "超市",
        "商场",
        "购物中心",
        "百货",
        "商城",
    ),
    "lodging": (
        "酒店",
        "宾馆",
        "旅店",
        "旅馆",
        "民宿",
        "客栈",
    ),
    "building_address": (
        "写字楼",
        "办公楼",
        "公司",
        "大厦",
        "楼宇",
        "金融中心",
        "环球金融中心",
        "产业园",
        "园区",
        "号楼",
        "座",
        "层",
        "室",
        "地址",
        "路口",
    ),
    "nearby_reference": (
        "附近那个",
        "附近的",
        "旁边那个",
        "旁边的",
        "边上那个",
        "边上的",
        "那个",
        "这个",
        "这家",
        "那家",
    ),
    "facility": (
        "停车场",
        "停车楼",
        "地下车库",
        "入口",
        "出口",
        "东门",
        "西门",
        "南门",
        "北门",
    ),
}


@dataclass(frozen=True)
class RegisteredNavigationPlace:
    place_id: str
    name: str
    display_name: str
    aliases: tuple[str, ...]
    latitude: float
    longitude: float
    adcode: str
    city: str = "北京市"


CORE_NAVIGATION_PLACES: tuple[RegisteredNavigationPlace, ...] = (
    RegisteredNavigationPlace(
        place_id="tiananmen_square",
        name="Tiananmen Square",
        display_name="天安门广场",
        aliases=("天安门", "天安门广场", "tiananmen", "tiananmen square", "tiananmen plaza"),
        latitude=39.9050,
        longitude=116.3976,
        adcode="110101",
    ),
    RegisteredNavigationPlace(
        place_id="forbidden_city",
        name="Forbidden City",
        display_name="故宫",
        aliases=("故宫", "故宫博物院", "紫禁城", "forbidden city", "palace museum", "imperial palace"),
        latitude=39.9163,
        longitude=116.3972,
        adcode="110101",
    ),
    RegisteredNavigationPlace(
        place_id="jingshan_park",
        name="Jingshan Park",
        display_name="景山公园",
        aliases=("景山", "景山公园", "煤山公园", "jingshan", "jingshan park", "coal hill park"),
        latitude=39.9240,
        longitude=116.3967,
        adcode="110101",
    ),
    RegisteredNavigationPlace(
        place_id="temple_of_heaven",
        name="Temple of Heaven",
        display_name="天坛",
        aliases=("天坛", "祈年殿", "temple of heaven", "tiantan", "heaven temple"),
        latitude=39.8837,
        longitude=116.4120,
        adcode="110101",
    ),
    RegisteredNavigationPlace(
        place_id="summer_palace",
        name="Summer Palace",
        display_name="颐和园",
        aliases=("颐和园", "summer palace", "yiheyuan"),
        latitude=39.9996,
        longitude=116.2755,
        adcode="110108",
    ),
    RegisteredNavigationPlace(
        place_id="yuanmingyuan_park",
        name="Yuanmingyuan Park",
        display_name="圆明园",
        aliases=("圆明园", "圆明园遗址公园", "old summer palace", "yuanmingyuan"),
        latitude=40.0089,
        longitude=116.3025,
        adcode="110108",
    ),
    RegisteredNavigationPlace(
        place_id="beihai_park",
        name="Beihai Park",
        display_name="北海公园",
        aliases=("北海", "北海公园", "beihai", "beihai park"),
        latitude=39.9255,
        longitude=116.3836,
        adcode="110102",
    ),
    RegisteredNavigationPlace(
        place_id="shichahai",
        name="Shichahai",
        display_name="什刹海",
        aliases=("什刹海", "后海", "shichahai", "houhai"),
        latitude=39.9406,
        longitude=116.3853,
        adcode="110102",
    ),
    RegisteredNavigationPlace(
        place_id="nanluoguxiang",
        name="Nanluoguxiang",
        display_name="南锣鼓巷",
        aliases=("南锣鼓巷", "nanluoguxiang", "nanluogu xiang"),
        latitude=39.9397,
        longitude=116.4039,
        adcode="110101",
    ),
    RegisteredNavigationPlace(
        place_id="yonghe_temple",
        name="Yonghe Temple",
        display_name="雍和宫",
        aliases=("雍和宫", "雍和宫景区", "yonghe temple", "lama temple"),
        latitude=39.9466,
        longitude=116.4173,
        adcode="110101",
    ),
    RegisteredNavigationPlace(
        place_id="prince_gong_mansion",
        name="Prince Gong's Mansion",
        display_name="恭王府",
        aliases=("恭王府", "prince gong's mansion", "prince gong mansion", "gongwangfu"),
        latitude=39.9371,
        longitude=116.3868,
        adcode="110102",
    ),
    RegisteredNavigationPlace(
        place_id="zhengyangmen",
        name="Zhengyangmen",
        display_name="正阳门",
        aliases=("正阳门", "前门", "箭楼", "qianmen", "front gate", "zhengyangmen"),
        latitude=39.8994,
        longitude=116.3977,
        adcode="110101",
    ),
    RegisteredNavigationPlace(
        place_id="national_museum_of_china",
        name="National Museum of China",
        display_name="中国国家博物馆",
        aliases=("中国国家博物馆", "国家博物馆", "国博", "national museum of china", "national museum"),
        latitude=39.905374,
        longitude=116.401304,
        adcode="110101",
    ),
    RegisteredNavigationPlace(
        place_id="confucius_temple_and_guozijian",
        name="Confucius Temple and Guozijian Museum",
        display_name="孔庙和国子监博物馆",
        aliases=("孔庙和国子监博物馆", "孔庙", "国子监", "北京孔庙", "beijing confucius temple", "guozijian"),
        latitude=39.946631,
        longitude=116.413879,
        adcode="110101",
    ),
    RegisteredNavigationPlace(
        place_id="national_stadium",
        name="National Stadium",
        display_name="鸟巢",
        aliases=("鸟巢", "国家体育场", "国家体育场鸟巢", "北京鸟巢", "bird's nest", "national stadium"),
        latitude=39.991619,
        longitude=116.395615,
        adcode="110105",
    ),
    RegisteredNavigationPlace(
        place_id="national_aquatics_center",
        name="National Aquatics Center",
        display_name="水立方",
        aliases=("水立方", "国家游泳中心", "国家游泳中心水立方", "water cube", "national aquatics center"),
        latitude=39.993551,
        longitude=116.390727,
        adcode="110105",
    ),
    RegisteredNavigationPlace(
        place_id="art_zone_798",
        name="798 Art Zone",
        display_name="798艺术区",
        aliases=("798", "798艺术区", "七九八艺术区", "798 art zone", "798 art district"),
        latitude=39.983285,
        longitude=116.495027,
        adcode="110105",
    ),
    RegisteredNavigationPlace(
        place_id="jiangtai_station",
        name="Jiangtai Station",
        display_name="将台地铁站",
        aliases=("将台", "将台站", "将台地铁站", "jiangtai", "jiangtai station"),
        latitude=39.971026,
        longitude=116.490213,
        adcode="110105",
    ),
    RegisteredNavigationPlace(
        place_id="beijing_zoo",
        name="Beijing Zoo",
        display_name="北京动物园",
        aliases=("北京动物园", "动物园", "beijing zoo"),
        latitude=39.942105,
        longitude=116.336701,
        adcode="110102",
    ),
    RegisteredNavigationPlace(
        place_id="wutasi",
        name="Wutasi",
        display_name="五塔寺",
        aliases=("五塔寺", "北京石刻艺术博物馆", "五塔寺塔", "wutasi", "wuta temple"),
        latitude=39.944042,
        longitude=116.330417,
        adcode="110108",
    ),
)

VISITBEIJING_NAVIGATION_PLACES: tuple[RegisteredNavigationPlace, ...] = tuple(
    RegisteredNavigationPlace(
        place_id=str(record["place_id"]),
        name=str(record["name"]),
        display_name=str(record["display_name"]),
        aliases=tuple(str(alias) for alias in record.get("aliases", ())),
        latitude=float(record["latitude"]),
        longitude=float(record["longitude"]),
        adcode=str(record["adcode"]),
        city=str(record.get("city") or "北京市"),
    )
    for record in VISITBEIJING_NAVIGATION_PLACE_RECORDS
)

REGISTERED_NAVIGATION_PLACES: tuple[RegisteredNavigationPlace, ...] = (
    CORE_NAVIGATION_PLACES + VISITBEIJING_NAVIGATION_PLACES
)

_REGISTERED_BY_NAME = {
    item.name.lower(): item for item in REGISTERED_NAVIGATION_PLACES
}
_REGISTERED_BY_ALIAS = {
    alias.strip().lower(): item
    for item in REGISTERED_NAVIGATION_PLACES
    for alias in (item.name, item.display_name, *item.aliases)
    if alias.strip()
}


def make_gps_navigation_place(current_position: dict[str, Any] | None) -> NavigationPlace | None:
    if not isinstance(current_position, dict):
        return None
    try:
        latitude = float(current_position.get("latitude"))
        longitude = float(current_position.get("longitude"))
    except (TypeError, ValueError):
        return None
    return NavigationPlace(
        raw_text="当前位置",
        place_id="gps_current_position",
        name="当前位置",
        display_name="当前位置",
        latitude=latitude,
        longitude=longitude,
        city="北京市",
        adcode=None,
        source="gps",
        confidence=1.0,
        reason="session_current_position",
    )


def resolve_navigation_place(text: str | None) -> NavigationPlace | None:
    raw = _clean_place_text(text)
    if not raw:
        return None
    if is_current_location_reference(raw):
        return None
    lowered = raw.lower()
    registered = _REGISTERED_BY_ALIAS.get(lowered)
    if registered is not None:
        return _registered_to_place(registered, raw, confidence=1.0)

    if place_text_has_ambiguity_signal(raw) and registered_navigation_place_matches(raw):
        return NavigationPlace(
            raw_text=raw,
            place_id=None,
            name=raw,
            display_name=raw,
            city="北京市",
            source="geocode_candidate",
            confidence=0.46,
            reason="registered_alias_with_ambiguity_signal",
        )

    for alias, registered_place in sorted(_REGISTERED_BY_ALIAS.items(), key=lambda item: len(item[0]), reverse=True):
        if alias and alias in lowered:
            return _registered_to_place(registered_place, raw, confidence=0.94, reason="alias_substring_match")

    canonical_name = DEFAULT_ATTRACTION_NAMES.get(lowered)
    if canonical_name:
        registered = _REGISTERED_BY_NAME.get(canonical_name.lower())
        if registered is not None:
            return _registered_to_place(registered, raw, confidence=0.98, reason="known_attraction_alias")

    matches = filter_by_name(MOCK_SEED_BUNDLE.attractions, raw)
    if matches:
        attraction = matches[0]
        registered = _REGISTERED_BY_NAME.get(attraction.name.lower())
        if registered is not None:
            return _registered_to_place(registered, raw, confidence=0.95, reason="mock_attraction_registered")
        return NavigationPlace(
            raw_text=raw,
            place_id=attraction.id,
            name=attraction.name,
            display_name=attraction.name,
            latitude=attraction.latitude,
            longitude=attraction.longitude,
            city="北京市",
            adcode=None,
            source="mock_attraction",
            confidence=0.82,
            reason="mock_attraction_match",
        )

    return NavigationPlace(
        raw_text=raw,
        place_id=None,
        name=raw,
        display_name=raw,
        city="北京市",
        source="geocode_candidate",
        confidence=0.45,
        reason="unregistered_beijing_geocode_candidate",
    )


def place_text_has_ambiguity_signal(text: str | None) -> bool:
    categories = place_ambiguity_categories(text)
    return bool(categories)


def place_ambiguity_categories(text: str | None) -> list[str]:
    raw = _clean_place_text(text)
    if not raw:
        return []
    return [
        category
        for category, keywords in PLACE_AMBIGUITY_KEYWORDS.items()
        if any(keyword in raw for keyword in keywords)
    ]


def registered_navigation_place_matches(text: str | None) -> list[NavigationPlace]:
    raw = _clean_place_text(text)
    if not raw:
        return []
    lowered = raw.lower()
    seen: set[str] = set()
    matches: list[NavigationPlace] = []
    for alias, registered_place in sorted(_REGISTERED_BY_ALIAS.items(), key=lambda item: len(item[0]), reverse=True):
        if not alias or alias not in lowered or registered_place.place_id in seen:
            continue
        seen.add(registered_place.place_id)
        matches.append(
            _registered_to_place(
                registered_place,
                raw,
                confidence=0.9,
                reason="registered_alias_candidate_for_clarification",
            )
        )
    return matches


def is_beijing_adcode(adcode: object) -> bool:
    return isinstance(adcode, str) and adcode.startswith(BEIJING_ADCODE_PREFIX)


def is_current_location_reference(text: str | None) -> bool:
    raw = _clean_place_text(text)
    return raw in CURRENT_LOCATION_REFERENCES


def navigation_candidate_places() -> dict[str, list[str]]:
    candidates = {
        item.name: [item.display_name, *item.aliases]
        for item in REGISTERED_NAVIGATION_PLACES
    }
    for attraction in MOCK_SEED_BUNDLE.attractions[:10]:
        candidates.setdefault(attraction.name, list(attraction.aliases))
    return candidates


def _registered_to_place(
    item: RegisteredNavigationPlace,
    raw_text: str,
    *,
    confidence: float,
    reason: str = "registered_navigation_place",
) -> NavigationPlace:
    return NavigationPlace(
        raw_text=raw_text,
        place_id=item.place_id,
        name=item.name,
        display_name=item.display_name,
        latitude=item.latitude,
        longitude=item.longitude,
        city=item.city,
        adcode=item.adcode,
        source="registry",
        confidence=confidence,
        reason=reason,
    )


def _clean_place_text(text: str | None) -> str:
    cleaned = (text or "").strip()
    for token in ("请问", "麻烦", "帮我", "告诉我", "一下", "附近", "周边", "入口", "门口"):
        cleaned = cleaned.replace(token, "")
    return cleaned.strip(" ，。！？?；;：:")
