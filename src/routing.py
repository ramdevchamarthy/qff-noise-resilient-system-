"""
Topology-aware routing and transpilation module using Qiskit.
Transpiles logical circuits against Processor A (5-qubit star-linear)
and Processor B (9-qubit heavy-hex) coupling maps and basis gates.
"""

from typing import Dict, Any, Tuple, Optional
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap


def transpile_for_processor(
    logical_circuit: QuantumCircuit,
    processor_dict: Dict[str, Any],
    optimization_level: int = 1,
    seed_transpiler: Optional[int] = 42
) -> Tuple[QuantumCircuit, Dict[str, Any]]:
    """
    Transpiles a logical QuantumCircuit to match the coupling map and basis gates of the target processor.
    Returns:
        (transpiled_circuit, metrics_dict)
    """
    coupling_edges = processor_dict.get("coupling_map", [])
    basis_gates = processor_dict.get("basis_gates", ["rz", "sx", "x", "cx"])
    cmap = CouplingMap(coupling_edges)

    transpiled = transpile(
        logical_circuit,
        coupling_map=cmap,
        basis_gates=basis_gates,
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler
    )

    ops = dict(transpiled.count_ops())
    # Count physical CX gates
    cx_count = ops.get("cx", 0)
    # Count algorithmic CX gates in logical circuit
    logical_ops = dict(logical_circuit.count_ops())
    algorithmic_cx = logical_ops.get("cx", 0)
    
    # In decomposed transpiled circuits, each SWAP = 3 CX.
    # Extra CX beyond algorithmic CX is due to routing SWAPs:
    extra_cx = max(0, cx_count - algorithmic_cx)
    inferred_swaps = extra_cx // 3

    metrics = {
        "processor_name": processor_dict.get("name", "Processor"),
        "physical_qubits": processor_dict.get("num_qubits", 5),
        "circuit_depth": transpiled.depth(),
        "transpiled_depth": transpiled.depth(),
        "total_gates": sum(ops.values()) - ops.get("measure", 0),
        "total_physical_cx": cx_count,
        "algorithmic_cx": algorithmic_cx,
        "swap_count": inferred_swaps,
        "two_qubit_gate_count": cx_count,
        "gate_counts": ops,
        "optimization_level": optimization_level,
        "seed_transpiler": seed_transpiler,
    }

    return transpiled, metrics
