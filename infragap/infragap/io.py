import json
import logging
from shapely.geometry import shape

logger = logging.getLogger(__name__)


def load_geojson(path):
    with open(path) as f:
        data = json.load(f)
    results = []
    for feature in data["features"]:
        try:
            geom = shape(feature["geometry"])
        except Exception:
            continue
        props = feature["properties"]
        if geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                if len(line.coords) < 2:
                    continue
                results.append((line, props))
        elif geom.geom_type == "LineString":
            if len(geom.coords) < 2:
                continue
            results.append((geom, props))
    logger.info("Loaded %d features from %s", len(results), path)
    return results
