"""
Dataset Manager for Q-ResQ Quantum Machine Learning Pipeline.
Handles CSV upload, validation, leakage-free preprocessing, stratified splitting,
and feature normalization for the 4-qubit Variational Quantum Classifier (PS-Q3).
"""

import csv
import hashlib
import io
import json
import math
import random
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

DATA_UPLOADS_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"


def compute_sha256(text: str) -> str:
    """Computes a SHA-256 hexadecimal digest for dataset fingerprinting."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def parse_and_inspect_csv(csv_content: str, filename: str = "dataset.csv") -> Dict[str, Any]:
    """
    Parses CSV content and extracts comprehensive structural summary:
    - Row count, column count
    - Column headers & inferred types (numeric vs categorical)
    - Missing value count & empty string count
    - Duplicate row count
    - First 5 preview rows
    """
    # Detect delimiter
    sample = csv_content[:4096]
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    reader = csv.reader(io.StringIO(csv_content), delimiter=delimiter)
    rows = [r for r in reader if r]

    if not rows:
        raise ValueError("Uploaded CSV file is completely empty.")

    headers = [h.strip() for h in rows[0]]
    if len(headers) < 2:
        raise ValueError("CSV must contain at least 2 columns (features and label).")

    data_rows = rows[1:]
    row_count = len(data_rows)
    col_count = len(headers)

    if row_count < 10:
        raise ValueError(f"Dataset has only {row_count} rows. At least 10 rows are required for train/test splitting.")

    # Column inspection
    columns_info = []
    missing_total = 0

    for col_idx, col_name in enumerate(headers):
        values = [r[col_idx].strip() if col_idx < len(r) else "" for r in data_rows]
        empty_count = sum(1 for v in values if v == "" or v.lower() in ("nan", "null", "none", "na"))
        missing_total += empty_count

        non_empty = [v for v in values if v != "" and v.lower() not in ("nan", "null", "none", "na")]
        is_numeric = False
        if non_empty:
            num_success = 0
            for v in non_empty:
                try:
                    float(v)
                    num_success += 1
                except ValueError:
                    pass
            is_numeric = (num_success / len(non_empty)) >= 0.90

        unique_vals = set(non_empty)
        sample_vals = non_empty[:5]

        columns_info.append({
            "name": col_name,
            "index": col_idx,
            "inferred_type": "numeric" if is_numeric else "categorical",
            "missing_count": empty_count,
            "unique_count": len(unique_vals),
            "sample_values": sample_vals,
        })

    # Duplicate rows detection
    row_tuples = [tuple(r) for r in data_rows]
    unique_rows = set(row_tuples)
    duplicate_count = len(row_tuples) - len(unique_rows)

    # First 5 preview rows formatted as dicts
    preview_rows = []
    for r in data_rows[:5]:
        row_dict = {}
        for col_idx, col_name in enumerate(headers):
            row_dict[col_name] = r[col_idx] if col_idx < len(r) else ""
        preview_rows.append(row_dict)

    dataset_id = f"ds_{uuid.uuid4().hex[:10]}"
    fingerprint = compute_sha256(csv_content)

    return {
        "dataset_id": dataset_id,
        "filename": filename,
        "row_count": row_count,
        "column_count": col_count,
        "headers": headers,
        "columns": columns_info,
        "duplicate_rows": duplicate_count,
        "total_missing_cells": missing_total,
        "preview_rows": preview_rows,
        "fingerprint": fingerprint,
    }


from src.storage import save_dataset_files, load_dataset_files


def save_uploaded_csv(dataset_id: str, csv_content: str, metadata: Dict[str, Any]) -> Tuple[Path, Path]:
    """Saves raw CSV and inspection metadata across tiered persistent storage."""
    return save_dataset_files(dataset_id, csv_content, metadata)


def load_uploaded_csv(dataset_id: str) -> Tuple[str, Dict[str, Any]]:
    """Loads uploaded CSV and metadata by dataset ID from persistent storage."""
    return load_dataset_files(dataset_id)


def validate_and_preprocess_dataset(
    csv_content: str,
    feature_columns: List[str],
    target_column: str,
    imputation_strategy: str = "mean",  # "mean", "median", "drop"
    train_ratio: float = 0.8,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Validates feature & target selections and executes a strictly leakage-free pipeline:
    1. Validates binary target (exactly 2 unique classes).
    2. Validates features (exactly 4 numeric features for 4-qubit VQC).
    3. Handles missing values: fits imputation on training partition only!
    4. Stratified train/test split.
    5. Fits Min-Max scaling [0, pi] on train set, scales test set with train bounds.
    6. Returns clean X_train, y_train, X_test, y_test, ranges, and validation report.
    """
    if len(feature_columns) != 4:
        raise ValueError(
            f"Variational Quantum Classifier requires exactly 4 features for its 4-qubit SU(2) feature map. "
            f"Received {len(feature_columns)} features ({', '.join(feature_columns)})."
        )

    if target_column in feature_columns:
        raise ValueError(f"Target column '{target_column}' cannot be included in input features (target leakage).")

    reader = csv.reader(io.StringIO(csv_content))
    rows = [r for r in reader if r]
    if not rows:
        raise ValueError("Dataset is empty.")

    headers = [h.strip() for h in rows[0]]
    header_indices = {h: idx for idx, h in enumerate(headers)}

    for f_col in feature_columns:
        if f_col not in header_indices:
            raise ValueError(f"Feature column '{f_col}' was not found in dataset headers.")
    if target_column not in header_indices:
        raise ValueError(f"Target column '{target_column}' was not found in dataset headers.")

    target_idx = header_indices[target_column]
    feature_indices = [header_indices[f] for f in feature_columns]

    raw_data_rows = rows[1:]

    # Parse rows into raw values
    parsed_samples = []
    for row_idx, r in enumerate(raw_data_rows):
        if len(r) <= target_idx:
            continue
        raw_t = r[target_idx].strip()
        if raw_t == "" or raw_t.lower() in ("nan", "null", "none"):
            continue  # cannot use sample without target

        raw_feats = [r[idx].strip() if idx < len(r) else "" for idx in feature_indices]
        parsed_samples.append({
            "id": f"SAMP-{row_idx + 1:04d}",
            "raw_features": raw_feats,
            "raw_target": raw_t,
        })

    if len(parsed_samples) < 10:
        raise ValueError(f"Too few valid samples ({len(parsed_samples)}) after removing missing targets.")

    # Check target classes
    unique_targets = sorted(list(set(s["raw_target"] for s in parsed_samples)))
    if len(unique_targets) != 2:
        raise ValueError(
            f"Target column '{target_column}' must have exactly 2 classes for binary classification. "
            f"Found {len(unique_targets)} classes: {unique_targets}"
        )

    # Map classes to 0 and 1 using clinical diagnostic conventions
    # Negative/control class (0): normal, control, healthy, negative, 0
    # Positive/condition class (1): arrhythmia, abnormal, disease, positive, 1
    neg_keywords = {"0", "0.0", "normal", "healthy", "control", "neg", "negative", "false", "no", "n"}
    pos_keywords = {"1", "1.0", "arrhythmia", "abnormal", "disease", "pos", "positive", "true", "yes", "y", "a"}

    val0_str = str(unique_targets[0]).strip().lower()
    val1_str = str(unique_targets[1]).strip().lower()

    if val0_str in neg_keywords or val1_str in pos_keywords:
        target_map = {unique_targets[0]: 0, unique_targets[1]: 1}
    elif val1_str in neg_keywords or val0_str in pos_keywords:
        target_map = {unique_targets[0]: 1, unique_targets[1]: 0}
    else:
        target_map = {unique_targets[0]: 0, unique_targets[1]: 1}

    class_counts = {str(unique_targets[0]): 0, str(unique_targets[1]): 0}
    for s in parsed_samples:
        lbl = target_map[s["raw_target"]]
        s["label"] = lbl
        class_counts[str(s["raw_target"])] += 1

    # Check minimum class representation
    min_count = min(class_counts.values())
    if min_count < 3:
        raise ValueError(f"Minority class in target has only {min_count} samples. At least 3 are required for evaluation.")

    # Stratified Split (80/20) BEFORE imputation to avoid test leakage
    rng = random.Random(seed)
    class_0_samples = [s for s in parsed_samples if s["label"] == 0]
    class_1_samples = [s for s in parsed_samples if s["label"] == 1]

    rng.shuffle(class_0_samples)
    rng.shuffle(class_1_samples)

    n_tr_0 = max(1, int(len(class_0_samples) * train_ratio))
    n_tr_1 = max(1, int(len(class_1_samples) * train_ratio))

    train_part = class_0_samples[:n_tr_0] + class_1_samples[:n_tr_1]
    test_part = class_0_samples[n_tr_0:] + class_1_samples[n_tr_1:]

    rng.shuffle(train_part)
    rng.shuffle(test_part)

    # Imputation: Compute statistics on TRAIN partition ONLY
    # Collect train numerical values per feature
    train_feat_values: List[List[float]] = [[] for _ in range(4)]
    for s in train_part:
        for j, val_str in enumerate(s["raw_features"]):
            try:
                train_feat_values[j].append(float(val_str))
            except ValueError:
                pass

    for j in range(4):
        if not train_feat_values[j]:
            raise ValueError(f"Feature '{feature_columns[j]}' contains no valid numeric values in training partition.")

    # Imputation fill values computed on train partition
    impute_vals = []
    for j in range(4):
        vals = sorted(train_feat_values[j])
        if imputation_strategy == "median":
            mid = len(vals) // 2
            med = vals[mid] if len(vals) % 2 != 0 else (vals[mid - 1] + vals[mid]) / 2.0
            impute_vals.append(med)
        else:  # default mean
            mean_val = sum(vals) / len(vals)
            impute_vals.append(mean_val)

    # Apply imputation to train and test partitions
    def fill_and_convert(sample_list: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[int], List[str]]:
        X_mat = []
        y_vec = []
        ids = []
        for s in sample_list:
            row_vec = []
            for j, val_str in enumerate(s["raw_features"]):
                try:
                    num_val = float(val_str)
                except ValueError:
                    num_val = impute_vals[j]
                row_vec.append(num_val)
            X_mat.append(row_vec)
            y_vec.append(s["label"])
            ids.append(s["id"])
        return X_mat, y_vec, ids

    X_train_raw, y_train, train_ids = fill_and_convert(train_part)
    X_test_raw, y_test, test_ids = fill_and_convert(test_part)

    # Feature variance check on train set
    for j in range(4):
        col_vals = [row[j] for row in X_train_raw]
        mn = min(col_vals)
        mx = max(col_vals)
        if mn == mx:
            raise ValueError(
                f"Feature '{feature_columns[j]}' is constant (min = max = {mn}) with zero variance. "
                "Constant features cannot encode variational quantum state phase."
            )

    # Fit Min-Max Scaler [0, pi] on TRAIN set ONLY
    ranges: List[Tuple[float, float]] = []
    for j in range(4):
        col_vals = [row[j] for row in X_train_raw]
        ranges.append((min(col_vals), max(col_vals)))

    low, high = 0.0, math.pi

    def scale_matrix(matrix: List[List[float]]) -> List[List[float]]:
        scaled = []
        for row in matrix:
            scaled_row = []
            for j in range(4):
                mn, mx = ranges[j]
                span = mx - mn if (mx - mn) != 0 else 1.0
                clipped = max(mn, min(mx, row[j]))
                norm_val = low + ((clipped - mn) / span) * (high - low)
                scaled_row.append(round(norm_val, 5))
            scaled.append(scaled_row)
        return scaled

    X_train_norm = scale_matrix(X_train_raw)
    X_test_norm = scale_matrix(X_test_raw)

    fingerprint = compute_sha256(f"{feature_columns}_{target_column}_{len(parsed_samples)}")

    return {
        "status": "valid",
        "fingerprint": fingerprint,
        "feature_columns": feature_columns,
        "target_column": target_column,
        "target_classes": unique_targets,
        "label_mapping": {str(k): v for k, v in target_map.items()},
        "class_counts": class_counts,
        "train_samples_count": len(X_train_norm),
        "test_samples_count": len(X_test_norm),
        "imputation_strategy": imputation_strategy,
        "train_feature_ranges": [{"feature": feature_columns[j], "min": ranges[j][0], "max": ranges[j][1]} for j in range(4)],
        "X_train": X_train_norm,
        "y_train": y_train,
        "train_ids": train_ids,
        "X_test": X_test_norm,
        "y_test": y_test,
        "test_ids": test_ids,
    }
