import networkx as nx
from infragap.metrics import compute_metrics


def test_empty_graph():
    """Graph with no nodes or edges."""
    G = nx.Graph()
    m = compute_metrics(G)
    assert m["num_nodes"] == 0
    assert m["num_edges"] == 0
    assert m["num_components"] == 0
    assert m["lcc_ratio"] == 0


def test_single_node():
    """Graph with one node, no edges."""
    G = nx.Graph()
    G.add_node(0)
    m = compute_metrics(G)
    assert m["num_nodes"] == 1
    assert m["num_components"] == 1
    assert m["bridges"] == 0
    assert m["beta"] == 0


def test_single_edge():
    """Graph with one edge → 1 bridge, beta < 1."""
    G = nx.Graph()
    G.add_edge(0, 1, length_m=500)
    m = compute_metrics(G)
    assert m["num_nodes"] == 2
    assert m["num_edges"] == 1
    assert m["bridges"] == 1
    assert m["total_length_m"] == 500
    assert m["lcc_ratio"] == 1.0


def test_k5_metrics(k5_graph):
    m = compute_metrics(k5_graph)
    assert m["num_nodes"] == 5
    assert m["num_edges"] == 10
    assert m["num_components"] == 1
    assert m["beta"] == 2.0
    assert m["alpha"] == 1.0
    assert m["gamma"] == 1.0
    assert m["bridges"] == 0


def test_path_metrics(path_graph):
    m = compute_metrics(path_graph)
    assert m["num_nodes"] == 5
    assert m["num_edges"] == 4
    assert m["num_components"] == 1
    assert m["beta"] == 0.8
    assert m["alpha"] == 0.0
    assert m["bridges"] == 4


def test_two_triangles_metrics(two_triangles):
    m = compute_metrics(two_triangles)
    assert m["num_components"] == 2
    assert m["total_length_m"] == 600
    assert m["lcc_ratio"] == 0.5
    assert m["bridges"] == 0


def test_star_metrics(star_graph):
    m = compute_metrics(star_graph)
    assert m["num_nodes"] == 5
    assert m["num_edges"] == 4
    assert m["num_components"] == 1
    assert m["bridges"] == 4
