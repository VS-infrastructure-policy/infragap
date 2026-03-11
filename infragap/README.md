# infragap

Infrastructure network connectivity diagnostics for policy analysts.

---

Public agencies collect infrastructure geometry -- bike lanes, transit corridors, power lines, water mains -- as GeoJSON or shapefiles. But answering "how connected is this network?" typically requires GIS software, spatial databases, or writing graph code from scratch. infragap does it in three lines of Python: load a GeoJSON file, run a diagnosis, read the results.

```python
import infragap

net = infragap.from_file("bike_lanes.geojson")
report = net.diagnose()
print(report)
```

```
  Network Diagnosis
  -----------------------------------
  Total length          202.9 km
  Segments              3,464
  Components              330
  Avg component           615 m

  Connectivity
    LCC length           23.9 km
    LCC ratio            11.8%
    Stranded             88.2%
    Beta (e/v)           0.94
    Alpha                0.01
    Gamma                0.31

  Resilience
    Bridges               2524
    Edge connectivity        0
```

Reading this output: Milan's bike lane network is heavily fragmented. Only 11.8% of the total infrastructure length sits in the largest connected component -- the rest is stranded in 329 smaller, disconnected clusters. The beta index (0.94) and alpha index (0.01) show a tree-like network with almost no route redundancy, and 2,524 of the network's edges are bridges (single points of failure whose removal would disconnect part of the network).

---

## Table of contents

- [Installation](#installation)
- [API reference](#api-reference)
  - [High-level: Network class](#high-level-network-class)
  - [Report objects](#report-objects)
  - [Low-level functions](#low-level-functions)
- [Metrics reference](#metrics-reference)
- [Methodology](#methodology)
- [Input requirements](#input-requirements)
- [Known limitations](#known-limitations)
- [Project structure](#project-structure)
- [Dependencies](#dependencies)
- [References](#references)

---

## Installation

```
pip install -e .
```

Requires Python 3.10 or later.

For development (includes pytest):

```
pip install -e ".[dev]"
```

---

## API reference

### High-level: Network class

The `Network` class is the main entry point. It loads a GeoJSON file, detects the coordinate reference system, builds a graph, and exposes all analysis methods.

#### `infragap.from_file(path, tolerance=5, strategies=None)`

Create a `Network` from a GeoJSON file.

- **path** -- Path to a GeoJSON file with LineString or MultiLineString features.
- **tolerance** -- Maximum distance in metres to snap nearby endpoints together (default: 5). Municipal GeoJSON data often has small digitisation gaps between segments that should be connected. The tolerance bridges these gaps. Higher values merge more aggressively; lower values preserve separation.
- **strategies** -- Set of clustering strategies to use during graph construction. Any subset of `{"endpoints", "tjunctions", "overlaps"}`. Default (`None`): all three. See [Methodology](#methodology) for what each strategy does.

```python
import infragap

# Default tolerance (5 metres), all strategies
net = infragap.from_file("bike_lanes.geojson")

# Strict: only merge endpoints within 2 metres
net = infragap.from_file("bike_lanes.geojson", tolerance=2)

# Lenient: merge endpoints within 10 metres
net = infragap.from_file("bike_lanes.geojson", tolerance=10)

# Endpoint snapping only (no T-junction or overlap detection)
net = infragap.from_file("bike_lanes.geojson", strategies={"endpoints"})

# Endpoints and T-junctions, but no overlap detection
net = infragap.from_file("bike_lanes.geojson", strategies={"endpoints", "tjunctions"})
```

#### `Network.diagnose()`

Run a full network-level diagnosis. Returns a `Report` object.

```python
report = net.diagnose()
print(report)
```

#### `Network.diagnose_by_zone(zones_path, name_col)`

Run a zone-level diagnosis by overlaying the network with administrative boundary polygons. Returns a `ZoneReport` object.

- **zones_path** -- Path to a GeoJSON file containing polygon features (neighbourhoods, municipalities, districts).
- **name_col** -- The property name in the zone file that identifies each zone (e.g. `"NIL"`, `"name"`, `"district_id"`).

```python
zones = net.diagnose_by_zone("neighbourhoods.geojson", name_col="NIL")
print(zones)
```

| NIL          | length_km | lcc_ratio | stranded_pct | num_components | density | bridges |
|--------------|-----------|-----------|--------------|----------------|---------|---------|
| Brera        |       3.2 |    0.6800 |         32.0 |              4 |    8.41 |      12 |
| Navigli      |       5.1 |    0.4300 |         57.0 |              7 |    6.23 |      19 |
| Isola        |       1.8 |    1.0000 |          0.0 |              1 |    4.50 |       8 |

The `density` column is km of infrastructure per km2 of zone area, projected to UTM.

#### `Network.bridges()`

Return a list of bridge edges -- connections whose removal would split a component.

```python
bridge_edges = net.bridges()
print(f"{len(bridge_edges)} single points of failure")

for node_a, node_b in bridge_edges[:5]:
    print(f"  {node_a} -- {node_b}")
```

#### `Network` attributes

After construction, the following attributes are available:

```python
net.segments       # number of line segments loaded (int)
net.graph          # the underlying networkx.Graph
net.transformer    # the pyproj Transformer (WGS84 to UTM)
net.lines          # list of (LineString, properties) tuples
net.path           # path to the source GeoJSON file
net.tolerance      # tolerance used for graph construction (metres)
net.strategies     # set of clustering strategies used (or None for all)
```

The `net.graph` object is a standard networkx graph. You can use any networkx function on it directly:

```python
import networkx as nx

print(nx.number_connected_components(net.graph))
print(nx.diameter(net.graph.subgraph(max(nx.connected_components(net.graph), key=len))))
```

---

### Report objects

#### `Report`

Returned by `Network.diagnose()`. Holds all network-level metrics.

```python
report = net.diagnose()

# Print a formatted summary
print(report)

# Access individual metrics as attributes
report.total_length_km        # 202.9
report.segments               # 3464
report.components             # 330
report.avg_component_length_m # 615.0
report.lcc_length_km          # 23.9
report.lcc_ratio              # 0.1177
report.stranded_pct           # 88.2
report.beta                   # 0.94
report.alpha                  # 0.01
report.gamma                  # 0.31
report.bridges                # 2524
report.edge_connectivity      # 0

# Export
report.to_dict()              # plain dictionary
report.to_dataframe()         # single-row pandas DataFrame
report.to_json()              # JSON string
```

#### `ZoneReport`

Returned by `Network.diagnose_by_zone()`. Wraps a pandas DataFrame with one row per zone.

```python
zones = net.diagnose_by_zone("neighbourhoods.geojson", name_col="NIL")

# Print the table
print(zones)

# Access the underlying DataFrame
zones.df

# Export to Excel (for non-technical stakeholders)
zones.to_excel("zone_report.xlsx")

# Export to GeoJSON (for mapping in QGIS, kepler.gl, Mapbox, etc.)
zones.to_geojson("zone_metrics.geojson")
```

The GeoJSON export attaches all computed metrics as properties on each zone polygon, making it ready for choropleth mapping.

---

### Low-level functions

The `Network` class is a convenience wrapper. Each step of the pipeline is also available as a standalone function. This is useful when you need more control, want to swap out a single step, or want to reuse a component in another project.

#### `infragap.detect_crs(longitude, latitude)`

Determine the correct UTM zone from a single WGS84 coordinate and return a `pyproj.Transformer`.

```python
from infragap import detect_crs

transformer = detect_crs(9.19, 45.46)
# Your UTM Zone is EPSG:32632
```

This is useful on its own any time you need to project WGS84 coordinates to metres and don't want to look up which UTM zone to use.

#### `infragap.get_length_meters(geom, transformer)`

Compute the length of any shapely geometry in metres using a pyproj transformer.

```python
from infragap import detect_crs, get_length_meters
from shapely.geometry import LineString

transformer = detect_crs(9.19, 45.46)
line = LineString([(9.18, 45.45), (9.20, 45.47)])
print(f"{get_length_meters(line, transformer):.1f} metres")
```

Works with any geometry that has a `.length` property: LineString, MultiLineString, LinearRing.

#### `infragap.load_geojson(path)`

Read a GeoJSON file and return a flat list of `(LineString, properties)` tuples. MultiLineStrings are split into individual LineStrings. Degenerate geometries (fewer than 2 coordinates) are filtered out.

```python
from infragap import load_geojson

lines = load_geojson("bike_lanes.geojson")
print(f"{len(lines)} segments")

geom, props = lines[0]
print(geom.geom_type)   # "LineString"
print(props)             # {"name": "Via Dante", ...}
```

#### `infragap.build_graph(lines, tolerance, transformer, strategies=None)`

Build a networkx graph from a list of `(LineString, properties)` tuples. This is the core algorithm -- it clusters lines using spatial strategies (endpoint proximity, T-junctions, overlapping segments) and constructs a graph with `length_m` edge attributes.

- **strategies** -- Set of clustering strategies. Any subset of `{"endpoints", "tjunctions", "overlaps"}`. Default (`None`): all three.

```python
from infragap import load_geojson, detect_crs, build_graph

lines = load_geojson("bike_lanes.geojson")
transformer = detect_crs(9.19, 45.46)

# All strategies (default)
G = build_graph(lines, tolerance=5, transformer=transformer)

# Endpoint snapping only
G = build_graph(lines, tolerance=5, transformer=transformer, strategies={"endpoints"})

print(G.number_of_nodes())
print(G.number_of_edges())
```

The returned graph is a standard `networkx.Graph`. Each edge has a `length_m` attribute (float, in metres).

#### `infragap.compute_metrics(G)`

Compute all connectivity and resilience metrics from any networkx graph that has `length_m` edge attributes. Returns a dictionary.

```python
from infragap import compute_metrics

metrics = compute_metrics(G)
print(metrics["lcc_ratio"])
print(metrics["bridges"])
print(metrics["alpha"])
```

This function is not limited to infragap-built graphs. You can use it on any networkx graph:

```python
import networkx as nx
from infragap import compute_metrics

G = nx.karate_club_graph()
for u, v in G.edges():
    G[u][v]["length_m"] = 100

metrics = compute_metrics(G)
```

#### `infragap.overlay(G, zones_path, name_col, transformer)`

Intersect a network graph with zone boundary polygons and compute per-zone metrics. Returns a `(DataFrame, geometries)` tuple.

```python
from infragap import overlay

df, geometries = overlay(G, "neighbourhoods.geojson", "NIL", transformer)
print(df)
```

---

## Metrics reference

### Network structure

| Metric | Definition |
|--------|-----------|
| **Segments** | Number of individual line geometries in the input file. |
| **Components** | Number of disconnected subnetworks. A fully connected network has 1 component. |
| **Avg component length** | Total network length divided by the number of components. Small values indicate many short, isolated fragments. |

### Connectivity indices

| Metric | Formula | Range | Interpretation |
|--------|---------|-------|---------------|
| **LCC ratio** | LCC length / total length | 0 -- 1 | Share of infrastructure in the largest connected component. The single most important fragmentation indicator. 1.0 = fully connected. |
| **Stranded %** | (1 - LCC ratio) x 100 | 0 -- 100 | Infrastructure disconnected from the main network. |
| **Beta** | e / v | 0 -- ... | Edges per node. Below 1.0 = tree-like (no alternative routes). Above 1.0 = loops and redundancy exist. |
| **Alpha** | (e - v + p) / (2v - 5) | 0 -- 1 | Meshedness (Kansky 1963). What fraction of all possible independent circuits exist. 0 = no loops, 1 = maximum redundancy. |
| **Gamma** | e / 3(v - 2) | 0 -- 1 | Connectivity (Kansky 1963). What fraction of all possible direct connections exist. |

Where *e* = edges, *v* = nodes, *p* = number of connected components.

### Resilience

| Metric | Definition |
|--------|-----------|
| **Bridges** | Number of edges whose removal would split a connected component into two. These are the network's single points of failure. |
| **Edge connectivity** | Minimum number of edges that must be removed to disconnect the network. Only meaningful for single-component networks; for fragmented networks this is 0 by definition. Use the bridge count instead for multi-component networks. |

---

## Methodology

infragap converts raw GeoJSON line segments into a networkx graph in two phases.

### Phase 1: Clustering

All line segments are grouped into connected clusters using a Union-Find data structure with path compression. Three spatial strategies run in sequence (each can be individually enabled or disabled via the `strategies` parameter):

1. **Endpoint-to-endpoint proximity** (`"endpoints"`). Two segments are placed in the same cluster if any of their endpoints fall within the tolerance distance of each other.

2. **T-junction detection** (`"tjunctions"`). A segment endpoint that falls within tolerance of the *interior* of another segment creates a connection. This captures cases common in municipal data where one lane meets another mid-block rather than at an intersection.

3. **Overlap detection** (`"overlaps"`). Segments that geometrically intersect or overlap are merged. This handles duplicate digitisation and crossing lines. Parallel lines that do not touch are kept separate to avoid falsely merging distinct infrastructure (e.g. bike lanes on opposite sides of a road).

Disabling strategies is useful for cross-tool comparisons (e.g. endpoint-only mode to match simpler tools like OSMnx) or for isolating the effect of each strategy on a particular dataset.

### Phase 2: Graph construction

Within each cluster, nearby endpoints are snapped to shared graph nodes using a second Union-Find pass. Cluster boundaries are strictly respected: two endpoints from different clusters are never merged, even if they are within tolerance. This prevents false connections between genuinely separate subnetworks.

Lines whose endpoints snap to the same node (self-loops) do not produce graph edges but their length is preserved as a node attribute and included in all length-based metrics.

### Projection

All distance calculations use UTM projection, automatically detected from the input coordinates. The UTM zone is determined from the first coordinate in the file.

---

## Input requirements

- **Format:** GeoJSON (RFC 7946).
- **Geometry types:** `LineString` and `MultiLineString`. MultiLineStrings are flattened into individual segments. Other geometry types (Point, Polygon) are ignored.
- **Coordinate system:** WGS84 (EPSG:4326), the GeoJSON standard.
- **Minimum content:** At least one valid line geometry with 2 or more coordinates. Features with invalid or degenerate geometries are silently skipped.

---

## Known limitations

- **Zone overlay geometry.** When called via the `Network` class, zone overlay uses the original curved geometries clipped to each zone boundary, so length measurements are accurate even for segments that straddle boundaries. The low-level `overlay()` function falls back to straight-line edges if original geometries are not supplied.

- **Edge connectivity for fragmented networks.** Edge connectivity is 0 by definition for any network with more than one connected component (it is already disconnected). For fragmented infrastructure, the bridge count is a more informative resilience metric.

- **Single UTM zone.** The CRS is detected from the first coordinate in the file. Networks spanning multiple UTM zones (> 6 degrees of longitude) will have increasing distortion at the edges.

---

## Project structure

```
infragap/
    __init__.py    Public API: from_file(), Network class
    crs.py         CRS detection and UTM projection
    io.py          GeoJSON loading, geometry extraction
    graph.py       Union-Find clustering, graph construction
    metrics.py     Connectivity and resilience computation
    report.py      Report and ZoneReport output classes
    zones.py       Spatial overlay with administrative boundaries
tests/
    conftest.py     Test fixtures (K5, path, triangles, star graphs)
    test_crs.py     CRS detection and projection tests
    test_graph.py   Graph construction and Union-Find tests
    test_io.py      GeoJSON loading tests
    test_metrics.py Known-answer metric tests
    test_network.py End-to-end integration tests
    test_report.py  Report formatting and export tests
    test_zones.py   Zone overlay tests
```

### Running tests

```
pytest
```

44 tests verify all modules: CRS detection, GeoJSON loading, graph construction (endpoint snapping, T-junctions, parallel line separation), metrics against known-answer graphs, report formatting and export, zone overlay, and end-to-end integration.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| shapely | >= 2.0 | Geometry operations, spatial indexing via STRtree |
| pyproj | >= 3.4 | Coordinate projection (WGS84 to UTM) |
| networkx | >= 3.0 | Graph data structure, component analysis, bridge detection |
| pandas | >= 2.0 | Tabular output for zone-level reports |
| openpyxl | >= 3.0 | Excel export for zone reports |

---

## References

- Kansky, K.J. (1963). *Structure of Transportation Networks*. University of Chicago Department of Geography Research Papers.
- Rodrigue, J.-P. (2020). *The Geography of Transport Systems*. 5th edition, Routledge.
- Barthelemy, M. (2011). Spatial networks. *Physics Reports*, 499(1-3), 1-101.
- Buhl, J., et al. (2006). Topological patterns in street networks of self-organized urban settlements. *The European Physical Journal B*, 49(4), 513-522.

---

## License

MIT
