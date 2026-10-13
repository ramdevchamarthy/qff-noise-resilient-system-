"""
Variational Quantum Classifier (VQC) Engine for QFF 2026 PS-Q3 using genuine Qiskit circuits and Qiskit Aer.
Implements:
  - 4-qubit Quantum Feature Map (Angle Encoding into qiskit.QuantumCircuit)
  - Parameterized Variational Ansatz (SU(2) rotations + cyclic CNOT entanglement)
  - Exact Ideal Statevector inference and finite-shot AerSimulator execution
  - Hardware topology transpilation onto Processor A and Processor B
  - Quantum Error Mitigation (Readout mitigation via calibration matrix & ZNE via gate folding)
"""

import math
import random
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

from src.routing import transpile_for_processor
from src.noise import build_qiskit_noise_model
from src.quantum_executor import QuantumExecutor
from src.mitigation import QiskitGateFolder, QiskitReadoutMitigator, ZeroNoiseExtrapolator
from src.metrics import compute_classification_metrics

WEIGHTS_FILE = Path(__file__).resolve().parent.parent / "data" / "processed" / "trained_vqc_weights.json"


def build_vqc_circuit(
    features: List[float],
    weights: List[float],
    num_qubits: int = 4,
    layers: int = 2,
    include_measurements: bool = False
) -> QuantumCircuit:
    """
    Constructs a genuine qiskit.QuantumCircuit for given feature vector and variational weights.
    features: 4 clinical features in [0, pi].
    weights: 2 * layers * num_qubits parameters (RY and RZ angles).
    """
    clbits = num_qubits if include_measurements else 0
    qc = QuantumCircuit(num_qubits, clbits, name="vqc_cardiac_classifier")

    # 1. Feature Map: Hadamard superposition + Angle encoding
    for q in range(num_qubits):
        qc.h(q)
        qc.ry(features[q], q)
        qc.rz(features[q] * 0.5, q)

    # 2. Parameterized Variational Ansatz
    param_idx = 0
    for l in range(layers):
        # Single-qubit parameterized rotations
        for q in range(num_qubits):
            ry_val = weights[param_idx]
            rz_val = weights[param_idx + 1]
            param_idx += 2
            qc.ry(ry_val, q)
            qc.rz(rz_val, q)

        # Entanglement layer (cyclic nearest-neighbor)
        qc.cx(0, 1)
        qc.cx(1, 2)
        qc.cx(2, 3)
        qc.cx(3, 0)

    if include_measurements:
        qc.measure(range(num_qubits), range(num_qubits))

    return qc


class ClassicalLogisticRegression:
    """
    Classical Logistic Regression baseline trained on identical features and data split.
    """

    def __init__(self, num_features: int = 4):
        self.weights = [0.0] * num_features
        self.bias = 0.0

    def fit(self, X: List[List[float]], y: List[int], epochs: int = 150, lr: float = 0.08, seed: int = 42):
        rng = random.Random(seed)
        self.weights = [(rng.random() - 0.5) * 0.2 for _ in range(len(self.weights))]
        self.bias = 0.0
        n = len(X)

        for _ in range(epochs):
            grad_w = [0.0] * len(self.weights)
            grad_b = 0.0
            for i in range(n):
                z = self.bias + sum(self.weights[j] * X[i][j] for j in range(len(self.weights)))
                p = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))
                err = p - y[i]
                for j in range(len(self.weights)):
                    grad_w[j] += err * X[i][j]
                grad_b += err

            for j in range(len(self.weights)):
                self.weights[j] -= lr * (grad_w[j] / n)
            self.bias -= lr * (grad_b / n)

    def predict_proba(self, X: List[List[float]]) -> List[float]:
        probs = []
        for x in X:
            z = self.bias + sum(self.weights[j] * x[j] for j in range(len(self.weights)))
            p = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))
            probs.append(round(p, 5))
        return probs

    def predict(self, X: List[List[float]]) -> List[int]:
        probs = self.predict_proba(X)
        return [1 if p >= 0.5 else 0 for p in probs]


class VariationalQuantumClassifier:
    """
    Full Qiskit-based Variational Quantum Classifier with support for ideal simulation,
    hardware transpilation onto Processors A/B/C, and quantum error mitigation.
    """

    def __init__(self, num_qubits: int = 4, layers: int = 2):
        self.num_qubits = num_qubits
        self.layers = layers
        self.num_params = 2 * layers * num_qubits  # 16 parameters
        self.weights: List[float] = [0.0] * self.num_params

    def initialize_weights(self, seed: int = 42):
        rng = random.Random(seed)
        self.weights = [round(rng.uniform(-math.pi / 2, math.pi / 2), 4) for _ in range(self.num_params)]

    def save_weights(self, path: Path = WEIGHTS_FILE):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "weights": self.weights,
                    "num_qubits": self.num_qubits,
                    "layers": self.layers,
                    "num_params": self.num_params,
                }, f, indent=2)
        except (OSError, PermissionError):
            try:
                from src.storage import get_writable_dir
                fallback_path = get_writable_dir("processed") / "trained_vqc_weights.json"
                with open(fallback_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "weights": self.weights,
                        "num_qubits": self.num_qubits,
                        "layers": self.layers,
                        "num_params": self.num_params,
                    }, f, indent=2)
            except Exception:
                pass

    def load_weights(self, path: Path = WEIGHTS_FILE) -> bool:
        search_paths = [path]
        try:
            from src.storage import get_read_dirs
            for r_dir in get_read_dirs("processed"):
                search_paths.append(r_dir / "trained_vqc_weights.json")
        except Exception:
            pass

        for p in search_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.weights = data["weights"]
                    self.num_qubits = data.get("num_qubits", 4)
                    self.layers = data.get("layers", 2)
                    self.num_params = len(self.weights)
                    return True
                except Exception:
                    continue
        return False

    def predict_single_ideal(self, features: List[float]) -> Tuple[float, int]:
        """Runs ideal statevector inference on a single sample using Qiskit."""
        qc = build_vqc_circuit(features, self.weights, self.num_qubits, self.layers)
        exp_z0, prob_1 = QuantumExecutor.run_ideal_statevector(qc, target_qubit=0)
        pred = 1 if prob_1 >= 0.5 else 0
        return prob_1, pred

    def _loss_on_batch(self, X_batch: List[List[float]], y_batch: List[int], weights: List[float], weight_class_1: float = 1.6) -> float:
        """Computes class-weighted binary cross-entropy loss on a mini-batch."""
        orig_weights = self.weights
        self.weights = weights
        total_loss = 0.0
        n = len(X_batch)
        for i in range(n):
            prob, _ = self.predict_single_ideal(X_batch[i])
            p_safe = max(1e-6, min(1.0 - 1e-6, prob))
            w = weight_class_1 if y_batch[i] == 1 else 1.0
            sample_loss = -w * (y_batch[i] * math.log(p_safe) + (1 - y_batch[i]) * math.log(1.0 - p_safe))
            total_loss += sample_loss
        self.weights = orig_weights
        return total_loss / n

    def fit_ideal(
        self,
        X_train: List[List[float]],
        y_train: List[int],
        epochs: int = 80,
        batch_size: int = 40,
        seed: int = 42,
        **kwargs
    ) -> List[float]:
        """
        Trains VQC weights on ideal simulator using Simultaneous Perturbation Stochastic Approximation (SPSA).
        """
        self.initialize_weights(seed=seed)
        rng = random.Random(seed)
        n = len(X_train)
        loss_history = []
        best_loss = 999.0
        best_weights = list(self.weights)

        a, c = 0.25, 0.12
        alpha, gamma = 0.602, 0.101

        for k in range(epochs):
            indices = list(range(n))
            rng.shuffle(indices)
            batch_idx = indices[:batch_size]
            X_b = [X_train[i] for i in batch_idx]
            y_b = [y_train[i] for i in batch_idx]

            ak = a / ((k + 1) ** alpha)
            ck = c / ((k + 1) ** gamma)

            delta = [rng.choice([-1.0, 1.0]) for _ in range(self.num_params)]
            theta_plus = [self.weights[i] + ck * delta[i] for i in range(self.num_params)]
            theta_minus = [self.weights[i] - ck * delta[i] for i in range(self.num_params)]

            loss_plus = self._loss_on_batch(X_b, y_b, theta_plus)
            loss_minus = self._loss_on_batch(X_b, y_b, theta_minus)

            curr_loss = (loss_plus + loss_minus) / 2.0
            loss_history.append(round(curr_loss, 4))

            if curr_loss < best_loss:
                best_loss = curr_loss
                best_weights = list(self.weights)

            diff = loss_plus - loss_minus
            grad = [diff / (2.0 * ck * delta[i]) for i in range(self.num_params)]

            for i in range(self.num_params):
                step = ak * grad[i]
                step_clipped = max(-0.25, min(0.25, step))
                self.weights[i] = round(self.weights[i] - step_clipped, 5)

        self.weights = best_weights
        self.save_weights()
        return loss_history

    def evaluate_batch(
        self,
        X_test: List[List[float]],
        y_test: List[int],
        processor: Optional[Any] = None,
        noise_model: Optional[Any] = None,
        mitigation_method: str = "none",  # "none", "zne", "readout", "dual", "ideal"
        shots: int = 1024,
        seed: Optional[int] = 42
    ) -> Dict[str, Any]:
        """
        Evaluates test dataset under specified processor and mitigation conditions using genuine Qiskit Aer simulation.
        """
        start_t = time.time()
        y_probs = []
        y_preds = []
        circuits_executed_total = 0
        total_shots = 0

        # Extract processor stats / dictionary
        proc_dict = processor.get_stats() if hasattr(processor, "get_stats") else (processor if isinstance(processor, dict) else None)

        sample_logical = build_vqc_circuit(X_test[0], self.weights, self.num_qubits, self.layers, include_measurements=True)
        if proc_dict is not None:
            _, transpile_metrics = transpile_for_processor(sample_logical, proc_dict, seed_transpiler=seed)
        else:
            transpile_metrics = {
                "transpiled_depth": sample_logical.depth(),
                "algorithmic_cx": 4 * self.layers,
                "swap_count": 0,
                "total_physical_cx": 4 * self.layers,
                "physical_qubits": self.num_qubits,
                "gate_counts": dict(sample_logical.count_ops())
            }

        # Convert noise_model if it's our legacy class or construct Qiskit NoiseModel
        qiskit_noise_model = None
        if noise_model is not None:
            if isinstance(noise_model, NoiseModel):
                qiskit_noise_model = noise_model
            else:
                p2 = getattr(noise_model, "p_2q", None)
                p1 = getattr(noise_model, "p_1q", None)
                pro = getattr(noise_model, "p_ro_01", None)
                if p2 is None and isinstance(noise_model, dict):
                    p2 = noise_model.get("two_qubit_noise_rate", noise_model.get("p_2q"))
                    pro = noise_model.get("readout_noise_rate", noise_model.get("p_ro_01"))
                    p1 = (p2 * 0.2) if p2 is not None else None

                basis = proc_dict.get("basis_gates", ["rz", "sx", "x", "cx"]) if proc_dict else ["rz", "sx", "x", "cx"]
                cal_dict = proc_dict.get("noise_calibration", {}) if proc_dict else {}
                p1 = p1 if p1 is not None else cal_dict.get("single_qubit_depolarizing_rate", 0.001)
                p2 = p2 if p2 is not None else cal_dict.get("two_qubit_depolarizing_rate", 0.005)
                pro = pro if pro is not None else cal_dict.get("readout_error_rate_01", 0.015)

                dummy_proc = {
                    "basis_gates": basis,
                    "noise_calibration": {
                        "single_qubit_depolarizing_rate": p1,
                        "two_qubit_depolarizing_rate": p2,
                        "readout_error_rate_01": pro,
                        "readout_error_rate_10": pro
                    }
                }
                qiskit_noise_model, _ = build_qiskit_noise_model(dummy_proc)

        # Setup executor
        executor = QuantumExecutor(noise_model=qiskit_noise_model, seed_simulator=seed)
        rem = QiskitReadoutMitigator(num_qubits=self.num_qubits, noise_model=qiskit_noise_model, seed_simulator=seed) if (qiskit_noise_model and mitigation_method in ["readout", "dual"]) else None
        cal_circuits = rem.calibration_circuits_count if rem else 0
        cal_shots = rem.calibration_shots_count if rem else 0

        # Evaluate each sample in test set
        for i, x in enumerate(X_test):
            sample_seed = (seed + i) if seed is not None else None
            logical_qc = build_vqc_circuit(x, self.weights, self.num_qubits, self.layers, include_measurements=True)

            if proc_dict is not None:
                transpiled_qc, _ = transpile_for_processor(logical_qc, proc_dict, seed_transpiler=sample_seed)
            else:
                transpiled_qc = logical_qc

            if qiskit_noise_model is None or mitigation_method == "ideal":
                # Ideal reference evaluation on logical circuit
                exp_z, prob_1 = QuantumExecutor.run_ideal_statevector(logical_qc, target_qubit=0)
                circuits_executed_total += 1
                total_shots += shots

            elif mitigation_method == "none":
                # Unmitigated noisy execution
                res = executor.run_shots(transpiled_qc, shots=shots, seed=sample_seed)
                prob_1 = res["prob_1"]
                circuits_executed_total += 1
                total_shots += shots

            elif mitigation_method == "readout":
                # Readout error mitigation only
                res = executor.run_shots(transpiled_qc, shots=shots, seed=sample_seed)
                _, mit_exp = rem.mitigate_counts(res["counts"])
                prob_1 = max(0.0, min(1.0, (1.0 - mit_exp) / 2.0))
                circuits_executed_total += 1
                total_shots += shots

            elif mitigation_method == "zne":
                # ZNE only (r in [1, 3, 5])
                curves = []
                for r in [1, 3, 5]:
                    folded = QiskitGateFolder.fold_circuit(transpiled_qc, scale_factor=r)
                    r_res = executor.run_shots(folded, shots=shots, seed=sample_seed)
                    curves.append(r_res["expectation_z0"])
                    circuits_executed_total += 1
                    total_shots += shots
                extrap_exp = ZeroNoiseExtrapolator.richardson_extrapolate([1, 3, 5], curves)
                prob_1 = max(0.0, min(1.0, (1.0 - extrap_exp) / 2.0))

            elif mitigation_method == "dual":
                # Dual mitigation: Fold -> Readout correct -> Richardson extrapolate
                curves = []
                for r in [1, 3, 5]:
                    folded = QiskitGateFolder.fold_circuit(transpiled_qc, scale_factor=r)
                    r_res = executor.run_shots(folded, shots=shots, seed=sample_seed)
                    _, mit_exp = rem.mitigate_counts(r_res["counts"])
                    curves.append(mit_exp)
                    circuits_executed_total += 1
                    total_shots += shots
                extrap_exp = ZeroNoiseExtrapolator.richardson_extrapolate([1, 3, 5], curves)
                prob_1 = max(0.0, min(1.0, (1.0 - extrap_exp) / 2.0))

            else:
                raise ValueError(f"Unknown mitigation_method: {mitigation_method}")

            pred = 1 if prob_1 >= 0.5 else 0
            y_probs.append(round(prob_1, 6))
            y_preds.append(pred)

        ml_metrics = compute_classification_metrics(y_test, y_preds, y_probs)
        arch_metrics = {
            "circuit_depth": transpile_metrics.get("circuit_depth", 0),
            "algorithmic_cx": transpile_metrics.get("algorithmic_cx", 8),
            "swap_count": transpile_metrics.get("swap_count", 0),
            "total_physical_cx": transpile_metrics.get("total_physical_cx", 8),
            "two_qubit_gate_count": transpile_metrics.get("total_physical_cx", 8),
            "circuits_executed": circuits_executed_total,
            "total_shots": total_shots,
            "calibration_circuits": cal_circuits,
            "calibration_shots": cal_shots,
            "evaluation_time_sec": round(time.time() - start_t, 3),
            "latency_ms": round((time.time() - start_t) * 1000.0, 2),
        }

        return {
            "ml_metrics": ml_metrics,
            "architecture_metrics": arch_metrics,
            "y_probs": y_probs,
            "y_preds": y_preds,
            "probabilities": y_probs,
            "predictions": y_preds,
            "mitigation_method": mitigation_method,
        }


def run_full_benchmark_suite(
    X_test: Optional[List[List[float]]] = None,
    y_test: Optional[List[int]] = None,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Executes the complete QFF 2026 Phase 1 Benchmark across:
      1. Classical Logistic Regression Baseline
      2. Ideal VQC Simulator (Reference)
      3. Processor A: Unmitigated Noisy
      4. Processor A: Dual-Layer Mitigated (ZNE + Readout)
      5. Processor B: Unmitigated Noisy
      6. Processor B: Dual-Layer Mitigated (ZNE + Readout)
    """
    from src.data_loader import generate_ecg_dataset, get_train_test_split
    from src.processors import load_all_processors

    if X_test is None or y_test is None:
        raw_samples = generate_ecg_dataset(250, seed=42)
        split = get_train_test_split(raw_samples, train_ratio=0.8, seed=42)
        X_train, y_train = split["X_train"], split["y_train"]
        X_test, y_test = split["X_test"], split["y_test"]
    else:
        raw_samples = generate_ecg_dataset(250, seed=42)
        split = get_train_test_split(raw_samples, train_ratio=0.8, seed=42)
        X_train, y_train = split["X_train"], split["y_train"]

    # 1. Classical Baseline
    clf = ClassicalLogisticRegression(4)
    clf.fit(X_train, y_train, epochs=150, lr=0.08, seed=42)
    y_pred_cls = clf.predict(X_test)
    y_prob_cls = clf.predict_proba(X_test)
    cls_metrics = compute_classification_metrics(y_test, y_pred_cls, y_prob_cls)

    # 2. VQC Model
    vqc = VariationalQuantumClassifier(num_qubits=4, layers=2)
    vqc.load_weights()

    procs = load_all_processors()
    proc_a = procs["A"]
    proc_b = procs["B"]

    noise_a = proc_a.get_stats()
    noise_b = proc_b.get_stats()

    res_ideal = vqc.evaluate_batch(X_test, y_test, mitigation_method="ideal", seed=seed)
    res_a_unmit = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_a, mitigation_method="none", seed=seed)
    res_a_mit = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_a, mitigation_method="dual", seed=seed)
    res_b_unmit = vqc.evaluate_batch(X_test, y_test, processor=proc_b, noise_model=noise_b, mitigation_method="none", seed=seed)
    res_b_mit = vqc.evaluate_batch(X_test, y_test, processor=proc_b, noise_model=noise_b, mitigation_method="dual", seed=seed)

    return {
        "classical_baseline": {"ml_metrics": cls_metrics, "name": "Classical Logistic Regression"},
        "ideal_vqc": res_ideal,
        "processor_a_unmitigated": res_a_unmit,
        "processor_a_mitigated": res_a_mit,
        "processor_b_unmitigated": res_b_unmit,
        "processor_b_mitigated": res_b_mit,
    }
