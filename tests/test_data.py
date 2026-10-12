import math
import pytest
from src.data_loader import generate_ecg_dataset, normalize_features, get_train_test_split


def test_dataset_generation():
    samples = generate_ecg_dataset(100, seed=42)
    assert len(samples) == 100
    # Check that both classes exist
    labels = [s["label"] for s in samples]
    assert 0 in labels
    assert 1 in labels
    assert sum(labels) > 20  # Significant representation of arrhythmia


def test_feature_normalization():
    raw_vectors = [
        [800.0, 90.0, 1.2, 0.0],
        [400.0, 140.0, 0.6, -0.2],
        [1200.0, 70.0, 1.8, 0.3],
    ]
    norm, ranges = normalize_features(raw_vectors, bounds=(0.0, math.pi))
    assert len(norm) == 3
    for vec in norm:
        for val in vec:
            assert 0.0 <= val <= math.pi + 1e-4


def test_stratified_train_test_split():
    samples = generate_ecg_dataset(150, seed=42)
    split = get_train_test_split(samples, train_ratio=0.8, seed=42)
    assert len(split["X_train"]) + len(split["X_test"]) == 150
    assert 118 <= len(split["X_train"]) <= 122
    assert len(split["y_train"]) == len(split["X_train"])
    assert len(split["y_test"]) == len(split["X_test"])
    # No NaN or None
    for vec in split["X_train"]:
        for x in vec:
            assert isinstance(x, float)
            assert not math.isnan(x)
