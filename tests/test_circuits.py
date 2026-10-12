import math
import pytest
from src.quantum_core import QuantumCircuit, StatevectorSimulator


def test_quantum_circuit_creation_and_depth():
    qc = QuantumCircuit(4, "test_qc")
    qc.h(0)
    qc.ry(1.0, 1)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)

    ops = qc.count_ops()
    assert ops["h"] == 1
    assert ops["ry"] == 1
    assert ops["cx"] == 3
    assert qc.depth() >= 3


def test_bell_state_fidelity():
    qc = QuantumCircuit(2, "bell")
    qc.h(0)
    qc.cx(0, 1)

    sim = StatevectorSimulator(2)
    sim.execute_circuit(qc)
    probs = sim.probabilities()

    # Prob(|00>) = 0.5, Prob(|11>) = 0.5
    assert math.isclose(probs[0], 0.5, abs_tol=1e-5)
    assert math.isclose(probs[1], 0.0, abs_tol=1e-5)
    assert math.isclose(probs[2], 0.0, abs_tol=1e-5)
    assert math.isclose(probs[3], 0.5, abs_tol=1e-5)

    # Correlator <Z0 Z1> = 1.0
    assert math.isclose(sim.expectation_value_all_z(), 1.0, abs_tol=1e-5)


def test_finite_shots_sampling():
    qc = QuantumCircuit(2, "sample_test")
    qc.h(0)
    sim = StatevectorSimulator(2)
    sim.execute_circuit(qc)
    counts = sim.sample_counts(shots=1000, seed=42)
    assert sum(counts.values()) == 1000
    # Both '00' and '01' should appear with roughly equal frequency
    assert abs(counts.get("00", 0) - counts.get("01", 0)) < 150
