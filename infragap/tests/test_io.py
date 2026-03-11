import json
import os
import tempfile
from infragap.io import load_geojson


def _make_geojson(features):
    collection = {"type": "FeatureCollection", "features": features}
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".geojson", delete=False)
    json.dump(collection, tmp)
    tmp.close()
    return tmp.name


def test_load_linestrings():
    features = [
        {
            "type": "Feature",
            "properties": {"name": "road_a"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.1, 45.4], [9.2, 45.5]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "road_b"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.2, 45.5], [9.3, 45.6]],
            },
        },
    ]
    path = _make_geojson(features)
    results = load_geojson(path)
    os.unlink(path)

    assert len(results) == 2
    assert results[0][0].geom_type == "LineString"
    assert results[0][1]["name"] == "road_a"


def test_load_multilinestring():
    features = [
        {
            "type": "Feature",
            "properties": {"name": "multi"},
            "geometry": {
                "type": "MultiLineString",
                "coordinates": [
                    [[9.1, 45.4], [9.2, 45.5]],
                    [[9.3, 45.6], [9.4, 45.7]],
                ],
            },
        }
    ]
    path = _make_geojson(features)
    results = load_geojson(path)
    os.unlink(path)

    assert len(results) == 2
    assert results[0][0].geom_type == "LineString"
    assert results[1][0].geom_type == "LineString"
    assert results[0][1]["name"] == "multi"
    assert results[1][1]["name"] == "multi"


def test_skip_short_geometries():
    features = [
        {
            "type": "Feature",
            "properties": {"name": "good"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.1, 45.4], [9.2, 45.5]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "bad"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.1, 45.4]],
            },
        },
    ]
    path = _make_geojson(features)
    results = load_geojson(path)
    os.unlink(path)

    assert len(results) == 1
    assert results[0][1]["name"] == "good"
