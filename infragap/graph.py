import logging
from collections import defaultdict

import networkx as nx
from shapely import STRtree
from shapely.geometry import Point
from shapely.ops import transform as shapely_transform

from infragap.crs import get_length_meters

logger = logging.getLogger(__name__)


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            next_x = self.parent[x]
            self.parent[x] = root
            x = next_x
        return root

    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            self.parent[root_x] = root_y


def build_graph(lines, tolerance, transformer, strategies=None):
    """
    Build a networkx graph from LineStrings by snapping nearby endpoints.
    Uses three merge strategies: endpoint-endpoint, T-junctions, overlaps.
    All distance checks use UTM projection (meters).

    lines: list of (LineString, properties) from load_geojson
    tolerance: max distance in meters to merge endpoints
    transformer: pyproj transformer for length calculation
    strategies: set of enabled clustering strategies. Any subset of
        {"endpoints", "tjunctions", "overlaps"}. Default: all three.
    """
    if strategies is None:
        strategies = {"endpoints", "tjunctions", "overlaps"}

    line_geoms = [line for line, _ in lines]
    n = len(lines)

    line_geoms_utm = [shapely_transform(transformer.transform, g) for g in line_geoms]

    endpoints_utm = []
    endpoint_coords = []
    for i in range(n):
        start_utm = Point(line_geoms_utm[i].coords[0])
        end_utm = Point(line_geoms_utm[i].coords[-1])
        endpoints_utm.append((start_utm, i))
        endpoints_utm.append((end_utm, i))
        endpoint_coords.append(line_geoms[i].coords[0])
        endpoint_coords.append(line_geoms[i].coords[-1])

    ep_points_utm = [pt for pt, _ in endpoints_utm]
    ep_tree = STRtree(ep_points_utm)
    line_tree = STRtree(line_geoms_utm)

    logger.debug("Collected %d endpoints from %d lines", len(endpoints_utm), n)

    line_parent = list(range(n))

    def line_find(x):
        while line_parent[x] != x:
            line_parent[x] = line_parent[line_parent[x]]
            x = line_parent[x]
        return x

    def line_union(x, y):
        px, py = line_find(x), line_find(y)
        if px != py:
            line_parent[px] = py

    ep_merges = 0
    if "endpoints" in strategies:
        for i, (pt, line_i) in enumerate(endpoints_utm):
            nearby = ep_tree.query(pt.buffer(tolerance), predicate="intersects")
            for j in nearby:
                if j != i:
                    _, line_j = endpoints_utm[j]
                    if line_i != line_j and line_find(line_i) != line_find(line_j):
                        if ep_points_utm[i].distance(ep_points_utm[j]) <= tolerance:
                            line_union(line_i, line_j)
                            ep_merges += 1

    logger.debug("Endpoint-to-endpoint merges: %d", ep_merges)

    tj_merges = 0
    if "tjunctions" in strategies:
        for pt, line_i in endpoints_utm:
            nearby_lines = line_tree.query(pt.buffer(tolerance), predicate="intersects")
            for line_j in nearby_lines:
                if line_i != line_j and line_find(line_i) != line_find(line_j):
                    dist = line_geoms_utm[line_j].distance(pt)
                    if dist <= tolerance:
                        line_union(line_i, line_j)
                        tj_merges += 1

    logger.debug("T-junction merges: %d", tj_merges)

    overlap_merges = 0
    if "overlaps" in strategies:
        for i in range(n):
            nearby = line_tree.query(line_geoms_utm[i].buffer(tolerance), predicate="intersects")
            for j in nearby:
                if i < j and line_find(i) != line_find(j):
                    if line_geoms_utm[i].intersects(line_geoms_utm[j]):
                        line_union(i, j)
                        overlap_merges += 1

    logger.debug("Overlapping line merges: %d", overlap_merges)

    clusters = defaultdict(list)
    for i in range(n):
        clusters[line_find(i)].append(i)

    logger.debug("Found %d clusters", len(clusters))

    uf = UnionFind()

    for i, (pt, line_i) in enumerate(endpoints_utm):
        nearby = ep_tree.query(pt.buffer(tolerance), predicate="intersects")
        for j in nearby:
            if j != i:
                _, line_j = endpoints_utm[j]
                if line_find(line_i) == line_find(line_j):
                    if ep_points_utm[i].distance(ep_points_utm[j]) <= tolerance:
                        uf.union(endpoint_coords[i], endpoint_coords[j])

    if "tjunctions" in strategies:
        for i, (pt, line_i) in enumerate(endpoints_utm):
            nearby_lines = line_tree.query(pt.buffer(tolerance), predicate="intersects")
            for j in nearby_lines:
                if line_i != j and line_find(line_i) == line_find(j):
                    dist = line_geoms_utm[j].distance(pt)
                    if dist <= tolerance:
                        start_j_utm = Point(line_geoms_utm[j].coords[0])
                        end_j_utm = Point(line_geoms_utm[j].coords[-1])
                        if pt.distance(start_j_utm) <= pt.distance(end_j_utm):
                            uf.union(endpoint_coords[i], line_geoms[j].coords[0])
                        else:
                            uf.union(endpoint_coords[i], line_geoms[j].coords[-1])

    G = nx.Graph()
    line_nodes = []
    total_length_all = 0

    for i, (line, props) in enumerate(lines):
        start = line.coords[0]
        end = line.coords[-1]
        node_a = uf.find(start)
        node_b = uf.find(end)
        length_m = get_length_meters(line, transformer)
        total_length_all += length_m
        line_nodes.append((node_a, node_b))

        if node_a == node_b:
            if not G.has_node(node_a):
                G.add_node(node_a, self_loop_m=0)
            G.nodes[node_a]["self_loop_m"] = G.nodes[node_a].get("self_loop_m", 0) + length_m
            continue

        if G.has_edge(node_a, node_b):
            G[node_a][node_b]["length_m"] += length_m
        else:
            G.add_edge(node_a, node_b, length_m=length_m)

    G.graph["total_length_all_m"] = total_length_all
    G.graph["line_nodes"] = line_nodes

    for cluster_line_ids in clusters.values():
        if len(cluster_line_ids) <= 1:
            continue

        cluster_nodes = set()
        for i in cluster_line_ids:
            na, nb = line_nodes[i]
            if G.has_node(na):
                cluster_nodes.add(na)
            if G.has_node(nb):
                cluster_nodes.add(nb)

        if len(cluster_nodes) < 2:
            continue

        sub = G.subgraph(list(cluster_nodes))
        sub_comps = list(nx.connected_components(sub))

        if len(sub_comps) > 1:
            first_node = next(iter(sub_comps[0]))
            for k in range(1, len(sub_comps)):
                other_node = next(iter(sub_comps[k]))
                G.add_edge(first_node, other_node, length_m=0)

    logger.info(
        "Built graph: %d nodes, %d edges, %d components",
        G.number_of_nodes(),
        G.number_of_edges(),
        nx.number_connected_components(G),
    )

    return G
