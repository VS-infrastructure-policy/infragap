import json
import os
import tempfile
import pytest
from infragap import from_file


def _make_geojson(features):
    collection = {"type": "FeatureCollection", "features": features}
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".geojson", delete=False)
    json.dump(collection, tmp)
    tmp.close()
    return tmp.name


def test_from_file_connected():
    """Two connected segments → 1 component, positive length."""
    features = [
        {
            "type": "Feature",
            "properties": {"name": "a"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.19, 45.46], [9.191, 45.46]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "b"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.191, 45.46], [9.192, 45.46]],
            },
        },
    ]
    path = _make_geojson(features)
    net = from_file(path)
    os.unlink(path)

    assert net.segments == 2
    report = net.diagnose()
    assert report.components == 1
    assert report.total_length_km > 0
    assert report.lcc_ratio == 1.0


def test_from_file_disconnected():
    """Two far-apart segments → 2 components."""
    features = [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.19, 45.46], [9.191, 45.46]],
            },
        },
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.30, 45.50], [9.301, 45.50]],
            },
        },
    ]
    path = _make_geojson(features)
    net = from_file(path)
    os.unlink(path)

    report = net.diagnose()
    assert report.components == 2
    assert report.lcc_ratio == pytest.approx(0.5, abs=0.05)


def test_from_file_empty_raises():
    """File with only Point geometries → no valid lines → ValueError."""
    features = [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Point", "coordinates": [9.19, 45.46]},
        },
    ]
    path = _make_geojson(features)
    with pytest.raises(ValueError):
        from_file(path)
    os.unlink(path)


def test_network_attributes():
    """Network exposes expected attributes after construction."""
    features = [
        {
            "type": "Feature",
            "properties": {"name": "test"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.19, 45.46], [9.191, 45.46]],
            },
        },
    ]
    path = _make_geojson(features)
    net = from_file(path)

    assert net.segments == 1
    assert net.tolerance == 5
    assert net.path == path
    assert net.transformer is not None
    assert net.graph is not None
    assert len(net.lines) == 1
    os.unlink(path)


def test_network_bridges():
    """A path of 2 edges has 2 bridge edges."""
    features = [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.19, 45.46], [9.191, 45.46]],
            },
        },
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.191, 45.46], [9.192, 45.46]],
            },
        },
    ]
    path = _make_geojson(features)
    net = from_file(path)
    os.unlink(path)

    bridges = net.bridges()
    assert len(bridges) == 2


def test_report_exports():
    """Report export methods should return the right types."""
    features = [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.19, 45.46], [9.191, 45.46]],
            },
        },
    ]
    path = _make_geojson(features)
    net = from_file(path)
    os.unlink(path)

    report = net.diagnose()
    assert isinstance(report.to_dict(), dict)
    assert isinstance(report.to_json(), str)
    assert len(report.to_dataframe()) == 1
