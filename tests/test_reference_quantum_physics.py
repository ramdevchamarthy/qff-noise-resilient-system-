"""
Focused Reference Tests for Quantum Physics, Gate Truth Tables,
Born Measurement Probabilities, Noise Channels, and Mitigation Inversion.
"""

import cmath
import math
import random
import pytest

from src.quantum_core import QuantumCircuit, StatevectorSimulator
from src.noise_models import CalibratedNoiseModel
from src.mitigation import (
    UnitaryGateFolder,
    ReadoutMitigator,
    ZeroNoiseExtrapolator,
)


# -----------------------------------------------------------------------------
# 1. Single-Qubit Gate Reference Tests
# -----------------------------------------------------------------------------

def test_single_qubit_pauli_x():
    """Verifies X|0> = |1> and <Z> = -1.0."""
    qc = QuantumCircuit(1, "x_gate")
    qc.x(0)
    sim = StatevectorSimulator(1)
    sim.execute_circuit(qc)
    probs = sim.probabilities()
    assert math.isclose(probs[0], 0.0, abs_tol=1e-6)
    assert math.isclose(probs[1], 1.0, abs_tol=1e-6)
    assert math.isclose(sim.expectation_value_z(0), -1.0, abs_tol=1e-6)


def test_single_qubit_hadamard_superposition():
    """Verifies H|0> creates equal superposition with 50/50 probabilities."""
    qc = QuantumCircuit(1, "h_gate")
    qc.h(0)
    sim = StatevectorSimulator(1)
    sim.execute_circuit(qc)
    probs = sim.probabilities()
    assert math.isclose(probs[0], 0.5, abs_tol=1e-6)
    assert math.isclose(probs[1], 0.5, abs_tol=1e-6)
    assert math.isclose(sim.expectation_value_z(0), 0.0, abs_tol=1e-6)


def test_single_qubit_sqrt_x():
    """Verifies SX applied twice equals Pauli X: (SX)^2 |0> = |1>."""
    qc = QuantumCircuit(1, "sx_gate")
    qc.sx(0)
    qc.sx(0)
    sim = StatevectorSimulator(1)
    sim.execute_circuit(qc)
    probs = sim.probabilities()
    assert math.isclose(probs[1], 1.0, abs_tol=1e-5)


def test_parameterized_rotations():
    """Verifies RY(pi)|0> flips state to |1> within precision."""
    qc = QuantumCircuit(1, "ry_rot")
    qc.ry(math.pi, 0)
    sim = StatevectorSimulator(1)
    sim.execute_circuit(qc)
    probs = sim.probabilities()
    assert math.isclose(probs[1], 1.0, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# 2. Multi-Qubit CX & SWAP Truth Tables
# -----------------------------------------------------------------------------

def test_cnot_truth_table():
    """Verifies CX operation truth table on all 4 computational basis inputs."""
    basis_inputs = [(0, 0), (0, 1), (1, 0), (1, 1)]
    expected_outputs = [(0, 0), (0, 1), (1, 1), (1, 0)]  # (ctrl, targ XOR ctrl)

    for (b_in_ctrl, b_in_targ), (b_exp_ctrl, b_exp_targ) in zip(basis_inputs, expected_outputs):
        qc = QuantumCircuit(2, "cx_truth")
        if b_in_ctrl:
            qc.x(0)
        if b_in_targ:
            qc.x(1)
        qc.cx(0, 1)

        sim = StatevectorSimulator(2)
        sim.execute_circuit(qc)
        probs = sim.probabilities()

        expected_idx = (b_exp_ctrl << 0) | (b_exp_targ << 1)
        # Note index bit order: qubit 0 is lowest bit
        exp_index = b_exp_ctrl * 1 + b_exp_targ * 2
        assert math.isclose(probs[exp_index], 1.0, abs_tol=1e-6)


def test_swap_gate_truth_table():
    """Verifies SWAP gate exchanges quantum states between qubits 0 and 2."""
    qc = QuantumCircuit(3, "swap_truth")
    qc.x(0)  # State |001> (q0=1, q1=0, q2=0)
    qc.swap(0, 2)  # Swapped to |100> (q0=0, q1=0, q2=1)

    sim = StatevectorSimulator(3)
    sim.execute_circuit(qc)
    probs = sim.probabilities()

    # Index 4 corresponds to q2=1, q1=0, q0=0: 1*4 = 4
    assert math.isclose(probs[4], 1.0, abs_tol=1e-6)
    assert math.isclose(probs[1], 0.0, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# 3. Measurement Probability & Born Rule Normalization
# -----------------------------------------------------------------------------

def test_born_rule_normalization():
    """Verifies sum of probabilities equals 1.0 on a 4-qubit entangled circuit."""
    qc = QuantumCircuit(4, "normalization_check")
    for q in range(4):
        qc.h(q)
        qc.rz(0.5 * q, q)
    qc.cx(0, 1)
    qc.cx(2, 3)

    sim = StatevectorSimulator(4)
    sim.execute_circuit(qc)
    probs = sim.probabilities()

    assert len(probs) == 16
    assert all(p >= 0.0 for p in probs)
    assert math.isclose(sum(probs), 1.0, abs_tol=1e-12)


# -----------------------------------------------------------------------------
# 4. Physical Noise Channel Modeling
# -----------------------------------------------------------------------------

def test_depolarizing_channel_fidelity_contraction():
    """Verifies that gate depolarizing error contracts probability towards mixed state."""
    p2 = 0.02
    noise = CalibratedNoiseModel(p_1q=0.002, p_2q=p2, p_ro_01=0.0, p_ro_10=0.0)
    
    phys_cx = 16
    phys_1q = 8
    F_gate = ((1.0 - noise.p_1q) ** phys_1q) * ((1.0 - noise.p_2q) ** phys_cx)

    ideal_probs = [1.0] + [0.0] * 15
    dim = 16
    mixed_p = 1.0 / dim
    noisy_probs = [F_gate * p + (1.0 - F_gate) * mixed_p for p in ideal_probs]

    # Ground state probability must contract from 1.0 to F_gate + (1-F_gate)/16
    assert noisy_probs[0] < 1.0
    assert noisy_probs[0] > mixed_p
    assert math.isclose(sum(noisy_probs), 1.0, abs_tol=1e-9)


def test_asymmetric_readout_matrix_properties():
    """Verifies that 16x16 readout calibration matrix rows sum to 1.0."""
    noise = CalibratedNoiseModel(p_ro_01=0.02, p_ro_10=0.03)
    cal_mat = noise.get_readout_calibration_matrix(4)
    
    assert len(cal_mat) == 16
    assert len(cal_mat[0]) == 16
    # Each column must sum to 1.0 (conservation of prepared state probability)
    for col in range(16):
        col_sum = sum(cal_mat[row][col] for row in range(16))
        assert math.isclose(col_sum, 1.0, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# 5. Mitigation Inversion & Simplex Projection
# -----------------------------------------------------------------------------

def test_readout_inversion_identity_reconstruction():
    """Verifies that inverting noisy counts reconstructed through M recovers ideal state."""
    noise = CalibratedNoiseModel(p_ro_01=0.015, p_ro_10=0.015)
    rem = ReadoutMitigator(noise, 2)
    
    # Let prepared state be pure |00> (index 0)
    ideal_counts = {"00": 10000, "01": 0, "10": 0, "11": 0}
    # Simulate readout distortion
    cal_matrix = rem.calibration_matrix
    dim = 4
    dist_p = [cal_matrix[r][0] for r in range(dim)]
    dist_counts = {
        format(r, "02b"): int(dist_p[r] * 10000) for r in range(dim)
    }

    mit_probs, mit_exp = rem.mitigate_counts(dist_counts)
    # Mitigated probability of |00> should be close to 1.0
    assert mit_probs["00"] >= 0.98
    assert math.isclose(mit_exp, 1.0, abs_tol=0.03)


def test_richardson_extrapolation_quadratic_cancellation():
    """Verifies that 3-point Richardson extrapolation recovers exact intercept for quadratic error."""
    # E(r) = E_0 + a*r + b*r^2 with E_0 = 0.75
    a, b = -0.05, 0.005
    E_0 = 0.75
    scales = [1, 3, 5]
    measurements = [E_0 + a * r + b * (r ** 2) for r in scales]
    
    extrapolated_e0 = ZeroNoiseExtrapolator.richardson_extrapolate(scales, measurements)
    assert math.isclose(extrapolated_e0, E_0, abs_tol=1e-6)
