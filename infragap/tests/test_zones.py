import json
import os
import tempfile
import networkx as nx
import pytest
from infragap.crs import detect_crs
from infragap.zones import overlay


@pytest.fixture
def transformer():
    return detect_crs(9.19, 45.46)


@pytest.fixture
def simple_graph():
    """Graph with two edges near (9.19, 45.46)."""
    G = nx.Graph()
    G.add_edge((9.19, 45.46), (9.191, 45.46), length_m=100)
    G.add_edge((9.191, 45.46), (9.192, 45.46), length_m=100)
    G.graph["total_length_all_m"] = 200
    return G


def _make_zone_geojson(zones):
    features = []
    for name, coords in zones:
        features.append({
            "type": "Feature",
            "properties": {"name": name},
            "geometry": {"type": "Polygon", "coordinates": [coords]},
        })
    collection = {"type": "FeatureCollection", "features": features}
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".geojson", delete=False)
    json.dump(collection, tmp)
    tmp.close()
    return tmp.name


def test_overlay_single_zone(simple_graph, transformer):
    """All edges fall inside a single large zone."""
    coords = [
        [9.18, 45.45], [9.20, 45.45], [9.20, 45.47],
        [9.18, 45.47], [9.18, 45.45],
    ]
    path = _make_zone_geojson([("center", coords)])
    df, geoms = overlay(simple_graph, path, "name", transformer)
    os.unlink(path)

    assert len(df) == 1
    assert df.iloc[0]["name"] == "center"
    assert df.iloc[0]["num_components"] >= 1
    assert df.iloc[0]["length_km"] > 0


def test_overlay_empty_zone(simple_graph, transformer):
    """Zone far from the graph → zeros."""
    coords = [
        [10.0, 46.0], [10.1, 46.0], [10.1, 46.1],
        [10.0, 46.1], [10.0, 46.0],
    ]
    path = _make_zone_geojson([("empty", coords)])
    df, geoms = overlay(simple_graph, path, "name", transformer)
    os.unlink(path)

    assert len(df) == 1
    assert df.iloc[0]["length_km"] == 0
    assert df.iloc[0]["lcc_ratio"] == 0
    assert df.iloc[0]["stranded_pct"] == 100.0


def test_overlay_multiple_zones(simple_graph, transformer):
    """Two zones: one covering the graph, one empty."""
    zone_a = [
        [9.18, 45.45], [9.20, 45.45], [9.20, 45.47],
        [9.18, 45.47], [9.18, 45.45],
    ]
    zone_b = [
        [10.0, 46.0], [10.1, 46.0], [10.1, 46.1],
        [10.0, 46.1], [10.0, 46.0],
    ]
    path = _make_zone_geojson([("has_infra", zone_a), ("no_infra", zone_b)])
    df, geoms = overlay(simple_graph, path, "name", transformer)
    os.unlink(path)

    assert len(df) == 2
    row_a = df[df["name"] == "has_infra"].iloc[0]
    row_b = df[df["name"] == "no_infra"].iloc[0]
    assert row_a["length_km"] > 0
    assert row_b["length_km"] == 0


def test_overlay_returns_geometries(simple_graph, transformer):
    """Returned geometries dict should contain zone polygons."""
    coords = [
        [9.18, 45.45], [9.20, 45.45], [9.20, 45.47],
        [9.18, 45.47], [9.18, 45.45],
    ]
    path = _make_zone_geojson([("test_zone", coords)])
    df, geoms = overlay(simple_graph, path, "name", transformer)
    os.unlink(path)

    assert "test_zone" in geoms
    assert geoms["test_zone"].geom_type == "Polygon"


def test_overlay_density(simple_graph, transformer):
    """Density should be a positive number for a zone with infrastructure."""
    coords = [
        [9.18, 45.45], [9.20, 45.45], [9.20, 45.47],
        [9.18, 45.47], [9.18, 45.45],
    ]
    path = _make_zone_geojson([("zone", coords)])
    df, geoms = overlay(simple_graph, path, "name", transformer)
    os.unlink(path)

    assert df.iloc[0]["density"] > 0
