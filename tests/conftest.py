import pytest
import networkx as nx


@pytest.fixture
def k5_graph():
    """Complete graph K5."""
    G = nx.complete_graph(5)
    for u, v in G.edges():
        G[u][v]["length_m"] = 100
    return G


@pytest.fixture
def path_graph():
    """Path graph P5."""
    G = nx.path_graph(5)
    for u, v in G.edges():
        G[u][v]["length_m"] = 100
    return G


@pytest.fixture
def two_triangles():
    """Two disconnected triangles."""
    G = nx.Graph()
    G.add_edge(0, 1, length_m=100)
    G.add_edge(1, 2, length_m=100)
    G.add_edge(2, 0, length_m=100)
    G.add_edge(3, 4, length_m=100)
    G.add_edge(4, 5, length_m=100)
    G.add_edge(5, 3, length_m=100)
    return G


@pytest.fixture
def star_graph():
    """Star graph S5."""
    G = nx.star_graph(4)
    for u, v in G.edges():
        G[u][v]["length_m"] = 100
    return G
