"""
Quantum Transpiler & Architecture Routing Engine for QFF 2026.
Maps logical circuits to physical coupling graphs, inserts routing SWAP gates,
decomposes multi-qubit interactions into hardware basis gates, and computes architecture metrics.
"""

from typing import Dict, List, Tuple, Any, Optional
from src.quantum_core import QuantumCircuit
from src.processors import QuantumProcessor, load_processor


class Transpiler:
    """
    Architecture-aware quantum circuit transpiler.
    """

    def __init__(self, processor: QuantumProcessor):
        self.processor = processor

    def transpile(
        self,
        logical_circuit: QuantumCircuit,
        initial_layout: Optional[Dict[int, int]] = None
    ) -> Tuple[QuantumCircuit, Dict[str, Any]]:
        """
        Transpiles logical circuit to fit the target processor's coupling graph.
        initial_layout: maps logical qubit index -> physical qubit index.
        """
        num_logical = logical_circuit.num_qubits
        if num_logical > self.processor.num_qubits:
            raise ValueError(
                f"Logical circuit requires {num_logical} qubits, but processor has only {self.processor.num_qubits} qubits."
            )

        # Default greedy or identity placement
        if initial_layout is None:
            # For 4 qubits on Processor A (5 qubits), layout: 0->0, 1->1, 2->2, 3->3
            initial_layout = {i: i for i in range(num_logical)}

        # Current layout: logical qubit -> physical qubit
        logical_to_physical = dict(initial_layout)
        # Reverse layout: physical qubit -> logical qubit
        physical_to_logical = {p: l for l, p in logical_to_physical.items()}

        transpiled_qc = QuantumCircuit(self.processor.num_qubits, f"{logical_circuit.name}_{self.processor.name}")
        swap_count = 0
        algorithmic_cx_count = 0
        total_cx_decomposed = 0

        for name, qubits, params in logical_circuit.instructions:
            if len(qubits) == 1:
                phys_q = logical_to_physical[qubits[0]]
                if name == "h":
                    transpiled_qc.h(phys_q)
                elif name == "x":
                    transpiled_qc.x(phys_q)
                elif name == "y":
                    transpiled_qc.y(phys_q)
                elif name == "z":
                    transpiled_qc.z(phys_q)
                elif name == "sx":
                    transpiled_qc.sx(phys_q)
                elif name == "rx":
                    transpiled_qc.rx(params[0], phys_q)
                elif name == "ry":
                    transpiled_qc.ry(params[0], phys_q)
                elif name == "rz":
                    transpiled_qc.rz(params[0], phys_q)
                else:
                    raise ValueError(f"Unknown 1Q gate {name}")

            elif len(qubits) == 2:
                l_ctrl, l_targ = qubits[0], qubits[1]
                p_ctrl = logical_to_physical[l_ctrl]
                p_targ = logical_to_physical[l_targ]
                algorithmic_cx_count += 1

                if self.processor.is_adjacent(p_ctrl, p_targ):
                    # Direct native 2-qubit interaction available
                    transpiled_qc.cx(p_ctrl, p_targ)
                    total_cx_decomposed += 1
                else:
                    # Non-adjacent: route along shortest path
                    path = self.processor.get_shortest_path(p_ctrl, p_targ)
                    if not path or len(path) < 2:
                        raise RuntimeError(f"No coupling path between physical qubits {p_ctrl} and {p_targ}")

                    # Swap control qubit along path until adjacent to target
                    swaps_needed = len(path) - 2
                    for step in range(swaps_needed):
                        node_a = path[step]
                        node_b = path[step + 1]
                        transpiled_qc.swap(node_a, node_b)
                        swap_count += 1
                        total_cx_decomposed += 3  # Hardware SWAP = 3 CX gates

                    # Execute interaction between path[-2] and path[-1] (p_targ)
                    transpiled_qc.cx(path[-2], path[-1])
                    total_cx_decomposed += 1

                    # Swap back to preserve deterministic physical layout
                    for step in reversed(range(swaps_needed)):
                        node_a = path[step]
                        node_b = path[step + 1]
                        transpiled_qc.swap(node_a, node_b)
                        swap_count += 1
                        total_cx_decomposed += 3

        ops = transpiled_qc.count_ops()
        metrics = {
            "processor_name": self.processor.name,
            "logical_qubits": num_logical,
            "physical_qubits": self.processor.num_qubits,
            "logical_depth": logical_circuit.depth(),
            "transpiled_depth": transpiled_qc.depth(),
            "algorithmic_cx": algorithmic_cx_count,
            "swap_count": swap_count,
            "total_physical_cx": total_cx_decomposed,
            "total_gates": len(transpiled_qc.instructions),
            "operations": ops,
            "layout": initial_layout,
            "routing_overhead_ratio": round(total_cx_decomposed / max(1, algorithmic_cx_count), 2),
        }
        return transpiled_qc, metrics


def compare_transpilation_on_all_processors(logical_circuit: QuantumCircuit) -> Dict[str, Any]:
    """Runs transpilation of the same logical circuit across Processors A, B, and C."""
    from src.processors import load_all_processors
    procs = load_all_processors()
    comparison = {}

    for key in ["A", "B", "C"]:
        proc = procs[key]
        transpiler = Transpiler(proc)
        _, metrics = transpiler.transpile(logical_circuit)
        comparison[key] = metrics

    return comparison


if __name__ == "__main__":
    # Test circuit with non-adjacent interactions on a 4-qubit linear ring
    qc = QuantumCircuit(4, "linear_entangler")
    for q in range(4):
        qc.ry(1.0, q)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    qc.cx(3, 0)  # Long-range interaction on linear architecture

    comp = compare_transpilation_on_all_processors(qc)
    print("Transpilation Comparison across A, B, C:")
    for k, v in comp.items():
        print(f"Processor {k}: Depth={v['transpiled_depth']}, Algorithmic CX={v['algorithmic_cx']}, SWAPs={v['swap_count']}, Total Physical CX={v['total_physical_cx']}")
