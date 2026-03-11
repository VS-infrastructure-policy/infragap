import networkx as nx

from infragap.io import load_geojson
from infragap.crs import detect_crs, get_length_meters
from infragap.graph import build_graph
from infragap.metrics import compute_metrics
from infragap.report import Report, ZoneReport
from infragap.zones import overlay


def from_file(path, tolerance=5, strategies=None):
    """Load infrastructure from GeoJSON and create a Network object."""
    return Network(path, tolerance, strategies=strategies)


class Network:
    """Main class for infrastructure network analysis."""

    def __init__(self, path, tolerance=5, strategies=None):
        self.path = path
        self.tolerance = tolerance
        self.strategies = strategies
        self.lines = load_geojson(path)
        if not self.lines:
            raise ValueError(
                f"No valid LineString or MultiLineString features found in {path}. "
                "Check that the file contains line geometries with at least 2 coordinates."
            )
        self.segments = len(self.lines)
        first_coord = self.lines[0][0].coords[0]
        self.transformer = detect_crs(first_coord[0], first_coord[1])
        self.graph = build_graph(self.lines, tolerance, self.transformer, strategies=strategies)

        comps = list(nx.connected_components(self.graph))
        node_to_comp = {n: i for i, comp in enumerate(comps) for n in comp}
        line_nodes = self.graph.graph.get("line_nodes", [])
        self._line_components = [
            node_to_comp.get(na, node_to_comp.get(nb, 0))
            for na, nb in line_nodes
        ]

    def diagnose(self):
        """Run full network diagnosis and return a Report."""
        metrics = compute_metrics(self.graph)
        return Report(metrics, self.segments)

    def diagnose_by_zone(self, zones_path, name_col):
        """Run zone-level diagnosis and return a ZoneReport."""
        df, geometries = overlay(
            self.graph, zones_path, name_col, self.transformer,
            lines=self.lines, line_components=self._line_components
        )
        report = ZoneReport(df)
        report._geometries = geometries
        return report

    def bridges(self):
        """Return list of bridge edges (single points of failure)."""
        return list(nx.bridges(self.graph))
