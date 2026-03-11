from shapely.geometry import LineString
from infragap.crs import detect_crs, get_length_meters


def test_northern_hemisphere():
    """Milan (lon=9.19, lat=45.46) → UTM zone 32N → EPSG:32632."""
    t = detect_crs(9.19, 45.46)
    assert t.target_crs.to_epsg() == 32632


def test_southern_hemisphere():
    """São Paulo (lon=-46.63, lat=-23.55) → UTM zone 23S → EPSG:32723."""
    t = detect_crs(-46.63, -23.55)
    assert t.target_crs.to_epsg() == 32723


def test_negative_longitude():
    """New York (lon=-74, lat=40.7) → UTM zone 18N → EPSG:32618."""
    t = detect_crs(-74, 40.7)
    assert t.target_crs.to_epsg() == 32618


def test_boundary_longitude_180():
    """lon=180 should give zone 60, not 61."""
    t = detect_crs(180, 45)
    assert t.target_crs.to_epsg() == 32660


def test_source_is_wgs84():
    """Transformer source should always be WGS 84."""
    t = detect_crs(9.19, 45.46)
    assert "WGS 84" in t.source_crs.name


def test_get_length_meters():
    """A ~780m line near Milan should have a reasonable projected length."""
    t = detect_crs(9.19, 45.46)
    line = LineString([(9.19, 45.46), (9.20, 45.46)])
    length = get_length_meters(line, t)
    # 0.01° longitude at lat 45.46° ≈ 786m
    assert 700 < length < 900
