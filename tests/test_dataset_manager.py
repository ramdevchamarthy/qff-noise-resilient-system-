"""
Tests for Dataset Manager, Training Pipeline, and Experiment Store.
Verifies data inspection, leakage-free preprocessing, validation, persistence, and exports.
"""

import pytest
from src.dataset_manager import (
    parse_and_inspect_csv,
    validate_and_preprocess_dataset,
    compute_sha256,
)
from src.experiment_store import (
    save_run,
    get_run,
    export_run_csv,
    save_model,
    get_model,
)
from backend.app.api.routes import (
    upload_dataset,
    validate_dataset,
    train_model,
    evaluate_batch_experiment,
    export_experiment_csv_endpoint,
)
from backend.app.models.schemas import (
    DatasetUploadRequest,
    DatasetValidateRequest,
    TrainModelRequest,
    BatchEvaluateRequest,
)

SAMPLE_CSV = """rr_interval,qrs_duration,r_peak,st_segment,diagnosis
800.5,85.2,1.2,0.01,0
820.1,88.4,1.1,0.02,0
810.0,86.0,1.3,0.00,0
830.5,84.1,1.25,-0.01,0
815.2,87.0,1.18,0.01,0
825.0,85.5,1.22,0.02,0
520.4,130.2,1.6,-0.20,1
540.1,128.5,1.55,-0.18,1
510.8,135.0,1.7,-0.22,1
530.2,132.1,1.65,-0.19,1
550.0,126.4,1.5,-0.15,1
515.6,134.8,1.68,-0.21,1
"""


def test_parse_and_inspect_csv():
    info = parse_and_inspect_csv(SAMPLE_CSV, "test.csv")
    assert info["row_count"] == 12
    assert info["column_count"] == 5
    assert "rr_interval" in info["headers"]
    assert "diagnosis" in info["headers"]
    assert len(info["preview_rows"]) == 5
    assert info["total_missing_cells"] == 0
    assert info["duplicate_rows"] == 0
    assert len(info["fingerprint"]) > 0


def test_validate_and_preprocess_dataset_binary_target():
    features = ["rr_interval", "qrs_duration", "r_peak", "st_segment"]
    prep = validate_and_preprocess_dataset(
        SAMPLE_CSV,
        feature_columns=features,
        target_column="diagnosis",
        train_ratio=0.75,
        seed=42,
    )
    assert prep["status"] == "valid"
    assert len(prep["target_classes"]) == 2
    assert prep["train_samples_count"] > 0
    assert prep["test_samples_count"] > 0
    assert len(prep["X_train"][0]) == 4
    assert len(prep["X_test"][0]) == 4
    # All normalized features must be within [0, pi]
    for row in prep["X_train"]:
        for val in row:
            assert 0.0 <= val <= 3.1416


def test_target_leakage_prevention():
    features = ["rr_interval", "qrs_duration", "r_peak", "diagnosis"]
    with pytest.raises(ValueError, match="target leakage"):
        validate_and_preprocess_dataset(
            SAMPLE_CSV,
            feature_columns=features,
            target_column="diagnosis",
        )


def test_feature_count_constraint():
    features = ["rr_interval", "qrs_duration", "r_peak"]  # only 3 features
    with pytest.raises(ValueError, match="requires exactly 4 features"):
        validate_and_preprocess_dataset(
            SAMPLE_CSV,
            feature_columns=features,
            target_column="diagnosis",
        )


def test_experiment_store_save_and_export():
    test_run = {
        "run_id": "test_run_12345",
        "processor_name": "Processor A",
        "mitigation_method": "Dual-Layer (ZNE + Readout)",
        "noise_rate_2q": 0.005,
        "readout_error_rate": 0.015,
        "circuits_executed": 3,
        "total_shots": 3072,
        "circuit_depth": 9,
        "swap_count": 2,
        "total_physical_cx": 16,
        "latency_ms": 12.5,
        "ml_metrics": {
            "accuracy": 0.90,
            "recall": 0.737,
            "precision": 0.875,
            "f1_score": 0.80,
            "specificity": 0.95,
        },
        "detailed_samples": [
            {"id": "SAMP-01", "ground_truth": 0, "predicted": 0, "probability": 0.12},
            {"id": "SAMP-02", "ground_truth": 1, "predicted": 1, "probability": 0.88},
        ]
    }
    saved_id = save_run(test_run)
    assert saved_id == "test_run_12345"

    retrieved = get_run(saved_id)
    assert retrieved is not None
    assert retrieved["processor_name"] == "Processor A"

    csv_text = export_run_csv(saved_id)
    assert "Q-ResQ" in csv_text
    assert "test_run_12345" in csv_text
    assert "Dual-Layer" in csv_text
    assert "Accuracy" in csv_text
    assert "SAMP-01" in csv_text


def test_api_dataset_upload_validate_and_train():
    # 1. Upload CSV
    up_req = DatasetUploadRequest(raw_csv=SAMPLE_CSV, filename="sample_ecg.csv")
    up_data = upload_dataset(up_req)
    dataset_id = up_data.dataset_id
    assert dataset_id.startswith("ds_")

    # 2. Validate Dataset
    val_req = DatasetValidateRequest(
        feature_columns=["rr_interval", "qrs_duration", "r_peak", "st_segment"],
        target_column="diagnosis",
        imputation_strategy="mean",
        seed=42,
    )
    val_data = validate_dataset(dataset_id, val_req)
    assert val_data.status == "valid"
    assert val_data.train_samples_count > 0

    # 3. Train Model
    train_req = TrainModelRequest(
        dataset_id=dataset_id,
        feature_columns=["rr_interval", "qrs_duration", "r_peak", "st_segment"],
        target_column="diagnosis",
        epochs=5,
        batch_size=8,
        lr=0.20,
        seed=42,
        model_name="Test Trained Model",
    )
    train_data = train_model(train_req)
    assert train_data.model_id is not None
    assert len(train_data.weights) == 16
    assert len(train_data.loss_history) == 5

    # 4. Batch Evaluate
    batch_req = BatchEvaluateRequest(
        dataset_id=dataset_id,
        model_id=train_data.model_id,
        feature_columns=["rr_interval", "qrs_duration", "r_peak", "st_segment"],
        target_column="diagnosis",
        processor="A",
        mitigation_method="dual",
        shots=256,
        seed=42,
    )
    batch_data = evaluate_batch_experiment(batch_req)
    assert batch_data.run_id is not None
    assert "accuracy" in batch_data.ml_metrics

    # 5. Export Run CSV
    run_id = batch_data.run_id
    export_resp = export_experiment_csv_endpoint(run_id)
    assert "text/csv" in export_resp.media_type
    assert run_id in export_resp.body.decode("utf-8")
