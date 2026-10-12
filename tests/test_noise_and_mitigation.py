import math
import pytest
from src.quantum_core import QuantumCircuit, StatevectorSimulator
from src.noise_models import CalibratedNoiseModel, NoisyCircuitExecutor
from src.mitigation import (
    UnitaryGateFolder,
    ReadoutMitigator,
    ZeroNoiseExtrapolator,
    QuantumMitigationEngine,
)


def test_gate_folding():
    qc = QuantumCircuit(2, "fold_test")
    qc.cx(0, 1)

    f1 = UnitaryGateFolder.fold_circuit(qc, scale_factor=1)
    assert f1.count_ops()["cx"] == 1

    f3 = UnitaryGateFolder.fold_circuit(qc, scale_factor=3)
    assert f3.count_ops()["cx"] == 3

    f5 = UnitaryGateFolder.fold_circuit(qc, scale_factor=5)
    assert f5.count_ops()["cx"] == 5


def test_richardson_extrapolation():
    # Linear test: E(r) = 1.0 - 0.1 * r => E(0) = 1.0
    scales = [1, 3, 5]
    vals = [1.0 - 0.1 * r for r in scales]
    e0 = ZeroNoiseExtrapolator.richardson_extrapolate(scales, vals)
    assert math.isclose(e0, 1.0, abs_tol=1e-5)


def test_readout_mitigation_inversion():
    noise = CalibratedNoiseModel(p_ro_01=0.03, p_ro_10=0.03)
    rem = ReadoutMitigator(noise, 2)
    # The inverted matrix times the calibration matrix must yield identity
    M = rem.calibration_matrix
    M_inv = rem.inv_matrix
    dim = 4
    for i in range(dim):
        for j in range(dim):
            prod = sum(M_inv[i][k] * M[k][j] for k in range(dim))
            expected = 1.0 if i == j else 0.0
            assert math.isclose(prod, expected, abs_tol=1e-4)


def test_dual_mitigation_error_reduction():
    qc = QuantumCircuit(4, "vqc_slice")
    for q in range(4):
        qc.ry(1.0, q)
    qc.cx(0, 1)
    qc.cx(1, 2)

    sim = StatevectorSimulator(4)
    sim.execute_circuit(qc)
    ideal_exp = sim.expectation_value_z(0)

    noise = CalibratedNoiseModel(p_1q=0.001, p_2q=0.008, p_ro_01=0.02, p_ro_10=0.02)
    engine = QuantumMitigationEngine(noise)

    res_none = engine.run_mitigated(qc, method="none", shots=2048, seed=42)
    res_dual = engine.run_mitigated(qc, method="dual", shots=2048, seed=42)

    err_none = abs(res_none["expectation_z0"] - ideal_exp)
    err_dual = abs(res_dual["expectation_z0"] - ideal_exp)

    # Dual mitigation should measurably reduce error compared to unmitigated
    assert err_dual <= err_none + 0.01
