"""
Processor Architecture Models for QFF 2026.
Loads official definitions for Processor A, Processor B, and proposed Processor C.
Computes topology graphs, shortest path distances, and connectivity constraints.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

PROCESSORS_DIR = Path(__file__).resolve().parent.parent / "processors"


class QuantumProcessor:
    """
    Physical Quantum Processor model.
    Encapsulates topology coupling graph, basis gates, and noise parameters.
    """

    def __init__(self, definition: Dict[str, Any]):
        self.name: str = definition.get("name", "Unknown Processor")
        self.stage: str = definition.get("stage", "Phase 1")
        self.num_qubits: int = definition.get("num_qubits", 5)
        self.topology_type: str = definition.get("topology_type", "custom")
        self.basis_gates: List[str] = definition.get("basis_gates", ["rz", "sx", "x", "cx"])
        self.noise_calibration: Dict[str, Any] = definition.get("noise_calibration", {})
        self.layout_coordinates: Dict[str, Dict[str, int]] = definition.get("layout_coordinates", {})

        # Build adjacency graph
        self.coupling_map: List[Tuple[int, int]] = [
            (edge[0], edge[1]) for edge in definition.get("coupling_map", [])
        ]
        self.undirected_edges: List[Tuple[int, int]] = [
            (edge[0], edge[1]) for edge in definition.get("undirected_edges", [])
        ]
        self.adjacency: Dict[int, List[int]] = {i: [] for i in range(self.num_qubits)}
        for u, v in self.undirected_edges:
            if v not in self.adjacency[u]:
                self.adjacency[u].append(v)
            if u not in self.adjacency[v]:
                self.adjacency[v].append(u)

        # Precompute all-pairs shortest paths
        self.distance_matrix = self._compute_shortest_paths()

    def _compute_shortest_paths(self) -> List[List[int]]:
        """Computes shortest path distances between all qubit pairs via BFS."""
        dist = [[999] * self.num_qubits for _ in range(self.num_qubits)]
        for start in range(self.num_qubits):
            dist[start][start] = 0
            queue = [start]
            visited = {start}
            while queue:
                curr = queue.pop(0)
                d = dist[start][curr]
                for nbr in self.adjacency[curr]:
                    if nbr not in visited:
                        visited.add(nbr)
                        dist[start][nbr] = d + 1
                        queue.append(nbr)
        return dist

    def is_adjacent(self, q1: int, q2: int) -> bool:
        return q2 in self.adjacency.get(q1, [])

    def get_shortest_path(self, start: int, target: int) -> List[int]:
        """Returns the sequence of nodes along the shortest path between start and target."""
        if start == target:
            return [start]
        queue = [[start]]
        visited = {start}
        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node == target:
                return path
            for nbr in self.adjacency[node]:
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append(path + [nbr])
        return []

    def get_stats(self) -> Dict[str, Any]:
        degrees = [len(self.adjacency[i]) for i in range(self.num_qubits)]
        avg_deg = sum(degrees) / self.num_qubits if self.num_qubits else 0
        finite_distances = [
            self.distance_matrix[i][j]
            for i in range(self.num_qubits)
            for j in range(i + 1, self.num_qubits)
            if self.distance_matrix[i][j] < 999
        ]
        diameter = max(finite_distances) if finite_distances else 0
        avg_distance = sum(finite_distances) / len(finite_distances) if finite_distances else 0

        return {
            "name": self.name,
            "stage": self.stage,
            "num_qubits": self.num_qubits,
            "edge_count": len(self.undirected_edges),
            "topology_type": self.topology_type,
            "avg_degree": round(avg_deg, 2),
            "diameter": diameter,
            "avg_shortest_path": round(avg_distance, 2),
            "two_qubit_noise_rate": self.noise_calibration.get("two_qubit_depolarizing_rate", 0.005),
            "readout_noise_rate": self.noise_calibration.get("readout_error_rate_01", 0.015),
            "layout_coordinates": self.layout_coordinates,
            "edges": self.undirected_edges,
        }


def load_processor(name_or_file: str) -> QuantumProcessor:
    """Loads processor by filename or short key ('A', 'B', 'C')."""
    mapping = {
        "a": "processor_A.json",
        "processor_a": "processor_A.json",
        "b": "processor_B.json",
        "processor_b": "processor_B.json",
        "c": "processor_C.json",
        "processor_c": "processor_C.json",
    }
    filename = mapping.get(name_or_file.lower(), name_or_file)
    path = PROCESSORS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Processor file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return QuantumProcessor(data)


def load_all_processors() -> Dict[str, QuantumProcessor]:
    return {
        "A": load_processor("processor_A.json"),
        "B": load_processor("processor_B.json"),
        "C": load_processor("processor_C.json"),
    }


if __name__ == "__main__":
    procs = load_all_processors()
    for key, p in procs.items():
        stats = p.get_stats()
        print(f"[{key}] {stats['name']} ({stats['num_qubits']} qubits, {stats['edge_count']} edges, diameter={stats['diameter']}, avg path={stats['avg_shortest_path']})")
