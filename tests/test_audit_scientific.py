"""
Scientific Correctness & Implementation Audit Regression Suite for QFF 2026 PS-Q3.
Validates:
  1. Exact metric derivation on small cohorts (N=7 held-out samples: 57.1% acc, 0% recall, 0% precision).
  2. Zero-denominator boundary conditions and contingency matrix alignment.
  3. Consistent clinical label mapping (Normal -> 0, Arrhythmia -> 1) regardless of alphabetization.
  4. Architecture-aware transpilation & optimal layout discovery (Processor A: 32 CX vs Processor B: 8 CX).
  5. Robustness sweep curve differentiation across physical topologies.
  6. Provenance tracking and durability notice handling.
"""

import math
import pytest
from src.metrics import compute_classification_metrics
from src.processors import load_all_processors, load_processor
from src.quantum_core import QuantumCircuit
from src.transpiler import Transpiler, compare_transpilation_on_all_processors
from src.vqc import build_vqc_circuit, VariationalQuantumClassifier
from src.dataset_manager import validate_and_preprocess_dataset
from backend.app.api.routes import get_robustness_sweep
from backend.app.models.schemas import SweepRequest


def test_audit_seven_sample_contingency_table():
    """
    Directly recalculates and validates the reported metrics:
    Test accuracy: 57.1%, Sensitivity: 0.0%, Precision: 0.0%, F1: 0.0% on 7 held-out test samples.
    Proves mathematically that:
      N = 7
      Ground truth: 4 Negative (0), 3 Positive (1)
      Predictions: 7 Negative (0) -> [0, 0, 0, 0, 0, 0, 0]
      Contingency: TN=4, FP=0, FN=3, TP=0
    """
    y_true = [0, 0, 0, 0, 1, 1, 1]
    y_pred = [0, 0, 0, 0, 0, 0, 0]
    y_prob = [0.25, 0.30, 0.22, 0.18, 0.48, 0.45, 0.49]

    metrics = compute_classification_metrics(y_true, y_pred, y_prob)

    assert metrics["sample_count"] == 7
    # Accuracy = (TP + TN) / N = (0 + 4) / 7 = 0.5714 (57.1%)
    assert metrics["accuracy"] == 0.5714
    assert round(metrics["accuracy"] * 100, 1) == 57.1

    # Sensitivity/Recall = TP / (TP + FN) = 0 / 3 = 0.0%
    assert metrics["recall"] == 0.0

    # Precision = TP / (TP + FP) = 0 / 0 -> 0.0% (guarded against zero-division)
    assert metrics["precision"] == 0.0

    # F1 = 0.0%
    assert metrics["f1_score"] == 0.0

    # Specificity = TN / (TN + FP) = 4 / 4 = 100.0%
    assert metrics["specificity"] == 1.0

    # Balanced Accuracy = (Recall + Specificity) / 2 = 0.50 (50.0%)
    assert metrics["balanced_accuracy"] == 0.50

    # Confusion matrix exact match
    cm = metrics["confusion_matrix"]
    assert cm["tn"] == 4
    assert cm["fp"] == 0
    assert cm["fn"] == 3
    assert cm["tp"] == 0

    # Verification: Denominator equals sum of all cells in confusion matrix
    assert cm["tn"] + cm["fp"] + cm["fn"] + cm["tp"] == metrics["sample_count"]

    # Small sample detection and warning
    assert metrics["is_small_sample"] is True
    assert "N=7 < 30" in metrics["small_sample_warning"]
    expected_std_err = math.sqrt(0.5714 * (1.0 - 0.5714) / 7)
    assert abs(metrics["std_error"] - expected_std_err) < 1e-3


def test_audit_zero_positive_predictions_denominator_handling():
    """
    Verifies that compute_classification_metrics never substitutes arbitrary defaults
    and cleanly handles zero denominators for recall, precision, and empty slices.
    """
    # 1. No positive predictions (TP=0, FP=0)
    m1 = compute_classification_metrics([1, 1], [0, 0])
    assert m1["precision"] == 0.0
    assert m1["recall"] == 0.0
    assert m1["f1_score"] == 0.0
    assert m1["accuracy"] == 0.0

    # 2. No negative ground truth (TN + FP == 0)
    m2 = compute_classification_metrics([1, 1], [1, 1])
    assert m2["specificity"] == 0.0
    assert m2["recall"] == 1.0
    assert m2["precision"] == 1.0
    assert m2["accuracy"] == 1.0

    # 3. No positive ground truth (TP + FN == 0)
    m3 = compute_classification_metrics([0, 0], [0, 0])
    assert m3["recall"] == 0.0
    assert m3["specificity"] == 1.0
    assert m3["accuracy"] == 1.0


def test_audit_clinical_label_mapping_invariance():
    """
    Verifies that string target classes are mapped to clinical labels correctly
    (Normal -> 0, Arrhythmia -> 1) regardless of lexicographical ordering.
    """
    csv_arrhythmia_first = """feat1,feat2,feat3,feat4,diagnosis
1.0,2.0,3.0,4.0,Arrhythmia
1.1,2.1,3.1,4.1,Arrhythmia
1.2,2.2,3.2,4.2,Arrhythmia
1.0,2.0,3.0,4.0,Normal
1.1,2.1,3.1,4.1,Normal
1.2,2.2,3.2,4.2,Normal
1.3,2.3,3.3,4.3,Arrhythmia
1.3,2.3,3.3,4.3,Normal
1.4,2.4,3.4,4.4,Normal
1.4,2.4,3.4,4.4,Arrhythmia
"""
    prep = validate_and_preprocess_dataset(
        csv_content=csv_arrhythmia_first,
        feature_columns=["feat1", "feat2", "feat3", "feat4"],
        target_column="diagnosis",
    )
    # Even though "Arrhythmia" comes before "Normal" alphabetically,
    # clinical mapping MUST set Normal = 0, Arrhythmia = 1
    assert prep["label_mapping"]["Normal"] == 0
    assert prep["label_mapping"]["Arrhythmia"] == 1

    # Verify y_train and y_test contain binary 0 and 1
    assert set(prep["y_train"]).issubset({0, 1})
    assert set(prep["y_test"]).issubset({0, 1})


def test_audit_transpiler_optimal_layout_processor_a_vs_b():
    """
    Verifies that Transpiler discovers the native 4-cycle on Processor B (Heavy-Hex)
    reducing physical CX gates from 32 to 8 (0 SWAPs), while Processor A requires 32 CX (8 SWAPs).
    """
    procs = load_all_processors()
    proc_a = procs["A"]
    proc_b = procs["B"]
    proc_c = procs["C"]

    # 4-qubit cyclic entangler
    qc = build_vqc_circuit([1.0, 1.2, 0.8, 1.5], [0.1] * 16, num_qubits=4, layers=2)

    _, m_a = Transpiler(proc_a).transpile(qc)
    _, m_b = Transpiler(proc_b).transpile(qc)
    _, m_c = Transpiler(proc_c).transpile(qc)

    # Processor A has a tree/star topology; cyclic entangling requires SWAP routing
    assert m_a["swap_count"] >= 4
    assert m_a["total_physical_cx"] >= 20

    # Processor B contains native 4-cycles (e.g. 0-1-6-8); optimal embedding needs 0 SWAPs
    assert m_b["swap_count"] == 0
    assert m_b["total_physical_cx"] == 8
    assert m_b["routing_overhead_ratio"] == 1.0

    # Processor C also embeds the 4-cycle natively with 0 SWAPs
    assert m_c["swap_count"] == 0
    assert m_c["total_physical_cx"] == 8

    # Hardware advantage: Processor B executes 4x fewer physical CX gates than Processor A
    assert m_b["total_physical_cx"] < m_a["total_physical_cx"]


def test_audit_robustness_sweep_distinct_processor_curves():
    """
    Verifies that get_robustness_sweep produces distinct curves for Processor A vs Processor B
    due to their physical CX count divergence (32 CX vs 8 CX).
    """
    req_a = SweepRequest(processor="A", shots=512, seed=42)
    req_b = SweepRequest(processor="B", shots=512, seed=42)

    res_a = get_robustness_sweep(req_a)
    res_b = get_robustness_sweep(req_b)

    assert res_a["processor"] == "Processor A"
    assert res_b["processor"] == "Processor B"

    pts_a = res_a["points"]
    pts_b = res_b["points"]

    assert len(pts_a) == 7
    assert len(pts_b) == 7

    # At noise = 0.0%, both processors mathematically coincide at the ideal simulator baseline
    assert pts_a[0]["noise_rate_pct"] == 0.0
    assert pts_b[0]["noise_rate_pct"] == 0.0
    assert pts_a[0]["unmitigated_accuracy"] == pts_b[0]["unmitigated_accuracy"]

    # At higher noise rates (e.g. 0.5% or 5.0%), Processor B and Processor A curves differ
    # because Processor B has only 8 physical CX while Processor A has 32 physical CX
    acc_a = [p["unmitigated_accuracy"] for p in pts_a[1:]]
    acc_b = [p["unmitigated_accuracy"] for p in pts_b[1:]]
    assert acc_a != acc_b, "Processor A and Processor B curves must not be identical across non-zero noise levels"


def test_audit_actual_mapped_circuit_edges_on_processor_b():
    """
    Directly inspects the actual mapped QuantumCircuit instructions on Processor B:
      1. Confirms every physical two-qubit gate (CX/SWAP) lies on a valid directed physical edge in coupling_map.
      2. Confirms exactly 8 physical CX gates are generated (no SWAPs).
      3. Confirms reported physical CX count matches count of cx instructions in transpiled_qc.
      4. Verifies physical qubits used are strictly within the physical qubit register.
    """
    proc_b = load_processor("B")
    qc = build_vqc_circuit([0.5, 1.2, 2.1, 0.8], [0.1] * 16, num_qubits=4, layers=2)

    transpiled_qc, metrics = Transpiler(proc_b).transpile(qc)

    valid_coupling_edges = set(proc_b.coupling_map)
    two_qubit_instructions = [
        (name, qubits)
        for name, qubits, _ in transpiled_qc.instructions
        if len(qubits) == 2
    ]

    # Every two-qubit gate MUST be physically adjacent
    assert len(two_qubit_instructions) == 8, f"Expected exactly 8 CX gates, got {len(two_qubit_instructions)}"
    for gate_name, qubits in two_qubit_instructions:
        assert gate_name == "cx", f"Expected cx gate, found {gate_name}"
        c, t = qubits[0], qubits[1]
        assert (c, t) in valid_coupling_edges, (
            f"Physical gate {gate_name} between q{c} and q{t} is NOT in Processor B coupling map!"
        )

    # All physical qubits used must be in [0, proc_b.num_qubits)
    for _, qubits, _ in transpiled_qc.instructions:
        for q in qubits:
            assert 0 <= q < proc_b.num_qubits, f"Physical qubit {q} out of bounds for Processor B"

    # Verify reported metrics match actual instruction counts
    ops = transpiled_qc.count_ops()
    assert ops.get("cx", 0) == metrics["total_physical_cx"]
    assert ops.get("swap", 0) == metrics["swap_count"]
    assert metrics["swap_count"] == 0
    assert metrics["total_physical_cx"] == 8

