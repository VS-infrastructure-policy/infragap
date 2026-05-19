import json
import logging
from collections import defaultdict

import networkx as nx
import pandas as pd
from shapely import STRtree
from shapely.geometry import LineString, shape
from shapely.ops import transform

from infragap.metrics import compute_metrics

logger = logging.getLogger(__name__)


def overlay(G, zones_path, name_col, transformer, lines=None, line_components=None):
    """
    Compute per-zone metrics by overlaying the network with zone boundaries.

    G: networkx graph from build_graph
    zones_path: path to GeoJSON file with zone polygons
    name_col: property name for zone identifier (e.g. "NIL")
    transformer: pyproj transformer for length/area calculation
    lines: list of (LineString, properties) from load_geojson (recommended).
           When provided with line_components, uses original curved geometries
           and clips them to zone boundaries for accurate length calculation.
    line_components: list of int, component id for each line in lines.
           Required when lines is provided.

    If lines/line_components are omitted, falls back to straight-line graph
    edges between endpoint nodes, which is less accurate near zone boundaries.
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

    logger.info("Loaded %d zones from %s", len(zones), zones_path)

    if lines is not None and line_components is not None:
        rows = _overlay_geometry(zones, name_col, transformer, lines, line_components)
    else:
        rows = _overlay_graph_edges(G, zones, name_col, transformer)

    df = pd.DataFrame(rows)
    return df, geometries


def _overlay_geometry(zones, name_col, transformer, lines, line_components):
    """
    Accurate zone overlay using original curved geometries clipped to boundaries.
    Groups clipped segments by component id to compute per-zone LCC ratio.
    """
    line_geoms = [geom for geom, _ in lines]
    tree = STRtree(line_geoms)

    rows = []
    for zone_name, zone_geom in zones:
        nearby = tree.query(zone_geom, predicate="intersects")

        if len(nearby) == 0:
            rows.append(_empty_row(zone_name, name_col))
            continue

        comp_lengths = defaultdict(float)
        total_length_m = 0

        for idx in nearby:
            geom = line_geoms[idx]
            if not zone_geom.intersects(geom):
                continue
            try:
                clipped = zone_geom.intersection(geom)
                length_m = transform(transformer.transform, clipped).length
            except Exception:
                length_m = transform(transformer.transform, geom).length

            if length_m > 0:
                comp_lengths[line_components[idx]] += length_m
                total_length_m += length_m

        if total_length_m == 0:
            rows.append(_empty_row(zone_name, name_col))
            continue

        lcc_length_m = max(comp_lengths.values())
        lcc_ratio = round(lcc_length_m / total_length_m, 4)
        projected_zone = transform(transformer.transform, zone_geom)
        area_km2 = projected_zone.area / 1_000_000
        density = round((total_length_m / 1000) / area_km2, 2) if area_km2 > 0 else 0

        rows.append({
            name_col: zone_name,
            "length_km": round(total_length_m / 1000, 3),
            "lcc_ratio": lcc_ratio,
            "stranded_pct": round((1 - lcc_ratio) * 100, 1),
            "num_components": len(comp_lengths),
            "density": density,
            "bridges": 0,
        })

    return rows


def _overlay_graph_edges(G, zones, name_col, transformer):
    """
    Fallback: reconstruct edges as straight lines between graph node coordinates.
    Less accurate near zone boundaries because original line curvature is lost.
    """
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
            rows.append(_empty_row(zone_name, name_col))
            continue

        sub = nx.Graph()
        for idx in nearby:
            u, v, data = edge_data[idx]
            sub.add_edge(u, v, length_m=data["length_m"])

        if sub.number_of_edges() == 0:
            rows.append(_empty_row(zone_name, name_col))
            continue

        zone_metrics = compute_metrics(sub)
        projected_zone = transform(transformer.transform, zone_geom)
        area_km2 = projected_zone.area / 1_000_000
        density = round(zone_metrics["total_length_km"] / area_km2, 2) if area_km2 > 0 else 0

        rows.append({
            name_col: zone_name,
            "length_km": zone_metrics["total_length_km"],
            "lcc_ratio": zone_metrics["lcc_ratio"],
            "stranded_pct": zone_metrics["stranded_pct"],
            "num_components": zone_metrics["num_components"],
            "density": density,
            "bridges": zone_metrics["bridges"],
        })

    return rows


def _empty_row(zone_name, name_col):
    return {
        name_col: zone_name,
        "length_km": 0,
        "lcc_ratio": 0,
        "stranded_pct": 100.0,
        "num_components": 0,
        "density": 0,
        "bridges": 0,
    }
