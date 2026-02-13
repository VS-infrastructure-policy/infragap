import pytest
import networkx as nx
from shapely.geometry import LineString
from infragap.crs import detect_crs
from infragap.graph import build_graph, UnionFind


@pytest.fixture
def transformer():
    return detect_crs(9.19, 45.46)


# --- UnionFind unit tests ---


def test_union_find_merge():
    """Union-Find correctly groups connected elements."""
    uf = UnionFind()
    uf.union("a", "b")
    uf.union("b", "c")
    assert uf.find("a") == uf.find("c")


def test_union_find_separate():
    """Unconnected elements stay in separate sets."""
    uf = UnionFind()
    uf.union("a", "b")
    assert uf.find("a") != uf.find("d")


# --- build_graph tests ---

# Coordinates near Milan (lon ~9.19, lat ~45.46)
# At this latitude: 1° lon ≈ 78km, 1° lat ≈ 111km
# So 5m ≈ 0.000064° lon


def test_exact_shared_endpoint(transformer):
    """Two lines sharing an exact endpoint → 1 component."""
    lines = [
        (LineString([(9.19, 45.46), (9.191, 45.46)]), {}),
        (LineString([(9.191, 45.46), (9.192, 45.46)]), {}),
    ]
    G = build_graph(lines, tolerance=5, transformer=transformer)
    assert nx.number_connected_components(G) == 1
    assert G.number_of_nodes() == 3
    assert G.number_of_edges() == 2


def test_endpoints_within_tolerance(transformer):
    """Two lines with a ~1m gap → snapped → 1 component."""
    lines = [
        (LineString([(9.19, 45.46), (9.191, 45.46)]), {}),
        (LineString([(9.1910001, 45.46), (9.192, 45.46)]), {}),
    ]
    G = build_graph(lines, tolerance=5, transformer=transformer)
    assert nx.number_connected_components(G) == 1


def test_endpoints_beyond_tolerance(transformer):
    """Two lines far apart → 2 components."""
    lines = [
        (LineString([(9.19, 45.46), (9.191, 45.46)]), {}),
        (LineString([(9.20, 45.47), (9.201, 45.47)]), {}),
    ]
    G = build_graph(lines, tolerance=5, transformer=transformer)
    assert nx.number_connected_components(G) == 2


def test_t_junction(transformer):
    """Endpoint of one line near interior of another → 1 component."""
    lines = [
        (LineString([(9.19, 45.46), (9.192, 45.46)]), {}),
        (LineString([(9.191, 45.46), (9.191, 45.461)]), {}),
    ]
    G = build_graph(lines, tolerance=5, transformer=transformer)
    assert nx.number_connected_components(G) == 1


def test_parallel_lines_not_merged(transformer):
    """Two parallel lines 50m apart should NOT be merged."""
    # 50m ≈ 0.00064° longitude at lat 45.46
    lines = [
        (LineString([(9.19, 45.46), (9.192, 45.46)]), {}),
        (LineString([(9.19, 45.46005), (9.192, 45.46005)]), {}),
    ]
    G = build_graph(lines, tolerance=5, transformer=transformer)
    assert nx.number_connected_components(G) == 2


def test_single_line(transformer):
    """A single line → 2 nodes, 1 edge, 1 component."""
    lines = [
        (LineString([(9.19, 45.46), (9.191, 45.46)]), {}),
    ]
    G = build_graph(lines, tolerance=5, transformer=transformer)
    assert G.number_of_nodes() == 2
    assert G.number_of_edges() == 1
    assert nx.number_connected_components(G) == 1


def test_total_length_stored(transformer):
    """Graph should store total length as a graph attribute."""
    lines = [
        (LineString([(9.19, 45.46), (9.191, 45.46)]), {}),
        (LineString([(9.191, 45.46), (9.192, 45.46)]), {}),
    ]
    G = build_graph(lines, tolerance=5, transformer=transformer)
    assert G.graph["total_length_all_m"] > 0


def test_edge_length_attribute(transformer):
    """Each edge should have a length_m attribute."""
    lines = [
        (LineString([(9.19, 45.46), (9.191, 45.46)]), {}),
    ]
    G = build_graph(lines, tolerance=5, transformer=transformer)
    for u, v, data in G.edges(data=True):
        assert "length_m" in data
        assert data["length_m"] > 0
