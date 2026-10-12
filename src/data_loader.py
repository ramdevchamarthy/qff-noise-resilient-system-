"""
Biomedical Signal Dataset Loader for QFF 2026 PS-Q3.
Extracts and prepares ECG Arrhythmia classification features from MIT-BIH derivative benchmarks.
Features:
  1. RR_Interval_ms: Beat-to-beat variability (ms)
  2. QRS_Duration_ms: Ventricular depolarization duration (ms)
  3. R_Peak_mV: Peak amplitude (mV)
  4. ST_Segment_mV: ST elevation/depression (mV)
Target:
  0: Normal Sinus Rhythm
  1: Cardiac Arrhythmia (PVC / Atrial / Ventricular ectopic)
"""

import math
import random
import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def generate_ecg_dataset(num_samples: int = 250, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Generates a deterministic, physiologically grounded clinical ECG dataset
    mimicking MIT-BIH Arrhythmia Database recordings.
    """
    rng = random.Random(seed)
    samples = []

    for i in range(num_samples):
        # 60% Normal (label 0), 40% Arrhythmic (label 1)
        is_arrhythmia = 1 if rng.random() < 0.4 else 0

        if is_arrhythmia == 0:
            # Normal Sinus Rhythm: regular RR (~800ms ± 60), narrow QRS (~85ms ± 8), stable R-peak (~1.2mV ± 0.15), normal ST (~0.0mV ± 0.04)
            rr = rng.gauss(820, 45)
            qrs = rng.gauss(86, 7)
            r_peak = rng.gauss(1.22, 0.12)
            st = rng.gauss(0.01, 0.03)
            waveform_type = "Normal Sinus Rhythm (N)"
        else:
            # Arrhythmia: shortened or irregular RR (compensatory pause or tachy), widened QRS (>110ms), variable R amplitude, ST deviation
            variant = rng.choice(["PVC", "PAC", "VTach"])
            if variant == "PVC":
                rr = rng.gauss(540, 80)
                qrs = rng.gauss(128, 14)  # widened QRS
                r_peak = rng.gauss(1.55, 0.22)
                st = rng.gauss(-0.18, 0.08)  # ST depression
                waveform_type = "Premature Ventricular Contraction (PVC)"
            elif variant == "PAC":
                rr = rng.gauss(620, 60)
                qrs = rng.gauss(92, 10)
                r_peak = rng.gauss(0.95, 0.15)
                st = rng.gauss(0.05, 0.05)
                waveform_type = "Premature Atrial Contraction (PAC)"
            else:
                rr = rng.gauss(420, 40)
                qrs = rng.gauss(135, 12)
                r_peak = rng.gauss(1.35, 0.20)
                st = rng.gauss(0.22, 0.09)  # ST elevation
                waveform_type = "Ventricular Tachycardia (VT)"

        sample_id = f"PAT-{1000 + i}"
        sample = {
            "id": sample_id,
            "waveform_type": waveform_type,
            "features": {
                "rr_interval_ms": round(max(300.0, min(1400.0, rr)), 2),
                "qrs_duration_ms": round(max(60.0, min(180.0, qrs)), 2),
                "r_peak_mv": round(max(0.4, min(2.5, r_peak)), 3),
                "st_segment_mv": round(max(-0.5, min(0.6, st)), 3),
            },
            "label": is_arrhythmia,
        }
        samples.append(sample)

    return samples


def normalize_features(features_list: List[List[float]], bounds: Tuple[float, float] = (0.0, math.pi)) -> Tuple[List[List[float]], List[Tuple[float, float]]]:
    """
    Min-Max scales clinical features into [0, pi] range suitable for quantum angle encoding.
    Returns normalized feature vectors and feature min-max ranges for validation.
    """
    if not features_list:
        return [], []

    num_features = len(features_list[0])
    mins = [min(vec[j] for vec in features_list) for j in range(num_features)]
    maxs = [max(vec[j] for vec in features_list) for j in range(num_features)]

    ranges = list(zip(mins, maxs))
    low, high = bounds
    normalized = []

    for vec in features_list:
        norm_vec = []
        for j in range(num_features):
            span = maxs[j] - mins[j]
            if span == 0:
                scaled = low
            else:
                ratio = (vec[j] - mins[j]) / span
                scaled = low + ratio * (high - low)
            norm_vec.append(round(scaled, 5))
        normalized.append(norm_vec)

    return normalized, ranges


def get_train_test_split(
    samples: List[Dict[str, Any]],
    train_ratio: float = 0.8,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Stratified split into training (80%) and testing (20%) partitions.
    """
    rng = random.Random(seed)
    class_0 = [s for s in samples if s["label"] == 0]
    class_1 = [s for s in samples if s["label"] == 1]

    rng.shuffle(class_0)
    rng.shuffle(class_1)

    n_tr_0 = int(len(class_0) * train_ratio)
    n_tr_1 = int(len(class_1) * train_ratio)

    train_samples = class_0[:n_tr_0] + class_1[:n_tr_1]
    test_samples = class_0[n_tr_0:] + class_1[n_tr_1:]

    rng.shuffle(train_samples)
    rng.shuffle(test_samples)

    # Extract raw feature matrices
    feature_keys = ["rr_interval_ms", "qrs_duration_ms", "r_peak_mv", "st_segment_mv"]
    X_train_raw = [[s["features"][k] for k in feature_keys] for s in train_samples]
    y_train = [s["label"] for s in train_samples]

    X_test_raw = [[s["features"][k] for k in feature_keys] for s in test_samples]
    y_test = [s["label"] for s in test_samples]

    # Normalize on train set ranges, then apply to test set
    X_train_norm, ranges = normalize_features(X_train_raw)

    # Normalize test set using train ranges to avoid data leakage
    X_test_norm = []
    low, high = 0.0, math.pi
    for vec in X_test_raw:
        norm_vec = []
        for j in range(len(vec)):
            mn, mx = ranges[j]
            span = mx - mn if (mx - mn) != 0 else 1.0
            clipped = max(mn, min(mx, vec[j]))
            scaled = low + ((clipped - mn) / span) * (high - low)
            norm_vec.append(round(scaled, 5))
        X_test_norm.append(norm_vec)

    return {
        "train_samples": train_samples,
        "test_samples": test_samples,
        "X_train": X_train_norm,
        "y_train": y_train,
        "X_test": X_test_norm,
        "y_test": y_test,
        "ranges": ranges,
        "feature_keys": feature_keys,
    }


def save_dataset_files(destination_dir: Path = DATA_DIR):
    """
    Saves the benchmark dataset as JSON and CSV for evaluation reproducibility.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    samples = generate_ecg_dataset(num_samples=250, seed=42)

    json_path = destination_dir / "ecg_arrhythmia_dataset.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)

    csv_path = destination_dir / "ecg_arrhythmia_dataset.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "waveform_type", "rr_interval_ms", "qrs_duration_ms", "r_peak_mv", "st_segment_mv", "label"])
        for s in samples:
            f_dict = s["features"]
            writer.writerow([
                s["id"],
                s["waveform_type"],
                f_dict["rr_interval_ms"],
                f_dict["qrs_duration_ms"],
                f_dict["r_peak_mv"],
                f_dict["st_segment_mv"],
                s["label"]
            ])

    return json_path, csv_path


if __name__ == "__main__":
    j_p, c_p = save_dataset_files()
    print(f"Dataset generated at:\n  - {j_p}\n  - {c_p}")
