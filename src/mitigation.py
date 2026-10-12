"""
Quantum Error Mitigation Suite for QFF 2026 PS-Q3.
Implements:
  1. Zero-Noise Extrapolation (ZNE) with Unitary Gate Folding (r=1, 3, 5) and Richardson / Polynomial Regression.
  2. Complete Readout Error Mitigation (REM) via Calibration Matrix Inversion and Simplex Projection.
  3. Combined Dual-Layer Mitigation (ZNE + REM).
Includes exact resource overhead accounting (extra circuits and shots).
"""

import math
from typing import Dict, List, Tuple, Any, Optional
from src.quantum_core import QuantumCircuit
from src.noise_models import CalibratedNoiseModel, NoisyCircuitExecutor


class UnitaryGateFolder:
    """
    Implements digital unitary gate folding for Zero-Noise Extrapolation.
    For CNOT gates: CX is self-inverse (CX = CX^dagger, CX * CX = I).
    Therefore, replacing CX with CX * (CX * CX)^k preserves the exact logical unitary
    while scaling physical noise by scale factor r = 2k + 1.
    """

    @staticmethod
    def fold_circuit(circuit: QuantumCircuit, scale_factor: int = 1) -> QuantumCircuit:
        """
        scale_factor must be an odd integer (1, 3, 5...).
        r = 1: original circuit
        r = 3: each CX -> CX CX CX (k=1)
        r = 5: each CX -> CX CX CX CX CX (k=2)
        """
        if scale_factor < 1 or scale_factor % 2 == 0:
            raise ValueError(f"Scale factor must be an odd positive integer (1, 3, 5...), got {scale_factor}")

        k = (scale_factor - 1) // 2
        folded = QuantumCircuit(circuit.num_qubits, f"{circuit.name}_folded_r{scale_factor}")

        for name, qubits, params in circuit.instructions:
            if name == "cx":
                c, t = qubits[0], qubits[1]
                # Emit (2k + 1) CX gates
                for _ in range(2 * k + 1):
                    folded.cx(c, t)
            elif name == "swap":
                q1, q2 = qubits[0], qubits[1]
                for _ in range(2 * k + 1):
                    folded.swap(q1, q2)
            else:
                # 1Q gates copied as-is or scaled accordingly
                if name == "h":
                    folded.h(qubits[0])
                elif name == "x":
                    folded.x(qubits[0])
                elif name == "y":
                    folded.y(qubits[0])
                elif name == "z":
                    folded.z(qubits[0])
                elif name == "sx":
                    folded.sx(qubits[0])
                elif name == "rx":
                    folded.rx(params[0], qubits[0])
                elif name == "ry":
                    folded.ry(params[0], qubits[0])
                elif name == "rz":
                    folded.rz(params[0], qubits[0])

        return folded


class ReadoutMitigator:
    """
    Inverts the physical measurement assignment matrix M with probability simplex projection.
    """

    def __init__(self, noise_model: CalibratedNoiseModel, num_qubits: int):
        self.noise_model = noise_model
        self.num_qubits = num_qubits
        self.dim = 1 << num_qubits
        self.calibration_matrix = noise_model.get_readout_calibration_matrix(num_qubits)
        self.inv_matrix = self._invert_matrix(self.calibration_matrix)

    def _invert_matrix(self, matrix: List[List[float]]) -> List[List[float]]:
        """Computes matrix inverse via Gauss-Jordan elimination."""
        n = len(matrix)
        # Augment with identity
        aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(matrix)]

        for col in range(n):
            # Pivot
            pivot_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
            aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
            pivot = aug[col][col]
            if abs(pivot) < 1e-12:
                pivot = 1e-12

            for j in range(2 * n):
                aug[col][j] /= pivot

            for r in range(n):
                if r != col:
                    factor = aug[r][col]
                    for j in range(2 * n):
                        aug[r][j] -= factor * aug[col][j]

        inv = [row[n:] for row in aug]
        return inv

    def project_to_simplex(self, vector: List[float]) -> List[float]:
        """
        Projects arbitrary real vector onto the probability simplex:
        min ||q - v||^2  subject to sum(q) = 1, q_i >= 0.
        Uses the deterministic Michelot-Duchi projection algorithm.
        """
        sorted_v = sorted(vector, reverse=True)
        dim = len(vector)
        cumsum = 0.0
        rho = 0
        for i, val in enumerate(sorted_v):
            cumsum += val
            theta = (cumsum - 1.0) / (i + 1)
            if val > theta:
                rho = i

        cumsum = sum(sorted_v[: rho + 1])
        theta = (cumsum - 1.0) / (rho + 1)
        projected = [max(0.0, x - theta) for x in vector]
        total = sum(projected)
        if total > 0.0:
            projected = [p / total for p in projected]
        return projected

    def mitigate_counts(self, noisy_counts: Dict[str, int]) -> Tuple[Dict[str, float], float]:
        """
        Applies inverse calibration matrix and simplex projection to observed shot counts.
        Returns mitigated probability distribution and mitigated expectation <Z0>.
        """
        total_shots = sum(noisy_counts.values())
        if total_shots == 0:
            return {}, 0.0

        p_obs = [0.0] * self.dim
        for b_str, count in noisy_counts.items():
            idx = int(b_str, 2)
            if idx < self.dim:
                p_obs[idx] = count / total_shots

        # Matrix multiply inv_matrix * p_obs
        p_raw = [0.0] * self.dim
        for i in range(self.dim):
            p_raw[i] = sum(self.inv_matrix[i][j] * p_obs[j] for j in range(self.dim))

        p_mitigated = self.project_to_simplex(p_raw)

        # Reconstruct expectation <Z_0>
        exp_z0 = 0.0
        mitigated_dict: Dict[str, float] = {}
        for idx, p in enumerate(p_mitigated):
            b_str = format(idx, f"0{self.num_qubits}b")
            mitigated_dict[b_str] = round(p, 6)
            bit0 = int(b_str[-1])
            sign = 1.0 if bit0 == 0 else -1.0
            exp_z0 += sign * p

        return mitigated_dict, round(exp_z0, 5)


class ZeroNoiseExtrapolator:
    """
    Executes circuits across scale factors r in {1, 3, 5} and extrapolates to r=0.
    """

    @staticmethod
    def richardson_extrapolate(scale_factors: List[int], values: List[float]) -> float:
        """
        Applies Richardson extrapolation for noise scale factors r = [1, 3, 5]:
        E(0) = (15/8)*E(1) - (10/8)*E(3) + (3/8)*E(5).
        """
        if scale_factors == [1, 3, 5]:
            e0 = (15.0 / 8.0) * values[0] - (10.0 / 8.0) * values[1] + (3.0 / 8.0) * values[2]
            return max(-1.0, min(1.0, e0))

        # General Richardson extrapolation via polynomial regression
        n = len(scale_factors)
        if n == 1:
            return values[0]
        if n == 2:
            r1, r2 = scale_factors[0], scale_factors[1]
            e0 = (r2 * values[0] - r1 * values[1]) / (r2 - r1)
            return max(-1.0, min(1.0, e0))

        # Quadratic polynomial fit at x=0
        r1, r2, r3 = scale_factors[0], scale_factors[1], scale_factors[2]
        v1, v2, v3 = values[0], values[1], values[2]
        # Lagrange interpolation at x=0
        l1 = (0 - r2) * (0 - r3) / ((r1 - r2) * (r1 - r3))
        l2 = (0 - r1) * (0 - r3) / ((r2 - r1) * (r2 - r3))
        l3 = (0 - r1) * (0 - r2) / ((r3 - r1) * (r3 - r2))
        e0 = l1 * v1 + l2 * v2 + l3 * v3
        return max(-1.0, min(1.0, e0))


class QuantumMitigationEngine:
    """
    Unified manager executing unmitigated, ZNE, Readout, and Dual-Layer mitigation workflows.
    """

    def __init__(self, noise_model: CalibratedNoiseModel):
        self.noise_model = noise_model
        self.executor = NoisyCircuitExecutor(noise_model)

    def run_mitigated(
        self,
        circuit: QuantumCircuit,
        method: str = "dual",  # "none", "zne", "readout", "dual"
        shots: int = 1024,
        scale_factors: List[int] = [1, 3, 5],
        seed: Optional[int] = None,
        num_active_qubits: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Runs experiment under requested mitigation strategy.
        Tracks total circuits executed and calibration shots used.
        """
        active_q = num_active_qubits if num_active_qubits is not None else circuit.num_qubits
        rem = ReadoutMitigator(self.noise_model, active_q)

        if method == "none":
            res = self.executor.run(circuit, shots=shots, seed=seed)
            return {
                "method": "Unmitigated Noisy",
                "expectation_z0": res["expectation_z0"],
                "counts": res["counts"],
                "circuits_executed": 1,
                "total_shots": shots,
                "calibration_shots": 0,
                "scale_factors": [1],
                "measured_curve": [res["expectation_z0"]],
            }

        elif method == "readout":
            res = self.executor.run(circuit, shots=shots, seed=seed)
            mitigated_counts, mit_exp = rem.mitigate_counts(res["counts"])
            return {
                "method": "Readout Error Mitigation (REM)",
                "expectation_z0": mit_exp,
                "counts": mitigated_counts,
                "circuits_executed": 1,
                "total_shots": shots,
                "calibration_shots": 1 << active_q,
                "scale_factors": [1],
                "measured_curve": [mit_exp],
            }

        elif method == "zne":
            curves = []
            total_shots = 0
            for r in scale_factors:
                folded_c = UnitaryGateFolder.fold_circuit(circuit, scale_factor=r)
                r_res = self.executor.run(folded_c, shots=shots, seed=seed)
                curves.append(r_res["expectation_z0"])
                total_shots += shots

            extrapolated_e0 = ZeroNoiseExtrapolator.richardson_extrapolate(scale_factors, curves)
            return {
                "method": "Zero-Noise Extrapolation (ZNE)",
                "expectation_z0": round(extrapolated_e0, 5),
                "circuits_executed": len(scale_factors),
                "total_shots": total_shots,
                "calibration_shots": 0,
                "scale_factors": scale_factors,
                "measured_curve": [round(c, 5) for c in curves],
            }

        elif method == "dual":
            curves = []
            total_shots = 0
            for r in scale_factors:
                folded_c = UnitaryGateFolder.fold_circuit(circuit, scale_factor=r)
                r_res = self.executor.run(folded_c, shots=shots, seed=seed)
                _, mit_exp = rem.mitigate_counts(r_res["counts"])
                curves.append(mit_exp)
                total_shots += shots

            extrapolated_e0 = ZeroNoiseExtrapolator.richardson_extrapolate(scale_factors, curves)
            return {
                "method": "Dual-Layer (ZNE + REM)",
                "expectation_z0": round(extrapolated_e0, 5),
                "circuits_executed": len(scale_factors),
                "total_shots": total_shots,
                "calibration_shots": 1 << active_q,
                "scale_factors": scale_factors,
                "measured_curve": [round(c, 5) for c in curves],
            }

        else:
            raise ValueError(f"Unknown mitigation method: {method}")


if __name__ == "__main__":
    qc = QuantumCircuit(4, "mitigation_test")
    for q in range(4):
        qc.ry(1.2, q)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)

    # Ideal expectation
    from src.quantum_core import StatevectorSimulator
    sim = StatevectorSimulator(4)
    sim.execute_circuit(qc)
    ideal_exp = sim.expectation_value_z(0)

    noise = CalibratedNoiseModel(p_1q=0.001, p_2q=0.008, p_ro_01=0.02, p_ro_10=0.02)
    engine = QuantumMitigationEngine(noise)

    res_none = engine.run_mitigated(qc, method="none", shots=2048, seed=42)
    res_ro = engine.run_mitigated(qc, method="readout", shots=2048, seed=42)
    res_zne = engine.run_mitigated(qc, method="zne", shots=2048, seed=42)
    res_dual = engine.run_mitigated(qc, method="dual", shots=2048, seed=42)

    print(f"Ideal <Z0>:                 {round(ideal_exp, 5)}")
    print(f"Unmitigated Noisy <Z0>:     {res_none['expectation_z0']} (Error = {abs(res_none['expectation_z0'] - ideal_exp):.5f})")
    print(f"Readout Mitigated <Z0>:     {res_ro['expectation_z0']} (Error = {abs(res_ro['expectation_z0'] - ideal_exp):.5f})")
    print(f"ZNE Mitigated <Z0>:         {res_zne['expectation_z0']} (Error = {abs(res_zne['expectation_z0'] - ideal_exp):.5f})")
    print(f"Dual (ZNE + Readout) <Z0>:  {res_dual['expectation_z0']} (Error = {abs(res_dual['expectation_z0'] - ideal_exp):.5f})")
    print(f"Extra circuits executed:    {res_dual['circuits_executed']}, total shots: {res_dual['total_shots']}")
