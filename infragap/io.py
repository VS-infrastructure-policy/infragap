import json
from shapely.geometry import shape


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
    print(f"Loaded file from {path}")
    return results
