"""
Scientific Metrics Engine for QFF 2026 PS-Q3.
Calculates problem-specific clinical ML metrics and common architecture metrics:
  - Accuracy, Recall (clinical priority for arrhythmias), Precision, F1-score
  - Confusion matrix [[TN, FP], [FN, TP]]
  - Log-loss / cross-entropy
  - Circuit depth, CX count, SWAP count, total shots, execution duration
  - Statistical variance across repeated seeds
"""

import math
from typing import Dict, List, Tuple, Any


def compute_classification_metrics(y_true: List[int], y_pred: List[int], y_probs: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Computes standard biomedical classification performance metrics.
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: y_true ({len(y_true)}) != y_pred ({len(y_pred)})")

    n = len(y_true)
    if n == 0:
        return {"accuracy": 0.0, "recall": 0.0, "precision": 0.0, "f1": 0.0, "tn": 0, "fp": 0, "fn": 0, "tp": 0}

    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    accuracy = (tp + tn) / n
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    # Cross-entropy loss if probabilities provided
    loss = 0.0
    if y_probs:
        eps = 1e-12
        for yt, p in zip(y_true, y_probs):
            p_clamped = max(eps, min(1.0 - eps, p))
            loss -= yt * math.log(p_clamped) + (1 - yt) * math.log(1.0 - p_clamped)
        loss /= n

    # Standard error of proportion for accuracy: sigma_p = sqrt(p(1-p)/N)
    std_err = math.sqrt(accuracy * (1.0 - accuracy) / n) if n > 0 else 0.0

    return {
        "sample_count": n,
        "accuracy": round(accuracy, 4),
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "f1_score": round(f1, 4),
        "loss": round(loss, 4),
        "std_error": round(std_err, 4),
        "confusion_matrix": {
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp,
        },
    }


def compute_architecture_metrics(
    transpiled_ops: Dict[str, int],
    depth: int,
    num_qubits: int,
    shots: int,
    circuits_executed: int,
    latency_ms: float
) -> Dict[str, Any]:
    """
    Computes common architecture / hardware resource metrics.
    """
    algorithmic_cx = transpiled_ops.get("cx", 0)
    swap_count = transpiled_ops.get("swap", 0)
    total_physical_cx = algorithmic_cx + 3 * swap_count

    return {
        "depth": depth,
        "physical_qubits": num_qubits,
        "algorithmic_cx": algorithmic_cx,
        "swap_count": swap_count,
        "total_physical_cx": total_physical_cx,
        "circuits_executed": circuits_executed,
        "total_shots_sampled": shots * circuits_executed,
        "latency_ms": round(latency_ms, 2),
        "routing_overhead_multiplier": round(total_physical_cx / max(1, algorithmic_cx), 2),
    }
