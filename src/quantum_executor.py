"""
Quantum Execution Engine using Qiskit Aer.
Executes QuantumCircuit instances under ideal statevector simulation,
ideal finite-shot execution, and calibrated hardware noise models.
"""

from typing import Dict, Any, Optional, Tuple, List
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit.quantum_info import Statevector, SparsePauliOp


class QuantumExecutor:
    """
    Executes circuits via Qiskit Aer with strict accounting of
    circuit instances, simulator submissions, and total shots.
    """

    def __init__(self, noise_model: Optional[NoiseModel] = None, seed_simulator: Optional[int] = 42):
        self.noise_model = noise_model
        self.seed_simulator = seed_simulator
        if noise_model is not None:
            self.sim = AerSimulator(noise_model=noise_model, seed_simulator=seed_simulator)
        else:
            self.sim = AerSimulator(seed_simulator=seed_simulator)

    @staticmethod
    def run_ideal_statevector(circuit: QuantumCircuit, target_qubit: int = 0) -> Tuple[float, float]:
        """
        Computes exact expectation value <Z_target> and probability P(1)
        using analytic Statevector evolution (zero finite-shot sampling error).
        """
        # Exclude measurement operations for statevector calculation if present
        qc_no_meas = circuit.remove_final_measurements(inplace=False) if circuit.num_clbits > 0 else circuit
        sv = Statevector.from_instruction(qc_no_meas)
        
        # Build Pauli Z operator for the target qubit:
        # In Qiskit, qubit index 0 corresponds to rightmost index in Pauli string
        num_q = circuit.num_qubits
        pauli_chars = ["I"] * num_q
        pauli_chars[num_q - 1 - target_qubit] = "Z"
        op_str = "".join(pauli_chars)
        op = SparsePauliOp.from_list([(op_str, 1.0)])
        
        exp_z = float(sv.expectation_value(op).real)
        prob_1 = max(0.0, min(1.0, (1.0 - exp_z) / 2.0))
        return exp_z, prob_1

    def run_shots(
        self,
        circuit: QuantumCircuit,
        shots: int = 1024,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a circuit with finite shot sampling.
        Returns:
            dict containing raw bitstring counts, computed expectation <Z_0>,
            and execution tracking metrics.
        """
        # Ensure circuit has measurements
        qc_exec = circuit.copy()
        if qc_exec.num_clbits == 0:
            qc_exec.measure_all()

        sim_to_use = self.sim
        if seed is not None and seed != self.seed_simulator:
            if self.noise_model is not None:
                sim_to_use = AerSimulator(noise_model=self.noise_model, seed_simulator=seed)
            else:
                sim_to_use = AerSimulator(seed_simulator=seed)

        job = sim_to_use.run(qc_exec, shots=shots)
        result = job.result()
        raw_counts = result.get_counts(qc_exec)

        # In Qiskit counts, bitstrings have qubit 0 at the rightmost index (e.g. "010" -> q0 is '0')
        # Compute <Z_0>:
        # outcome bit for q0 == '0' -> +1
        # outcome bit for q0 == '1' -> -1
        total_shots = sum(raw_counts.values())
        z0_val = 0.0
        for bstr, count in raw_counts.items():
            # Strip spaces if multi-register bitstring
            clean_bstr = bstr.replace(" ", "")
            bit_q0 = clean_bstr[-1]
            sign = 1.0 if bit_q0 == '0' else -1.0
            z0_val += sign * (count / total_shots)

        prob_1 = max(0.0, min(1.0, (1.0 - z0_val) / 2.0))

        return {
            "counts": raw_counts,
            "expectation_z0": round(z0_val, 6),
            "prob_1": round(prob_1, 6),
            "shots": total_shots,
            "circuits_executed": 1,
            "is_noisy": self.noise_model is not None,
        }
