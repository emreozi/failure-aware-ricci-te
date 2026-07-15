"""Reader for REPETITA graph and demand files.

REPETITA stores one capacity and delay per directed arc.  The routing graph
therefore remains directed.  Discrete curvature is computed separately on the
undirected physical projection and its score is copied to both directions by
the failure-aware optimizer.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import networkx as nx

from .topology import ODDemand


@dataclass(frozen=True)
class RepetitaInstance:
    name: str
    graph: nx.DiGraph
    demands: list[ODDemand]
    topology_path: Path
    demand_path: Path


def _nonempty_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_graph(path: str | Path) -> nx.DiGraph:
    path = Path(path)
    lines = _nonempty_lines(path)
    if not lines or not lines[0].startswith("NODES "):
        raise ValueError(f"not a REPETITA graph: {path}")

    node_count = int(lines[0].split()[1])
    edge_header = next(idx for idx, line in enumerate(lines) if line.startswith("EDGES "))
    edge_count = int(lines[edge_header].split()[1])
    node_rows = lines[2:edge_header]
    edge_rows = lines[edge_header + 2:]
    if len(node_rows) != node_count or len(edge_rows) != edge_count:
        raise ValueError(f"declared and parsed counts differ in {path}")

    graph = nx.DiGraph(
        name=path.stem,
        source=str(path),
        parallel_arcs_collapsed=0,
        parallel_bundles=0,
    )
    for idx, row in enumerate(node_rows):
        fields = row.split()
        label = fields[0]
        x = float(fields[1]) if len(fields) > 1 else float("nan")
        y = float(fields[2]) if len(fields) > 2 else float("nan")
        graph.add_node(idx, label=label, x=x, y=y)

    for row in edge_rows:
        fields = row.split()
        if len(fields) < 6:
            raise ValueError(f"malformed edge row in {path}: {row}")
        label, source, target, weight, bandwidth, delay = fields[:6]
        u, v = int(source), int(target)
        delay_value = float(delay)
        weight_value = float(weight)
        bandwidth_value = float(bandwidth)
        if graph.has_edge(u, v):
            existing = graph[u][v]
            if not (
                math.isclose(existing["delay"], delay_value)
                and math.isclose(existing["igp_weight"], weight_value)
            ):
                raise ValueError(
                    f"parallel arcs with unequal cost are unsupported for {(u, v)} in {path}"
                )
            existing["capacity"] += bandwidth_value
            existing["bundle_size"] += 1
            existing["labels"].append(label)
            graph.graph["parallel_arcs_collapsed"] += 1
            continue
        graph.add_edge(
            u,
            v,
            label=label,
            labels=[label],
            bundle_size=1,
            igp_weight=weight_value,
            capacity=bandwidth_value,
            delay=delay_value,
            cost=delay_value if delay_value > 0 else float(weight),
        )
    graph.graph["parallel_bundles"] = sum(
        1 for _, _, data in graph.edges(data=True) if data["bundle_size"] > 1
    )
    return graph


def load_demands(path: str | Path) -> list[ODDemand]:
    path = Path(path)
    lines = _nonempty_lines(path)
    if not lines or not lines[0].startswith("DEMANDS "):
        raise ValueError(f"not a REPETITA demand file: {path}")
    declared = int(lines[0].split()[1])
    rows = lines[2:]
    if len(rows) != declared:
        raise ValueError(f"declared and parsed demand counts differ in {path}")
    demands = []
    for row in rows:
        fields = row.split()
        if len(fields) < 4:
            raise ValueError(f"malformed demand row in {path}: {row}")
        _, source, target, bandwidth = fields[:4]
        volume = float(bandwidth)
        if volume > 0:
            demands.append(ODDemand(int(source), int(target), volume))
    return demands


def load_instance(topology_path: str | Path, demand_path: str | Path) -> RepetitaInstance:
    topology_path = Path(topology_path)
    demand_path = Path(demand_path)
    graph = load_graph(topology_path)
    demands = load_demands(demand_path)
    missing = {
        endpoint
        for demand in demands
        for endpoint in (demand.source, demand.target)
        if endpoint not in graph
    }
    if missing:
        raise ValueError(f"demand endpoints absent from topology: {sorted(missing)}")
    return RepetitaInstance(
        name=topology_path.stem,
        graph=graph,
        demands=demands,
        topology_path=topology_path,
        demand_path=demand_path,
    )


def physical_projection(graph: nx.DiGraph) -> nx.Graph:
    """Return an undirected simple graph solely for structural scoring."""

    projection = nx.Graph(name=f"{graph.graph.get('name', '')}-physical")
    projection.add_nodes_from(graph.nodes(data=True))
    for u, v, data in graph.edges(data=True):
        if projection.has_edge(u, v):
            projection[u][v]["cost"] = min(projection[u][v]["cost"], data["cost"])
            projection[u][v]["capacity"] += data["capacity"]
        else:
            projection.add_edge(
                u,
                v,
                cost=float(data.get("cost", 1.0)),
                capacity=float(data.get("capacity", 1.0)),
            )
    return projection


def discover_instances(dataset_root: str | Path, demand_index: int = 0) -> list[tuple[Path, Path]]:
    """Find topology/demand pairs without loading them."""

    root = Path(dataset_root)
    pairs = []
    for topology_path in sorted(root.glob("*.graph")):
        demand_path = root / f"{topology_path.stem}.{demand_index:04d}.demands"
        if demand_path.exists():
            pairs.append((topology_path, demand_path))
    return pairs
