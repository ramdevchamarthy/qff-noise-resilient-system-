"""
Variational Quantum Classifier (VQC) Engine for QFF 2026 PS-Q3.
Implements:
  - 4-qubit Quantum Feature Map (Angle Encoding of biomedical ECG biomarkers)
  - Parameterized Variational Ansatz (Hardware-efficient SU(2) rotations + entanglers)
  - Classical training on ideal simulator using parameter-shift/finite differences
  - Classical baseline models (Logistic Regression & Linear Classifier)
  - Multi-processor hardware execution and error mitigation evaluation
"""

import math
import random
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

from src.quantum_core import QuantumCircuit, StatevectorSimulator
from src.processors import load_processor, QuantumProcessor
from src.transpiler import Transpiler
from src.noise_models import CalibratedNoiseModel, NoisyCircuitExecutor
from src.mitigation import QuantumMitigationEngine, ReadoutMitigator, ZeroNoiseExtrapolator
from src.metrics import compute_classification_metrics, compute_architecture_metrics

WEIGHTS_FILE = Path(__file__).resolve().parent.parent / "data" / "processed" / "trained_vqc_weights.json"


def build_vqc_circuit(features: List[float], weights: List[float], num_qubits: int = 4, layers: int = 2) -> QuantumCircuit:
    """
    Constructs logical quantum circuit for a given feature vector and variational weights.
    features: 4 clinical features in [0, pi].
    weights: 2 * layers * num_qubits parameters (RY and RZ angles).
    """
    qc = QuantumCircuit(num_qubits, "vqc_cardiac_classifier")

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

    return qc


class ClassicalLogisticRegression:
    """
    Classical Logistic Regression baseline trained on identical features and data split.
    """

    def __init__(self, num_features: int = 4):
        self.weights = [0.0] * num_features
        self.bias = 0.0

    def fit(self, X: List[List[float]], y: List[int], epochs: int = 150, lr: float = 0.05, seed: int = 42):
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
    Full Variational Quantum Classifier with support for ideal simulation,
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
        """Runs ideal statevector inference on a single sample."""
        qc = build_vqc_circuit(features, self.weights, self.num_qubits, self.layers)
        sim = StatevectorSimulator(self.num_qubits)
        sim.execute_circuit(qc)
        exp_z0 = sim.expectation_value_z(0)
        prob = max(0.0, min(1.0, (1.0 - exp_z0) / 2.0))
        pred = 1 if prob >= 0.5 else 0
        return prob, pred

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
        lr: float = 0.25,
        seed: int = 42,
        **kwargs
    ) -> List[float]:
        """
        Trains VQC weights on ideal simulator using Simultaneous Perturbation
        Stochastic Approximation (SPSA), the standard optimizer for variational circuits.
        """
        self.initialize_weights(seed=seed)
        rng = random.Random(seed)
        n = len(X_train)
        loss_history = []
        best_loss = 999.0
        best_weights = list(self.weights)

        # SPSA hyperparameters
        a = 0.25
        c = 0.12
        alpha = 0.602
        gamma = 0.101

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
        processor: Optional[QuantumProcessor] = None,
        noise_model: Optional[CalibratedNoiseModel] = None,
        mitigation_method: str = "none",  # "none", "zne", "readout", "dual"
        shots: int = 1024,
        seed: Optional[int] = 42
    ) -> Dict[str, Any]:
        """
        Evaluates test dataset under specified processor and mitigation conditions.
        """
        start_t = time.time()
        y_probs = []
        y_preds = []
        circuits_executed_total = 0
        total_shots = 0

        # Pre-transpile once to obtain exact physical hardware operations and SWAP counts
        sample_logical = build_vqc_circuit(X_test[0], self.weights, self.num_qubits, self.layers)
        transpile_metrics = {
            "transpiled_depth": sample_logical.depth(),
            "algorithmic_cx": 4 * self.layers,
            "swap_count": 0,
            "total_physical_cx": 4 * self.layers,
            "physical_qubits": self.num_qubits,
        }
        if processor is not None:
            transpiler = Transpiler(processor)
            _, transpile_metrics = transpiler.transpile(sample_logical)

        phys_cx = transpile_metrics["total_physical_cx"]
        phys_1q = sum(cnt for op, cnt in sample_logical.count_ops().items() if op not in ["cx", "swap"])
        rem = ReadoutMitigator(noise_model, self.num_qubits) if noise_model else None

        for i, x in enumerate(X_test):
            sample_seed = (seed + i) if seed is not None else None
            rng = random.Random(sample_seed)
            logical_qc = build_vqc_circuit(x, self.weights, self.num_qubits, self.layers)

            # Compute ideal statevector for this sample
            sim = StatevectorSimulator(self.num_qubits)
            sim.execute_circuit(logical_qc)
            ideal_probs = sim.probabilities()
            ideal_exp = sim.expectation_value_z(0)

            if noise_model is None or mitigation_method == "ideal":
                exp_val = ideal_exp
                circuits_executed_total += 1
                total_shots += shots
            else:
                dim = 1 << self.num_qubits
                mixed_p = 1.0 / dim

                if mitigation_method == "none":
                    # Unmitigated on physical processor with routing CX noise
                    F_gate = ((1.0 - noise_model.p_1q) ** phys_1q) * ((1.0 - noise_model.p_2q) ** phys_cx)
                    p_noisy = [F_gate * p + (1.0 - F_gate) * mixed_p for p in ideal_probs]
                    cal_matrix = noise_model.get_readout_calibration_matrix(self.num_qubits)
                    p_dev = [sum(cal_matrix[r][c] * p_noisy[c] for c in range(dim)) for r in range(dim)]
                    p_dev = [max(0.0, p) for p in p_dev]
                    tot = sum(p_dev)
                    p_dev = [p / tot for p in p_dev] if tot > 0 else p_dev
                    counts = sim.sample_counts(shots=shots, seed=sample_seed)
                    # Sample with noise
                    indices = rng.choices(range(dim), weights=p_dev, k=shots)
                    n_counts: Dict[str, int] = {}
                    for idx in indices:
                        b_str = format(idx, f"0{self.num_qubits}b")
                        n_counts[b_str] = n_counts.get(b_str, 0) + 1
                    exp_val = sum((1.0 if int(b[-1]) == 0 else -1.0) * (c / shots) for b, c in n_counts.items())
                    circuits_executed_total += 1
                    total_shots += shots

                elif mitigation_method == "readout":
                    F_gate = ((1.0 - noise_model.p_1q) ** phys_1q) * ((1.0 - noise_model.p_2q) ** phys_cx)
                    p_noisy = [F_gate * p + (1.0 - F_gate) * mixed_p for p in ideal_probs]
                    cal_matrix = noise_model.get_readout_calibration_matrix(self.num_qubits)
                    p_dev = [sum(cal_matrix[r][c] * p_noisy[c] for c in range(dim)) for r in range(dim)]
                    indices = rng.choices(range(dim), weights=p_dev, k=shots)
                    n_counts: Dict[str, int] = {}
                    for idx in indices:
                        b_str = format(idx, f"0{self.num_qubits}b")
                        n_counts[b_str] = n_counts.get(b_str, 0) + 1
                    _, exp_val = rem.mitigate_counts(n_counts)
                    circuits_executed_total += 1
                    total_shots += shots

                elif mitigation_method == "zne":
                    # Evaluate at scale factors r in [1, 3, 5]
                    zne_curves = []
                    for r in [1, 3, 5]:
                        r_cx = r * phys_cx
                        F_r = ((1.0 - noise_model.p_1q) ** phys_1q) * ((1.0 - noise_model.p_2q) ** r_cx)
                        p_r = [F_r * p + (1.0 - F_r) * mixed_p for p in ideal_probs]
                        cal_matrix = noise_model.get_readout_calibration_matrix(self.num_qubits)
                        p_dev = [sum(cal_matrix[row][c] * p_r[c] for c in range(dim)) for row in range(dim)]
                        indices = rng.choices(range(dim), weights=p_dev, k=shots)
                        r_counts: Dict[str, int] = {}
                        for idx in indices:
                            b_str = format(idx, f"0{self.num_qubits}b")
                            r_counts[b_str] = r_counts.get(b_str, 0) + 1
                        r_exp = sum((1.0 if int(b[-1]) == 0 else -1.0) * (c / shots) for b, c in r_counts.items())
                        zne_curves.append(r_exp)
                    from src.mitigation import ZeroNoiseExtrapolator
                    exp_val = ZeroNoiseExtrapolator.richardson_extrapolate([1, 3, 5], zne_curves)
                    circuits_executed_total += 3
                    total_shots += 3 * shots

                elif mitigation_method == "dual":
                    # Dual: Readout mitigation on each folded run + Richardson ZNE
                    zne_curves = []
                    for r in [1, 3, 5]:
                        r_cx = r * phys_cx
                        F_r = ((1.0 - noise_model.p_1q) ** phys_1q) * ((1.0 - noise_model.p_2q) ** r_cx)
                        p_r = [F_r * p + (1.0 - F_r) * mixed_p for p in ideal_probs]
                        cal_matrix = noise_model.get_readout_calibration_matrix(self.num_qubits)
                        p_dev = [sum(cal_matrix[row][c] * p_r[c] for c in range(dim)) for row in range(dim)]
                        indices = rng.choices(range(dim), weights=p_dev, k=shots)
                        r_counts: Dict[str, int] = {}
                        for idx in indices:
                            b_str = format(idx, f"0{self.num_qubits}b")
                            r_counts[b_str] = r_counts.get(b_str, 0) + 1
                        _, r_exp_mit = rem.mitigate_counts(r_counts)
                        zne_curves.append(r_exp_mit)
                    from src.mitigation import ZeroNoiseExtrapolator
                    exp_val = ZeroNoiseExtrapolator.richardson_extrapolate([1, 3, 5], zne_curves)
                    circuits_executed_total += 3
                    total_shots += 3 * shots

            # Clinical decision boundary: P(arrhythmia) >= 0.5
            p_arrhythmia = max(0.0, min(1.0, (1.0 - exp_val) / 2.0))
            pred = 1 if p_arrhythmia >= 0.5 else 0
            y_probs.append(round(p_arrhythmia, 4))
            y_preds.append(pred)

        latency_ms = (time.time() - start_t) * 1000.0
        ml_metrics = compute_classification_metrics(y_test, y_preds, y_probs)

        return {
            "ml_metrics": ml_metrics,
            "architecture_metrics": {
                "processor_name": processor.name if processor else "Ideal Statevector Simulator",
                "physical_qubits": processor.num_qubits if processor else self.num_qubits,
                "circuit_depth": transpile_metrics.get("transpiled_depth", sample_logical.depth()),
                "algorithmic_cx": transpile_metrics.get("algorithmic_cx", 4 * self.layers),
                "swap_count": transpile_metrics.get("swap_count", 0),
                "total_physical_cx": transpile_metrics.get("total_physical_cx", 4 * self.layers),
                "circuits_executed": circuits_executed_total,
                "total_shots": total_shots,
                "latency_ms": round(latency_ms, 2),
            },
            "mitigation_method": mitigation_method,
            "predictions": y_preds,
            "probabilities": y_probs,
        }


def run_full_benchmark_suite() -> Dict[str, Any]:
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

    raw_samples = generate_ecg_dataset(250, seed=42)
    split = get_train_test_split(raw_samples, train_ratio=0.8, seed=42)
    X_train, y_train = split["X_train"], split["y_train"]
    X_test, y_test = split["X_test"], split["y_test"]

    # 1. Classical Baseline
    clf = ClassicalLogisticRegression(4)
    clf.fit(X_train, y_train, epochs=150, lr=0.08, seed=42)
    y_pred_cls = clf.predict(X_test)
    y_prob_cls = clf.predict_proba(X_test)
    cls_metrics = compute_classification_metrics(y_test, y_pred_cls, y_prob_cls)

    # 2. VQC Model
    vqc = VariationalQuantumClassifier(num_qubits=4, layers=2)
    if not vqc.load_weights():
        print("Training VQC on ideal simulator...")
        vqc.fit_ideal(X_train, y_train, epochs=25, lr=0.15, seed=42)

    procs = load_all_processors()
    proc_a = procs["A"]
    proc_b = procs["B"]

    noise_a = CalibratedNoiseModel.from_processor(proc_a.get_stats())
    noise_b = CalibratedNoiseModel.from_processor(proc_b.get_stats())

    print("Running Ideal Reference...")
    res_ideal = vqc.evaluate_batch(X_test, y_test, mitigation_method="ideal")

    print("Running Processor A (Unmitigated)...")
    res_a_unmit = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_a, mitigation_method="none")

    print("Running Processor A (Dual Mitigated)...")
    res_a_mit = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_a, mitigation_method="dual")

    print("Running Processor B (Unmitigated)...")
    res_b_unmit = vqc.evaluate_batch(X_test, y_test, processor=proc_b, noise_model=noise_b, mitigation_method="none")

    print("Running Processor B (Dual Mitigated)...")
    res_b_mit = vqc.evaluate_batch(X_test, y_test, processor=proc_b, noise_model=noise_b, mitigation_method="dual")

    return {
        "classical_baseline": {"ml_metrics": cls_metrics, "name": "Classical Logistic Regression"},
        "ideal_vqc": res_ideal,
        "processor_a_unmitigated": res_a_unmit,
        "processor_a_mitigated": res_a_mit,
        "processor_b_unmitigated": res_b_unmit,
        "processor_b_mitigated": res_b_mit,
    }


if __name__ == "__main__":
    results = run_full_benchmark_suite()
    print("\n================== FULL BENCHMARK SUMMARY ==================")
    print(f"Classical Baseline:   Acc={results['classical_baseline']['ml_metrics']['accuracy']}, Recall={results['classical_baseline']['ml_metrics']['recall']}")
    print(f"Ideal VQC:            Acc={results['ideal_vqc']['ml_metrics']['accuracy']}, Recall={results['ideal_vqc']['ml_metrics']['recall']}")
    print(f"Processor A (Noisy):  Acc={results['processor_a_unmitigated']['ml_metrics']['accuracy']}, Recall={results['processor_a_unmitigated']['ml_metrics']['recall']}")
    print(f"Processor A (Dual):   Acc={results['processor_a_mitigated']['ml_metrics']['accuracy']}, Recall={results['processor_a_mitigated']['ml_metrics']['recall']}")
    print(f"Processor B (Noisy):  Acc={results['processor_b_unmitigated']['ml_metrics']['accuracy']}, Recall={results['processor_b_unmitigated']['ml_metrics']['recall']}")
    print(f"Processor B (Dual):   Acc={results['processor_b_mitigated']['ml_metrics']['accuracy']}, Recall={results['processor_b_mitigated']['ml_metrics']['recall']}")
