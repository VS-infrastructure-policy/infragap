import json
import networkx as nx
import pandas as pd
from shapely.geometry import shape, LineString
from shapely import STRtree
from shapely.ops import transform
from infragap.metrics import compute_metrics


def overlay(G, zones_path, name_col, transformer):
    """
    Compute per-zone metrics by overlaying the network with zone boundaries.

    G: networkx graph from build_graph
    zones_path: path to GeoJSON file with zone polygons
    name_col: property name for zone identifier (e.g. "NIL")
    transformer: pyproj transformer for area calculation

    Note: edges are represented as straight lines between their endpoint nodes.
    Original line curvature is not preserved in the graph, so the spatial
    intersection with zone boundaries is approximate.
    """

    with open(zones_path) as f:
        zone_data = json.load(f)

    zones = []
    geometries = {}
    for feature in zone_data["features"]:
        geom = shape(feature["geometry"])
        name = feature["properties"][name_col]
        zones.append((name, geom))
        geometries[name] = geom

    print(f"Loaded {len(zones)} zones from {zones_path}")

    edge_lines = []
    edge_data = []
    for u, v, data in G.edges(data=True):
        line = LineString([u, v])
        edge_lines.append(line)
        edge_data.append((u, v, data))

    tree = STRtree(edge_lines)

    rows = []
    for zone_name, zone_geom in zones:
        nearby = tree.query(zone_geom, predicate="intersects")

        if len(nearby) == 0:
            rows.append({
                name_col: zone_name,
                "length_km": 0,
                "lcc_ratio": 0,
                "stranded_pct": 100.0,
                "num_components": 0,
                "density": 0,
                "bridges": 0,
            })
            continue

        sub = nx.Graph()
        for idx in nearby:
            u, v, data = edge_data[idx]
            sub.add_edge(u, v, length_m=data["length_m"])

        if sub.number_of_edges() == 0:
            rows.append({
                name_col: zone_name,
                "length_km": 0,
                "lcc_ratio": 0,
                "stranded_pct": 100.0,
                "num_components": 0,
                "density": 0,
                "bridges": 0,
            })
            continue

        zone_metrics = compute_metrics(sub)

        projected_zone = transform(transformer.transform, zone_geom)
        area_km2 = projected_zone.area / 1_000_000

        if area_km2 > 0:
            density = zone_metrics["total_length_km"] / area_km2
        else:
            density = 0

        rows.append({
            name_col: zone_name,
            "length_km": zone_metrics["total_length_km"],
            "lcc_ratio": zone_metrics["lcc_ratio"],
            "stranded_pct": zone_metrics["stranded_pct"],
            "num_components": zone_metrics["num_components"],
            "density": round(density, 2),
            "bridges": zone_metrics["bridges"],
        })

    df = pd.DataFrame(rows)
    return df, geometries
