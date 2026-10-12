import pytest
from src.processors import load_all_processors, load_processor
from src.quantum_core import QuantumCircuit
from src.transpiler import Transpiler, compare_transpilation_on_all_processors


def test_processors_loading():
    procs = load_all_processors()
    assert "A" in procs
    assert "B" in procs
    assert "C" in procs

    p_a = procs["A"]
    assert p_a.num_qubits == 5
    assert len(p_a.undirected_edges) == 4
    assert p_a.is_adjacent(0, 1)
    assert not p_a.is_adjacent(0, 4)

    p_b = procs["B"]
    assert p_b.num_qubits == 9
    assert len(p_b.undirected_edges) == 12

    p_c = procs["C"]
    assert p_c.num_qubits == 8


def test_transpiler_routing_and_swaps():
    proc_a = load_processor("A")
    transpiler = Transpiler(proc_a)

    # 4-qubit cyclic circuit: 0-1, 1-2, 2-3, 3-0
    qc = QuantumCircuit(4, "test_ring")
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    qc.cx(3, 0)

    transpiled, metrics = transpiler.transpile(qc)
    assert metrics["swap_count"] > 0
    assert metrics["total_physical_cx"] > metrics["algorithmic_cx"]
    assert metrics["transpiled_depth"] >= qc.depth()


def test_compare_transpilation_across_architectures():
    qc = QuantumCircuit(4, "test_compare")
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    qc.cx(3, 0)

    comp = compare_transpilation_on_all_processors(qc)
    assert "A" in comp
    assert "B" in comp
    assert "C" in comp
    # Processor C should have fewer or equal physical CX gates than A
    assert comp["C"]["total_physical_cx"] <= comp["A"]["total_physical_cx"]
