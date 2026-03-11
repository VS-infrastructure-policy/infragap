import networkx as nx


def compute_metrics(G):
    """Compute connectivity and resilience metrics from a networkx graph."""

    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()

    # Total network length (includes self-loop segments if present)
    edge_length_m = sum(data["length_m"] for u, v, data in G.edges(data=True))
    total_length_m = G.graph.get("total_length_all_m", edge_length_m)
    total_length_km = total_length_m / 1000

    components = list(nx.connected_components(G))
    num_components = len(components)

    # Component lengths (edges + self-loop segments)
    component_lengths = []
    for comp in components:
        subgraph = G.subgraph(comp)
        edge_len = sum(data["length_m"] for u, v, data in subgraph.edges(data=True))
        node_len = sum(subgraph.nodes[n].get("self_loop_m", 0) for n in comp)
        component_lengths.append(edge_len + node_len)

    component_lengths.sort(reverse=True)

    # Largest connected component (by length, not node count)
    lcc_length_m = component_lengths[0] if component_lengths else 0
    lcc_length_km = lcc_length_m / 1000
    lcc_ratio = lcc_length_m / total_length_m if total_length_m > 0 else 0
    stranded_pct = (1 - lcc_ratio) * 100

    avg_comp_length_m = total_length_m / num_components if num_components > 0 else 0

    # Kansky indices
    # Beta = e/v (circuit ratio; below 1 = tree-like, above 1 = has loops)
    beta = num_edges / num_nodes if num_nodes > 0 else 0

    # Alpha = meshedness: (e - v + p) / (2v - 5)
    if num_nodes > 2:
        alpha = (num_edges - num_nodes + num_components) / (2 * num_nodes - 5)
        alpha = max(0, min(alpha, 1.0))
    else:
        alpha = 0

    # Gamma = connectivity: e / 3(v - 2)
    if num_nodes > 2:
        gamma = num_edges / (3 * (num_nodes - 2))
        gamma = min(gamma, 1.0)
    else:
        gamma = 0

    bridge_list = list(nx.bridges(G))
    num_bridges = len(bridge_list)

    # Edge connectivity (minimum edges to remove to disconnect the network)
    if num_components == 1 and num_nodes > 1:
        edge_conn = nx.edge_connectivity(G)
    else:
        edge_conn = 0

    return {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "total_length_m": total_length_m,
        "total_length_km": round(total_length_km, 1),
        "num_components": num_components,
        "component_lengths_m": component_lengths,
        "lcc_length_m": lcc_length_m,
        "lcc_length_km": round(lcc_length_km, 1),
        "lcc_ratio": round(lcc_ratio, 4),
        "stranded_pct": round(stranded_pct, 1),
        "avg_component_length_m": round(avg_comp_length_m, 0),
        "beta": round(beta, 2),
        "alpha": round(alpha, 2),
        "gamma": round(gamma, 2),
        "bridges": num_bridges,
        "bridge_list": bridge_list,
        "edge_connectivity": edge_conn,
    }
