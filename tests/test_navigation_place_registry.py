from yoyo.modules.knowledge.place_resolver import (
    CORE_NAVIGATION_PLACES,
    REGISTERED_NAVIGATION_PLACES,
    VISITBEIJING_NAVIGATION_PLACES,
    place_text_has_ambiguity_signal,
    resolve_navigation_place,
)


def test_visitbeijing_navigation_registry_is_loaded() -> None:
    assert len(CORE_NAVIGATION_PLACES) == 20
    assert len(VISITBEIJING_NAVIGATION_PLACES) == 127
    assert len(REGISTERED_NAVIGATION_PLACES) == 147


def test_visitbeijing_registry_resolves_high_confidence_places() -> None:
    place = resolve_navigation_place("齐白石旧居纪念馆")

    assert place is not None
    assert place.place_id == "visitbeijing_120983"
    assert place.display_name == "齐白石旧居纪念馆"
    assert place.source == "registry"
    assert place.latitude == 39.935745
    assert place.longitude == 116.401518


def test_core_registry_still_wins_for_known_tourism_aliases() -> None:
    place = resolve_navigation_place("正阳门")

    assert place is not None
    assert place.place_id == "zhengyangmen"
    assert place.display_name == "正阳门"
    assert place.confidence == 1.0


def test_registered_alias_with_commercial_signal_requires_clarification() -> None:
    place = resolve_navigation_place("正阳门餐厅")

    assert place is not None
    assert place.source == "geocode_candidate"
    assert place.confidence == 0.46
    assert place.reason == "registered_alias_with_ambiguity_signal"
    assert place_text_has_ambiguity_signal("正阳门北京环球金融中心")


def test_low_confidence_visitbeijing_candidates_are_not_registered() -> None:
    for name in ["御花园", "文昌帝君庙", "王府井小吃街"]:
        place = resolve_navigation_place(name)
        assert place is not None
        assert place.source == "geocode_candidate"
        assert place.confidence == 0.45


def test_generated_registry_does_not_create_suffix_stripped_aliases() -> None:
    place = resolve_navigation_place("史家胡同")

    assert place is not None
    assert place.source == "geocode_candidate"
