from __future__ import annotations

from dataclasses import dataclass

from yoyo.modules.knowledge.schemas import AttractionContext, ProfileContext


@dataclass(frozen=True)
class MockSeedBundle:
    attractions: list[AttractionContext]
    profiles: list[ProfileContext]


_BASE_ATTRACTIONS = [
    {
        "id": "attr-tiananmen-square",
        "name": "Tiananmen Square",
        "aliases": ["Tiananmen", "Tiananmen Plaza"],
        "category": "landmark",
        "latitude": 39.9050,
        "longitude": 116.3976,
        "recommended_duration_minutes": 45,
        "tags": ["central", "history", "symbolic"],
        "short_intro": "A major civic landmark in central Beijing and one of the city’s most recognizable public spaces.",
        "history": "It has long served as a ceremonial and political landmark in modern Chinese history.",
        "highlights": ["large ceremonial square", "easy route anchor", "historic city-center context"],
        "visitor_tips": ["Visit early to avoid crowds", "Pair it with the Forbidden City route"],
        "practical_notes": ["Security checks may affect pacing", "Open plaza conditions vary with weather"],
        "family_friendly_notes": ["Wide open space is easier for group movement"],
        "photo_spot_notes": ["Best wide-angle shots come from the north-south axis"],
    },
    {
        "id": "attr-forbidden-city",
        "name": "Forbidden City",
        "aliases": ["Palace Museum", "Imperial Palace"],
        "category": "museum",
        "latitude": 39.9163,
        "longitude": 116.3972,
        "recommended_duration_minutes": 180,
        "tags": ["imperial", "history", "museum"],
        "short_intro": "The imperial palace complex of the Ming and Qing dynasties and one of Beijing’s signature cultural sites.",
        "history": "It was the political and ceremonial center of imperial China for centuries.",
        "highlights": ["imperial architecture", "palace courtyards", "dynastic history"],
        "visitor_tips": ["Reserve enough time for multiple halls", "Morning visits are usually easier to pace"],
        "practical_notes": ["Large walking distance inside the complex", "Timed-entry planning may matter"],
        "family_friendly_notes": ["Choose fewer halls if traveling with children"],
        "photo_spot_notes": ["Gate and courtyard symmetry works well for photos"],
    },
    {
        "id": "attr-jingshan-park",
        "name": "Jingshan Park",
        "aliases": ["Jingshan", "Coal Hill Park"],
        "category": "park",
        "latitude": 39.9240,
        "longitude": 116.3967,
        "recommended_duration_minutes": 60,
        "tags": ["views", "park", "sunset"],
        "short_intro": "A hilltop park known for panoramic views over central Beijing and the Forbidden City.",
        "history": "The hill was formed from earth removed during the construction of the palace moat.",
        "highlights": ["panoramic city view", "Forbidden City overlook", "easy scenic stop"],
        "visitor_tips": ["Best combined with the Forbidden City", "Useful for sunset views on clear days"],
        "practical_notes": ["Some uphill walking is required", "Short scenic visit works well late in the route"],
        "family_friendly_notes": ["Keep the stop short if children are tired"],
        "photo_spot_notes": ["Best skyline view near the summit platform"],
    },
    {
        "id": "attr-temple-of-heaven",
        "name": "Temple of Heaven",
        "aliases": ["Tiantan", "Heaven Temple"],
        "category": "park",
        "latitude": 39.8837,
        "longitude": 116.4120,
        "recommended_duration_minutes": 120,
        "tags": ["ritual", "architecture", "park"],
        "short_intro": "A major ceremonial complex where emperors once performed rites connected to harvest and heaven worship.",
        "history": "It reflects imperial ritual life and ceremonial cosmology from the Ming and Qing eras.",
        "highlights": ["Hall of Prayer for Good Harvests", "ritual architecture", "park atmosphere"],
        "visitor_tips": ["Leave enough time for both architecture and park paths", "Works well in a slower-paced route"],
        "practical_notes": ["The park area is broad, so route pacing matters", "Entry queues may vary by time of day"],
        "family_friendly_notes": ["Open park areas are easier for family breaks"],
        "photo_spot_notes": ["The Hall of Prayer is the most iconic photo point"],
    },
    {
        "id": "attr-summer-palace",
        "name": "Summer Palace",
        "aliases": ["Yiheyuan"],
        "category": "park",
        "latitude": 39.9996,
        "longitude": 116.2755,
        "recommended_duration_minutes": 210,
        "tags": ["lake", "garden", "imperial"],
        "short_intro": "A vast imperial garden complex centered on Kunming Lake and long scenic walkways.",
        "history": "It served as an imperial retreat and showcases Qing-era garden design.",
        "highlights": ["Kunming Lake", "Long Corridor", "garden landscapes"],
        "visitor_tips": ["Best for travelers who enjoy slower scenic routes", "Plan breaks because the site is extensive"],
        "practical_notes": ["Walking distance can be significant", "Boat and shoreline areas change pacing"],
        "family_friendly_notes": ["Good for relaxed family sightseeing if time is available"],
        "photo_spot_notes": ["Lake-edge and corridor sections offer varied compositions"],
    },
]

_INTEREST_ROTATIONS = [
    ["history", "culture"],
    ["photography", "views"],
    ["family", "relaxed"],
    ["architecture", "walking"],
    ["food", "light_exploration"],
]

_TRAVEL_STYLES = ["balanced", "relaxed", "focused", "scenic"]
_WALKING_PREFERENCES = ["light", "moderate", "high"]
_AUDIENCE_TYPES = ["general", "family", "solo", "couple"]
_ANSWER_LENGTHS = ["short", "medium", "long"]
_LANGUAGES = ["en", "zh", "es"]
_GUIDE_STYLES = ["NF", "NT", "SJ", "SP"]


def build_mock_seed_bundle(attraction_count: int = 50, profile_count: int = 50) -> MockSeedBundle:
    attractions: list[AttractionContext] = []
    for index in range(attraction_count):
        base = _BASE_ATTRACTIONS[index % len(_BASE_ATTRACTIONS)]
        suffix = index + 1
        attractions.append(
            AttractionContext(
                id=f"{base['id']}-{suffix}",
                name=base["name"] if index < len(_BASE_ATTRACTIONS) else f"{base['name']} {suffix}",
                aliases=[*base["aliases"], f"{base['name']} Tour Variant {suffix}"],
                category=base["category"],
                latitude=base["latitude"],
                longitude=base["longitude"],
                recommended_duration_minutes=base["recommended_duration_minutes"],
                tags=[*base["tags"], f"variant-{suffix}"],
                short_intro=base["short_intro"],
                history=base["history"],
                highlights=base["highlights"],
                visitor_tips=base["visitor_tips"],
                practical_notes=base["practical_notes"],
                family_friendly_notes=base["family_friendly_notes"],
                photo_spot_notes=base["photo_spot_notes"],
                source="mock_postgres",
            )
        )

    profiles: list[ProfileContext] = []
    for index in range(profile_count):
        profiles.append(
            ProfileContext(
                user_id=f"mock-user-{index + 1}",
                preferred_language=_LANGUAGES[index % len(_LANGUAGES)],
                interests=_INTEREST_ROTATIONS[index % len(_INTEREST_ROTATIONS)],
                travel_style=_TRAVEL_STYLES[index % len(_TRAVEL_STYLES)],
                walking_preference=_WALKING_PREFERENCES[index % len(_WALKING_PREFERENCES)],
                pace_preference=_TRAVEL_STYLES[index % len(_TRAVEL_STYLES)],
                audience_type=_AUDIENCE_TYPES[index % len(_AUDIENCE_TYPES)],
                answer_length_preference=_ANSWER_LENGTHS[index % len(_ANSWER_LENGTHS)],
                guide_style_preference=_GUIDE_STYLES[index % len(_GUIDE_STYLES)],
                source="mock_postgres",
            )
        )

    return MockSeedBundle(attractions=attractions, profiles=profiles)


MOCK_SEED_BUNDLE = build_mock_seed_bundle()
