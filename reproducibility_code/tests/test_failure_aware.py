import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import networkx as nx

from geo_routing.failure_aware import (
    adaptive_failure_outcome,
    build_path_catalog,
    edge_key,
    frozen_failure_outcome,
    random_single_edge_failures,
    solve_nominal_te,
    solve_scenario_risk_te,
    solve_tail_robust_te,
)
from geo_routing.curvature import ollivier_all
from geo_routing.topology import ODDemand
from geo_routing.repetita import load_instance, physical_projection
from geo_routing.exp_submission_upgrade import split_double_failures


def diamond_graph():
    graph = nx.Graph()
    graph.add_edges_from([(0, 1), (1, 3), (0, 2), (2, 3)])
    for u, v in graph.edges():
        graph[u][v]["cost"] = 1.0
        graph[u][v]["capacity"] = 5.0
    return graph


class FailureAwareTests(unittest.TestCase):
    def test_portable_ollivier_curvature_on_triangle(self):
        graph = nx.complete_graph(3)
        curvature, _ = ollivier_all(graph, alpha=0.5)
        for value in curvature.values():
            self.assertAlmostEqual(value, 0.75, places=7)

    def test_minimum_mlu_splits_a_symmetric_demand(self):
        graph = diamond_graph()
        demands = [ODDemand(0, 3, 10.0)]
        catalog = build_path_catalog(graph, demands, k_paths=2)
        solution = solve_nominal_te(graph, demands, catalog=catalog, mlu_slack=0.0)
        self.assertTrue(solution.success)
        self.assertAlmostEqual(solution.mlu, 1.0, places=7)
        self.assertEqual(len([flow for flow in solution.path_flows if flow > 1e-8]), 2)

    def test_frozen_failure_uses_delivered_traffic_not_edge_labels(self):
        graph = diamond_graph()
        demands = [ODDemand(0, 3, 10.0)]
        solution = solve_nominal_te(graph, demands, k_paths=2, mlu_slack=0.0)
        outcome = frozen_failure_outcome(graph, demands, solution, {(0, 1)})
        self.assertAlmostEqual(outcome.delivered_fraction, 0.5, places=7)

    def test_nominal_structural_policy_respects_explicit_latency_limit(self):
        graph = nx.Graph()
        graph.add_edges_from([(0, 1), (1, 3), (0, 2), (2, 4), (4, 3)])
        for u, v in graph.edges():
            graph[u][v]["cost"] = 1.0
            graph[u][v]["capacity"] = 10.0
        demands = [ODDemand(0, 3, 5.0)]
        catalog = build_path_catalog(graph, demands, k_paths=2)
        risk = {edge_key(0, 1): 1.0, edge_key(1, 3): 1.0}
        unconstrained = solve_nominal_te(
            graph, demands, catalog=catalog, risk_scores=risk,
            risk_strength=100.0, mlu_slack=1.0,
        )
        constrained = solve_nominal_te(
            graph, demands, catalog=catalog, risk_scores=risk,
            risk_strength=100.0, mlu_slack=1.0, latency_limit=2.2,
        )
        self.assertGreater(unconstrained.average_path_cost, 2.9)
        self.assertLessEqual(constrained.average_path_cost, 2.2 + 1e-8)

    def test_adaptive_delivery_is_capacity_feasible(self):
        graph = diamond_graph()
        demands = [ODDemand(0, 3, 10.0)]
        outcome = adaptive_failure_outcome(graph, demands, {(0, 1)}, k_paths=2)
        self.assertAlmostEqual(outcome.delivered_fraction, 0.5, places=7)
        self.assertLessEqual(outcome.max_utilization, 1.0 + 1e-8)

    def test_adaptive_delivery_can_use_a_precomputed_catalog(self):
        graph = diamond_graph()
        demands = [ODDemand(0, 3, 10.0)]
        catalog = build_path_catalog(graph, demands, k_paths=2)
        outcome = adaptive_failure_outcome(
            graph, demands, {(0, 1)}, k_paths=2, catalog=catalog
        )
        self.assertAlmostEqual(outcome.delivered_fraction, 0.5, places=7)

    def test_tail_robust_solution_minimizes_worst_physical_exposure(self):
        graph = diamond_graph()
        demands = [ODDemand(0, 3, 10.0)]
        catalog = build_path_catalog(graph, demands, k_paths=2)
        solution = solve_tail_robust_te(
            graph, demands, catalog=catalog, mlu_slack=0.0, latency_limit=2.0
        )
        self.assertTrue(solution.success)
        self.assertAlmostEqual(solution.policy_exposure, 0.5, places=7)
        for edge in [(0, 1), (0, 2)]:
            outcome = frozen_failure_outcome(graph, demands, solution, {edge})
            self.assertAlmostEqual(outcome.delivered_fraction, 0.5, places=7)

    def test_scenario_max_reproduces_single_link_tail_optimizer(self):
        graph = diamond_graph()
        demands = [ODDemand(0, 3, 10.0)]
        catalog = build_path_catalog(graph, demands, k_paths=2)
        scenarios = [{edge} for edge in graph.edges()]
        generic = solve_scenario_risk_te(
            graph, demands, scenarios, catalog=catalog, risk_measure="max",
            mlu_slack=0.0, latency_limit=2.0
        )
        legacy = solve_tail_robust_te(
            graph, demands, catalog=catalog, mlu_slack=0.0, latency_limit=2.0
        )
        self.assertTrue(generic.success)
        self.assertAlmostEqual(generic.policy_exposure, legacy.policy_exposure, places=7)
        self.assertAlmostEqual(generic.average_path_cost, legacy.average_path_cost, places=7)

    def test_double_failure_counts_each_intersected_path_once(self):
        graph = diamond_graph()
        demands = [ODDemand(0, 3, 10.0)]
        catalog = build_path_catalog(graph, demands, k_paths=2)
        solution = solve_scenario_risk_te(
            graph,
            demands,
            scenarios=[{(0, 1), (1, 3)}],
            catalog=catalog,
            risk_measure="expected",
            mlu_slack=0.0,
            latency_limit=2.0,
        )
        self.assertTrue(solution.success)
        self.assertAlmostEqual(solution.policy_exposure, 0.5, places=7)

    def test_cvar_is_at_least_expected_loss_and_at_most_maximum_loss(self):
        graph = diamond_graph()
        demands = [ODDemand(0, 3, 10.0)]
        catalog = build_path_catalog(graph, demands, k_paths=2)
        scenarios = [{(0, 1)}, {(0, 2)}]
        expected = solve_scenario_risk_te(
            graph, demands, scenarios, catalog=catalog, risk_measure="expected",
            mlu_slack=0.0, latency_limit=2.0
        )
        cvar = solve_scenario_risk_te(
            graph, demands, scenarios, catalog=catalog, risk_measure="cvar", beta=0.9,
            mlu_slack=0.0, latency_limit=2.0
        )
        maximum = solve_scenario_risk_te(
            graph, demands, scenarios, catalog=catalog, risk_measure="max",
            mlu_slack=0.0, latency_limit=2.0
        )
        self.assertTrue(cvar.success)
        self.assertLessEqual(expected.policy_exposure, cvar.policy_exposure + 1e-8)
        self.assertLessEqual(cvar.policy_exposure, maximum.policy_exposure + 1e-8)

    def test_directed_arcs_keep_separate_capacity_and_fail_together(self):
        graph = nx.DiGraph()
        graph.add_edges_from([(0, 1), (1, 0), (1, 2), (2, 1), (0, 2), (2, 0)])
        for u, v in graph.edges():
            graph[u][v]["cost"] = 1.0
            graph[u][v]["capacity"] = 5.0
        demands = [ODDemand(0, 1, 5.0), ODDemand(1, 0, 5.0)]
        solution = solve_nominal_te(graph, demands, k_paths=2, mlu_slack=0.0)
        self.assertTrue(solution.success)
        outcome = frozen_failure_outcome(graph, demands, solution, {(0, 1)})
        self.assertLess(outcome.delivered_fraction, 1.0)
        self.assertEqual(len(random_single_edge_failures(graph, 3, seed=1)), 3)

    def test_repetita_reader_preserves_directed_arcs(self):
        graph_text = """NODES 3
label x y
n0 0 0
n1 1 0
n2 2 0

EDGES 5
label src dest weight bw delay
e0 0 1 10 100 5
e1 1 0 10 100 5
e2 1 2 10 80 7
e3 2 1 10 80 7
e4 0 1 10 100 5
"""
        demand_text = """DEMANDS 2
label src dest bw
d0 0 2 25
d1 2 0 30
"""
        with TemporaryDirectory() as directory:
            topology_path = Path(directory) / "toy.graph"
            demand_path = Path(directory) / "toy.0000.demands"
            topology_path.write_text(graph_text, encoding="utf-8")
            demand_path.write_text(demand_text, encoding="utf-8")
            instance = load_instance(topology_path, demand_path)
        self.assertTrue(instance.graph.is_directed())
        self.assertEqual(instance.graph.number_of_edges(), 4)
        self.assertEqual(instance.graph[0][1]["capacity"], 200.0)
        self.assertEqual(instance.graph.graph["parallel_arcs_collapsed"], 1)
        self.assertEqual(len(instance.demands), 2)
        self.assertEqual(physical_projection(instance.graph).number_of_edges(), 2)

    def test_double_failure_split_is_deterministic_disjoint_and_capped(self):
        edges = [(index, index + 1) for index in range(30)]
        first = split_double_failures("test", edges, cap=40)
        second = split_double_failures("test", edges, cap=40)
        self.assertEqual(first, second)
        self.assertLessEqual(len(first["design"]), 40)
        self.assertLessEqual(len(first["evaluation"]), 40)
        self.assertTrue(set(first["design"]).isdisjoint(first["evaluation"]))


if __name__ == "__main__":
    unittest.main()
