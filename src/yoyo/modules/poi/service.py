from yoyo.modules.poi.catalog import POI_CATALOG


def get_poi_info(name: str | None) -> dict[str, object] | None:
    if name is None:
        return None
    return POI_CATALOG.get(name)
