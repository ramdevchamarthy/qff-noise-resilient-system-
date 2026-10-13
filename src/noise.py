"""
Official Qiskit Noise Model Builder for QFF 2026 PS-Q3.
Constructs valid qiskit_aer.noise.NoiseModel instances directly from
organizer-provided processor benchmark configurations (Processor A and B).
"""

from typing import Dict, Any, Optional, Tuple, List
from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError


def build_qiskit_noise_model(
    processor_dict: Dict[str, Any],
    intensity_multiplier: float = 1.0,
    custom_p_2q: Optional[float] = None,
    custom_p_ro: Optional[float] = None
) -> Tuple[NoiseModel, Dict[str, float]]:
    """
    Constructs a Qiskit Aer NoiseModel from processor configuration dict.
    Basis gates supported: ['rz', 'sx', 'x', 'cx']
    """
    cal = processor_dict.get("noise_calibration", {})
    base_p1 = cal.get("single_qubit_depolarizing_rate", 0.001)
    base_p2 = cal.get("two_qubit_depolarizing_rate", 0.005)
    base_ro01 = cal.get("readout_error_rate_01", 0.015)
    base_ro10 = cal.get("readout_error_rate_10", 0.015)

    if custom_p_2q is not None:
        p2 = custom_p_2q
        p1 = p2 * 0.2
    else:
        p2 = base_p2 * intensity_multiplier
        p1 = base_p1 * intensity_multiplier

    if custom_p_ro is not None:
        p_ro_01 = custom_p_ro
        p_ro_10 = custom_p_ro
    else:
        p_ro_01 = base_ro01 * intensity_multiplier
        p_ro_10 = base_ro10 * intensity_multiplier

    # Bounds check
    p1 = max(0.0, min(0.75, p1))
    p2 = max(0.0, min(0.75, p2))
    p_ro_01 = max(0.0, min(0.5, p_ro_01))
    p_ro_10 = max(0.0, min(0.5, p_ro_10))

    noise_model = NoiseModel(basis_gates=processor_dict.get("basis_gates", ["rz", "sx", "x", "cx"]))

    # 1-qubit depolarizing error
    if p1 > 0.0:
        err_1q = depolarizing_error(p1, 1)
        noise_model.add_all_qubit_quantum_error(err_1q, ["sx", "x", "rz"])

    # 2-qubit depolarizing error on CX
    if p2 > 0.0:
        err_2q = depolarizing_error(p2, 2)
        noise_model.add_all_qubit_quantum_error(err_2q, ["cx"])

    # Readout error
    if p_ro_01 > 0.0 or p_ro_10 > 0.0:
        # ReadoutError matrix: [[P(0|0), P(1|0)], [P(0|1), P(1|1)]]
        ro_matrix = [
            [1.0 - p_ro_10, p_ro_10],
            [p_ro_01, 1.0 - p_ro_01]
        ]
        ro_err = ReadoutError(ro_matrix)
        noise_model.add_all_qubit_readout_error(ro_err)

    params_summary = {
        "p_1q": round(p1, 6),
        "p_2q": round(p2, 6),
        "p_ro_01": round(p_ro_01, 6),
        "p_ro_10": round(p_ro_10, 6),
        "source": cal.get("source", "QFF 2026 Authoritative Configuration")
    }

    return noise_model, params_summary
