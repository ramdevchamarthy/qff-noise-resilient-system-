"""
Quantum Core Simulation Engine.
Implements exact statevector evolution, native quantum gates, expectation values,
and multinomial shot measurement sampling without third-party C-extensions.
"""

import cmath
import math
import random
from typing import List, Tuple, Dict, Any, Optional

ComplexVector = List[complex]


class QuantumCircuit:
    """
    Logical and physical quantum circuit representation.
    Tracks gate sequences, qubit counts, and execution metrics.
    """

    def __init__(self, num_qubits: int, name: str = "qc"):
        self.num_qubits = num_qubits
        self.name = name
        self.instructions: List[Tuple[str, List[int], List[float]]] = []

    def h(self, qubit: int):
        self.instructions.append(("h", [qubit], []))

    def x(self, qubit: int):
        self.instructions.append(("x", [qubit], []))

    def y(self, qubit: int):
        self.instructions.append(("y", [qubit], []))

    def z(self, qubit: int):
        self.instructions.append(("z", [qubit], []))

    def sx(self, qubit: int):
        self.instructions.append(("sx", [qubit], []))

    def rx(self, theta: float, qubit: int):
        self.instructions.append(("rx", [qubit], [theta]))

    def ry(self, theta: float, qubit: int):
        self.instructions.append(("ry", [qubit], [theta]))

    def rz(self, theta: float, qubit: int):
        self.instructions.append(("rz", [qubit], [theta]))

    def cx(self, control: int, target: int):
        self.instructions.append(("cx", [control, target], []))

    def swap(self, q1: int, q2: int):
        self.instructions.append(("swap", [q1, q2], []))

    def count_ops(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for name, _, _ in self.instructions:
            counts[name] = counts.get(name, 0) + 1
        return counts

    def depth(self) -> int:
        """Computes circuit depth (longest dependency path across qubits)."""
        qubit_depths = [0] * self.num_qubits
        for name, qubits, _ in self.instructions:
            max_d = max(qubit_depths[q] for q in qubits)
            new_d = max_d + 1
            for q in qubits:
                qubit_depths[q] = new_d
        return max(qubit_depths) if qubit_depths else 0

    def copy(self) -> 'QuantumCircuit':
        new_qc = QuantumCircuit(self.num_qubits, self.name)
        new_qc.instructions = [
            (name, list(qubits), list(params))
            for name, qubits, params in self.instructions
        ]
        return new_qc


class StatevectorSimulator:
    """
    High-precision complex statevector simulator.
    """

    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.dim = 1 << num_qubits
        self.state: ComplexVector = [complex(0.0, 0.0)] * self.dim
        self.state[0] = complex(1.0, 0.0)  # |00...0>

    def reset(self):
        self.state = [complex(0.0, 0.0)] * self.dim
        self.state[0] = complex(1.0, 0.0)

    def apply_single_qubit_gate(self, u00: complex, u01: complex, u10: complex, u11: complex, qubit: int):
        """Applies a 2x2 unitary matrix to the designated target qubit."""
        step = 1 << qubit
        double_step = step << 1
        for i in range(0, self.dim, double_step):
            for j in range(step):
                idx0 = i + j
                idx1 = idx0 + step
                v0 = self.state[idx0]
                v1 = self.state[idx1]
                self.state[idx0] = u00 * v0 + u01 * v1
                self.state[idx1] = u10 * v0 + u11 * v1

    def apply_h(self, q: int):
        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        self.apply_single_qubit_gate(inv_sqrt2, inv_sqrt2, inv_sqrt2, -inv_sqrt2, q)

    def apply_x(self, q: int):
        self.apply_single_qubit_gate(0.0, 1.0, 1.0, 0.0, q)

    def apply_y(self, q: int):
        self.apply_single_qubit_gate(0.0, complex(0.0, -1.0), complex(0.0, 1.0), 0.0, q)

    def apply_z(self, q: int):
        self.apply_single_qubit_gate(1.0, 0.0, 0.0, -1.0, q)

    def apply_sx(self, q: int):
        # sqrt(X) = 0.5 * [[1+i, 1-i], [1-i, 1+i]]
        half = 0.5
        u00 = complex(half, half)
        u01 = complex(half, -half)
        self.apply_single_qubit_gate(u00, u01, u01, u00, q)

    def apply_rx(self, theta: float, q: int):
        cos_t = math.cos(theta / 2.0)
        sin_t = math.sin(theta / 2.0)
        self.apply_single_qubit_gate(cos_t, complex(0.0, -sin_t), complex(0.0, -sin_t), cos_t, q)

    def apply_ry(self, theta: float, q: int):
        cos_t = math.cos(theta / 2.0)
        sin_t = math.sin(theta / 2.0)
        self.apply_single_qubit_gate(cos_t, -sin_t, sin_t, cos_t, q)

    def apply_rz(self, theta: float, q: int):
        exp_neg = cmath.exp(complex(0.0, -theta / 2.0))
        exp_pos = cmath.exp(complex(0.0, theta / 2.0))
        self.apply_single_qubit_gate(exp_neg, 0.0, 0.0, exp_pos, q)

    def apply_cx(self, control: int, target: int):
        """Applies CNOT with specified control and target qubits."""
        ctrl_mask = 1 << control
        targ_mask = 1 << target
        for idx in range(self.dim):
            if (idx & ctrl_mask) and not (idx & targ_mask):
                flipped_idx = idx | targ_mask
                # Swap amplitudes between |...1...0...> and |...1...1...>
                self.state[idx], self.state[flipped_idx] = self.state[flipped_idx], self.state[idx]

    def apply_swap(self, q1: int, q2: int):
        """Applies SWAP gate between q1 and q2."""
        mask1 = 1 << q1
        mask2 = 1 << q2
        for idx in range(self.dim):
            bit1 = 1 if (idx & mask1) else 0
            bit2 = 1 if (idx & mask2) else 0
            if bit1 != bit2 and bit1 == 1:
                swapped_idx = (idx & ~mask1) | mask2
                self.state[idx], self.state[swapped_idx] = self.state[swapped_idx], self.state[idx]

    def execute_circuit(self, circuit: QuantumCircuit):
        """Runs all instructions in the circuit sequentially."""
        for name, qubits, params in circuit.instructions:
            if name == "h":
                self.apply_h(qubits[0])
            elif name == "x":
                self.apply_x(qubits[0])
            elif name == "y":
                self.apply_y(qubits[0])
            elif name == "z":
                self.apply_z(qubits[0])
            elif name == "sx":
                self.apply_sx(qubits[0])
            elif name == "rx":
                self.apply_rx(params[0], qubits[0])
            elif name == "ry":
                self.apply_ry(params[0], qubits[0])
            elif name == "rz":
                self.apply_rz(params[0], qubits[0])
            elif name == "cx":
                self.apply_cx(qubits[0], qubits[1])
            elif name == "swap":
                self.apply_swap(qubits[0], qubits[1])
            else:
                raise ValueError(f"Unsupported gate instruction: {name}")

    def probabilities(self) -> List[float]:
        """Returns exact analytical probability distribution P(i) = |psi_i|^2."""
        probs = [abs(amp) ** 2 for amp in self.state]
        total = sum(probs)
        if total > 0.0:
            probs = [p / total for p in probs]
        return probs

    def sample_counts(self, shots: int = 1024, seed: Optional[int] = None) -> Dict[str, int]:
        """Samples finite measurement counts in computational basis using fast random sampling."""
        probs = self.probabilities()
        rng = random.Random(seed)
        sampled_indices = rng.choices(range(self.dim), weights=probs, k=shots)
        counts: Dict[str, int] = {}
        for idx in sampled_indices:
            b_str = format(idx, f"0{self.num_qubits}b")
            counts[b_str] = counts.get(b_str, 0) + 1
        return counts

    def expectation_value_z(self, qubit: int) -> float:
        """Calculates <Z_q> directly from statevector."""
        probs = self.probabilities()
        mask = 1 << qubit
        exp_val = 0.0
        for idx, p in enumerate(probs):
            bit = 1 if (idx & mask) else 0
            sign = 1.0 if bit == 0 else -1.0
            exp_val += sign * p
        return exp_val

    def expectation_value_all_z(self) -> float:
        """Calculates parity expectation value <Z_0 Z_1 ... Z_{n-1}>."""
        probs = self.probabilities()
        exp_val = 0.0
        for idx, p in enumerate(probs):
            # Parity of bitstring
            parity = bin(idx).count("1") % 2
            sign = 1.0 if parity == 0 else -1.0
            exp_val += sign * p
        return exp_val


if __name__ == "__main__":
    # Test Bell state |Phi+> = (|00> + |11>) / sqrt(2)
    qc = QuantumCircuit(2, "bell_test")
    qc.h(0)
    qc.cx(0, 1)
    sim = StatevectorSimulator(2)
    sim.execute_circuit(qc)
    probs = sim.probabilities()
    counts = sim.sample_counts(shots=2048, seed=42)
    print("Analytical Bell state probabilities:", [round(p, 4) for p in probs])
    print("Measurement counts (2048 shots):", counts)
    print("<Z0>:", sim.expectation_value_z(0), "<Z1>:", sim.expectation_value_z(1))
    print("<Z0 Z1>:", sim.expectation_value_all_z())
