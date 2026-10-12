"""
Calibrated Quantum Noise Modeling Engine for QFF 2026.
Simulates realistic NISQ physical imperfections:
  - 1-qubit gate depolarizing error (p_1q ~ 0.1%)
  - 2-qubit CX gate depolarizing error (p_2q ~ 0.5%)
  - Readout / measurement assignment error (p_ro ~ 1.5%)
Supports parameterized noise intensity sweeps for the Robustness Lab.
"""

import random
from typing import Dict, List, Tuple, Any, Optional
from src.quantum_core import QuantumCircuit, StatevectorSimulator


class CalibratedNoiseModel:
    """
    Hardware-calibrated noise model according to QFF 2026 specifications.
    """

    def __init__(
        self,
        p_1q: float = 0.001,
        p_2q: float = 0.005,
        p_ro_01: float = 0.015,
        p_ro_10: float = 0.015,
        name: str = "calibrated_device_noise"
    ):
        self.p_1q = max(0.0, min(1.0, p_1q))
        self.p_2q = max(0.0, min(1.0, p_2q))
        self.p_ro_01 = max(0.0, min(1.0, p_ro_01))
        self.p_ro_10 = max(0.0, min(1.0, p_ro_10))
        self.name = name

    @classmethod
    def from_processor(cls, processor_dict: Dict[str, Any], intensity_multiplier: float = 1.0) -> 'CalibratedNoiseModel':
        cal = processor_dict.get("noise_calibration", {})
        p1 = cal.get("single_qubit_depolarizing_rate", 0.001) * intensity_multiplier
        p2 = cal.get("two_qubit_depolarizing_rate", 0.005) * intensity_multiplier
        ro01 = cal.get("readout_error_rate_01", 0.015) * intensity_multiplier
        ro10 = cal.get("readout_error_rate_10", 0.015) * intensity_multiplier
        return cls(p_1q=p1, p_2q=p2, p_ro_01=ro01, p_ro_10=ro10, name=f"{processor_dict.get('name', 'Proc')}_noise")

    @classmethod
    def ideal(cls) -> 'CalibratedNoiseModel':
        return cls(p_1q=0.0, p_2q=0.0, p_ro_01=0.0, p_ro_10=0.0, name="ideal_reference")

    def apply_readout_noise_to_bitstring(self, bitstring: str, rng: random.Random) -> str:
        """Applies independent asymmetric bit-flip noise to measurement outcomes."""
        noisy_bits = []
        for bit in bitstring:
            if bit == '0':
                # 0 flips to 1 with probability p_ro_10
                flipped = '1' if rng.random() < self.p_ro_10 else '0'
            else:
                # 1 flips to 0 with probability p_ro_01
                flipped = '0' if rng.random() < self.p_ro_01 else '1'
            noisy_bits.append(flipped)
        return "".join(noisy_bits)

    def apply_readout_noise_to_counts(self, ideal_counts: Dict[str, int], seed: Optional[int] = None) -> Dict[str, int]:
        """Perturbs raw shot measurement counts via readout confusion matrix."""
        if self.p_ro_01 == 0.0 and self.p_ro_10 == 0.0:
            return dict(ideal_counts)

        rng = random.Random(seed)
        noisy_counts: Dict[str, int] = {}

        for bitstring, count in ideal_counts.items():
            for _ in range(count):
                noisy_bits = self.apply_readout_noise_to_bitstring(bitstring, rng)
                noisy_counts[noisy_bits] = noisy_counts.get(noisy_bits, 0) + 1

        return noisy_counts

    def get_readout_calibration_matrix(self, num_qubits: int) -> List[List[float]]:
        """
        Computes the theoretical / calibrated 2^n x 2^n assignment matrix M:
        M[i][j] = P(measure bitstring i | prepared bitstring j).
        """
        dim = 1 << num_qubits
        matrix = [[0.0] * dim for _ in range(dim)]

        for j in range(dim):
            prep_bits = format(j, f"0{num_qubits}b")
            for i in range(dim):
                meas_bits = format(i, f"0{num_qubits}b")
                # Transition probability is product of single-qubit probabilities
                prob = 1.0
                for p_bit, m_bit in zip(prep_bits, meas_bits):
                    if p_bit == '0':
                        prob *= (1.0 - self.p_ro_10) if m_bit == '0' else self.p_ro_10
                    else:
                        prob *= (1.0 - self.p_ro_01) if m_bit == '1' else self.p_ro_01
                matrix[i][j] = prob

        return matrix


class NoisyCircuitExecutor:
    """
    Executes a quantum circuit under the specified CalibratedNoiseModel.
    Simulates stochastic gate depolarization and readout distortion.
    """

    def __init__(self, noise_model: CalibratedNoiseModel):
        self.noise_model = noise_model

    def run(
        self,
        circuit: QuantumCircuit,
        shots: int = 1024,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes circuit with gate depolarizing effects and readout errors.
        """
        rng = random.Random(seed)
        num_qubits = circuit.num_qubits
        dim = 1 << num_qubits

        # In NISQ execution, depolarizing gate error causes exponential fidelity decay
        # with gate depth and two-qubit gate counts.
        # Total gate depolarizing fidelity: F_gate = (1 - p_1q)^N_1q * (1 - p_2q)^N_2q
        op_counts = circuit.count_ops()
        n_2q = op_counts.get("cx", 0) + 3 * op_counts.get("swap", 0)
        n_1q = sum(cnt for op, cnt in op_counts.items() if op not in ["cx", "swap"])

        gate_fidelity = ((1.0 - self.noise_model.p_1q) ** n_1q) * ((1.0 - self.noise_model.p_2q) ** n_2q)

        # 1. Compute ideal statevector
        sim = StatevectorSimulator(num_qubits)
        sim.execute_circuit(circuit)
        ideal_probs = sim.probabilities()

        # 2. Mix with maximally mixed state I / 2^n according to gate depolarizing fidelity
        mixed_prob = 1.0 / dim
        noisy_probs = [
            gate_fidelity * p + (1.0 - gate_fidelity) * mixed_prob
            for p in ideal_probs
        ]

        # 3. Apply readout transition matrix to noisy probabilities: p_device = M * p_noisy
        cal_matrix = self.noise_model.get_readout_calibration_matrix(num_qubits)
        final_probs = [0.0] * dim
        for i in range(dim):
            final_probs[i] = sum(cal_matrix[i][j] * noisy_probs[j] for j in range(dim))

        # Normalize to ensure sum to 1.0
        tot_p = sum(final_probs)
        if tot_p > 0:
            final_probs = [p / tot_p for p in final_probs]

        # 4. Fast shot sampling using random.choices
        sampled_indices = rng.choices(range(dim), weights=final_probs, k=shots)
        final_counts: Dict[str, int] = {}
        for idx in sampled_indices:
            b_str = format(idx, f"0{num_qubits}b")
            final_counts[b_str] = final_counts.get(b_str, 0) + 1

        # Reconstructed expectation value <Z_0>
        total_shots = shots
        exp_z0 = 0.0
        for b_str, count in final_counts.items():
            bit0 = int(b_str[-1])
            sign = 1.0 if bit0 == 0 else -1.0
            exp_z0 += sign * (count / total_shots)

        return {
            "counts": final_counts,
            "shots": total_shots,
            "gate_fidelity": round(gate_fidelity, 5),
            "expectation_z0": round(exp_z0, 5),
            "n_1q_gates": n_1q,
            "n_2q_gates": n_2q,
            "noise_model": self.noise_model.name,
        }


if __name__ == "__main__":
    qc = QuantumCircuit(4, "noise_test")
    for q in range(4):
        qc.ry(1.0, q)
    qc.cx(0, 1)
    qc.cx(2, 3)

    noise = CalibratedNoiseModel(p_1q=0.001, p_2q=0.005, p_ro_01=0.015, p_ro_10=0.015)
    executor = NoisyCircuitExecutor(noise)
    res = executor.run(qc, shots=2048, seed=42)
    print("Noisy Execution Result:")
    print("Gate Fidelity:", res["gate_fidelity"])
    print("Expectation <Z0>:", res["expectation_z0"])
    print("Sample Count Keys:", len(res["counts"]))
