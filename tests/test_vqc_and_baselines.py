import pytest
from src.data_loader import generate_ecg_dataset, get_train_test_split
from src.vqc import ClassicalLogisticRegression, VariationalQuantumClassifier


def test_classical_baseline_training():
    samples = generate_ecg_dataset(100, seed=42)
    split = get_train_test_split(samples, train_ratio=0.8, seed=42)
    clf = ClassicalLogisticRegression(4)
    clf.fit(split["X_train"], split["y_train"], epochs=100, lr=0.1, seed=42)

    preds = clf.predict(split["X_test"])
    assert len(preds) == len(split["y_test"])
    correct = sum(1 for yt, yp in zip(split["y_test"], preds) if yt == yp)
    acc = correct / len(preds)
    assert acc >= 0.70  # Baseline should achieve solid classification accuracy


def test_vqc_inference_and_evaluation():
    samples = generate_ecg_dataset(50, seed=42)
    split = get_train_test_split(samples, train_ratio=0.8, seed=42)
    vqc = VariationalQuantumClassifier(num_qubits=4, layers=2)
    vqc.load_weights()

    res = vqc.evaluate_batch(split["X_test"][:10], split["y_test"][:10], mitigation_method="ideal")
    assert "ml_metrics" in res
    assert "accuracy" in res["ml_metrics"]
    assert "recall" in res["ml_metrics"]
    assert 0.0 <= res["ml_metrics"]["accuracy"] <= 1.0
