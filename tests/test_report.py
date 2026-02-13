import json
import pandas as pd
from infragap.report import Report, ZoneReport


def _make_metrics():
    return {
        "num_nodes": 100,
        "num_edges": 120,
        "total_length_m": 50000,
        "total_length_km": 50.0,
        "num_components": 5,
        "component_lengths_m": [30000, 10000, 5000, 3000, 2000],
        "lcc_length_m": 30000,
        "lcc_length_km": 30.0,
        "lcc_ratio": 0.6,
        "stranded_pct": 40.0,
        "avg_component_length_m": 10000,
        "beta": 1.2,
        "alpha": 0.15,
        "gamma": 0.41,
        "bridges": 30,
        "bridge_list": [],
        "edge_connectivity": 2,
    }


def test_report_str():
    r = Report(_make_metrics(), segments=200)
    text = str(r)
    assert "50.0 km" in text
    assert "200" in text
    assert "Bridges" in text
    assert "Connectivity" in text


def test_report_attributes():
    r = Report(_make_metrics(), segments=200)
    assert r.total_length_km == 50.0
    assert r.segments == 200
    assert r.components == 5
    assert r.lcc_ratio == 0.6
    assert r.stranded_pct == 40.0
    assert r.beta == 1.2
    assert r.alpha == 0.15
    assert r.gamma == 0.41
    assert r.bridges == 30
    assert r.edge_connectivity == 2


def test_report_to_dict():
    r = Report(_make_metrics(), segments=200)
    d = r.to_dict()
    assert d["segments"] == 200
    assert d["total_length_km"] == 50.0
    # Internal lists should be stripped
    assert "bridge_list" not in d
    assert "component_lengths_m" not in d


def test_report_to_json():
    r = Report(_make_metrics(), segments=200)
    j = r.to_json()
    parsed = json.loads(j)
    assert parsed["segments"] == 200
    assert parsed["lcc_ratio"] == 0.6


def test_report_to_dataframe():
    r = Report(_make_metrics(), segments=200)
    df = r.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df["segments"].iloc[0] == 200


def test_zone_report_str():
    df = pd.DataFrame([
        {"zone": "A", "length_km": 10, "lcc_ratio": 0.8},
        {"zone": "B", "length_km": 5, "lcc_ratio": 0.5},
    ])
    zr = ZoneReport(df)
    text = str(zr)
    assert "A" in text
    assert "B" in text


def test_zone_report_repr():
    df = pd.DataFrame([{"zone": "X", "value": 1}])
    zr = ZoneReport(df)
    assert "X" in repr(zr)
