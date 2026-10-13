"""
Regression tests for storage resilience, serverless read-only filesystem handling,
and multi-request dataset upload -> preview -> validate -> train -> evaluate workflow.
"""

import pytest
from unittest.mock import patch

from backend.app.api.routes import (
    upload_dataset,
    get_dataset_preview,
    validate_dataset,
    run_experiment,
    evaluate_batch_experiment,
)
from backend.app.models.schemas import (
    DatasetUploadRequest,
    DatasetValidateRequest,
    ExperimentRequest,
    BatchEvaluateRequest,
)
from src.storage import (
    get_writable_dir,
    save_dataset_files,
    load_dataset_files,
    save_experiment_run,
    load_experiment_run,
)

SAMPLE_CSV = """rr_interval_ms,qrs_duration_ms,r_peak_mv,st_segment_mv,arrhythmia_label
812.4,84.2,1.25,0.01,0
825.1,86.0,1.18,0.02,0
805.3,83.9,1.22,-0.01,0
830.0,85.5,1.20,0.01,0
815.8,87.1,1.15,0.02,0
820.5,84.8,1.24,0.00,0
810.0,85.0,1.21,0.01,0
818.0,86.2,1.19,-0.02,0
540.2,132.5,1.62,-0.18,1
525.0,128.0,1.55,-0.20,1
550.8,135.2,1.70,-0.15,1
515.3,130.4,1.58,-0.22,1
535.1,133.0,1.65,-0.19,1
545.9,129.5,1.60,-0.17,1
520.0,131.0,1.61,-0.21,1
"""


def test_multi_request_upload_preview_validate_pipeline():
    """Tests upload, preview, and validation across distinct sequential requests."""
    # Request 1: Upload CSV
    upload_req = DatasetUploadRequest(raw_csv=SAMPLE_CSV, filename="clinical_regression.csv")
    upload_res = upload_dataset(upload_req)
    dataset_id = upload_res.dataset_id
    assert dataset_id.startswith("ds_")
    assert upload_res.row_count == 15
    assert upload_res.column_count == 5
    assert len(upload_res.preview_rows) == 5

    # Request 2: Preview in a completely separate request
    preview_res = get_dataset_preview(dataset_id)
    assert preview_res.dataset_id == dataset_id
    assert preview_res.filename == "clinical_regression.csv"
    assert preview_res.headers == ["rr_interval_ms", "qrs_duration_ms", "r_peak_mv", "st_segment_mv", "arrhythmia_label"]

    # Request 3: Validate in another separate request
    val_req = DatasetValidateRequest(
        feature_columns=["rr_interval_ms", "qrs_duration_ms", "r_peak_mv", "st_segment_mv"],
        target_column="arrhythmia_label",
        imputation_strategy="mean",
        train_ratio=0.8,
        seed=42,
    )
    val_res = validate_dataset(dataset_id, val_req)
    assert val_res.status == "valid"
    assert val_res.train_samples_count == 11
    assert val_res.test_samples_count == 4
    assert val_res.target_classes == ["0", "1"]


def test_read_only_filesystem_fallback():
    """Simulates a read-only filesystem (as in /var/task on Vercel) and verifies fallback to /tmp."""
    with patch("src.storage._is_dir_writable", return_value=False):
        # Even when project directory is reported read-only, writable dir should resolve to /tmp
        w_dir = get_writable_dir("uploads")
        assert "qresq_data" in str(w_dir)

        # Dataset save and load must succeed without OSError [Errno 30]
        meta = {"test": True, "dataset_id": "ds_ro_test"}
        csv_path, meta_path = save_dataset_files("ds_ro_test", SAMPLE_CSV, meta)
        assert csv_path.exists()
        assert meta_path.exists()

        loaded_csv, loaded_meta = load_dataset_files("ds_ro_test")
        assert loaded_csv == SAMPLE_CSV
        assert loaded_meta["test"] is True


def test_experiment_run_and_batch_evaluation_persistence_tolerance():
    """Verifies single-sample and batch experiment execution succeed and return valid metrics."""
    # Single sample experiment run
    run_req = ExperimentRequest(
        processor="A",
        mitigation_method="dual",
        sample_id="PAT-1000",
        noise_enabled=True,
        noise_intensity_multiplier=1.0,
        shots=256,
    )
    run_res = run_experiment(run_req)
    assert run_res.run_id is not None
    assert run_res.predicted_label in (0, 1)
    assert 0.0 <= run_res.probability_arrhythmia <= 1.0
    assert run_res.circuits_executed == 3  # Dual ZNE folding

    # Batch evaluation
    batch_req = BatchEvaluateRequest(
        processor="A",
        mitigation_method="readout",
        noise_enabled=True,
        shots=256,
    )
    batch_res = evaluate_batch_experiment(batch_req)
    assert batch_res.run_id is not None
    assert batch_res.ml_metrics["accuracy"] >= 0.0
    assert batch_res.ml_metrics["sample_count"] == 50


def test_simulated_cold_start_across_empty_memory_cache():
    """Simulates serverless cold starts by emptying memory caches between requests."""
    from src.storage import _DATASET_CACHE, _RUN_CACHE, _MODEL_CACHE
    from backend.app.api.routes import train_model, get_experiment_run
    from backend.app.models.schemas import TrainModelRequest

    # Request 1: Upload dataset
    upload_req = DatasetUploadRequest(raw_csv=SAMPLE_CSV, filename="cold_start_test.csv")
    upload_res = upload_dataset(upload_req)
    ds_id = upload_res.dataset_id
    assert upload_res.is_persisted is False  # In local test without blob token
    assert upload_res.durability == "ephemeral_container"

    # COLD START 1: Evict all in-memory caches
    _DATASET_CACHE.clear()
    _RUN_CACHE.clear()
    _MODEL_CACHE.clear()

    # Request 2: Preview after cold start (must reload from disk)
    preview_res = get_dataset_preview(ds_id)
    assert preview_res.dataset_id == ds_id
    assert preview_res.filename == "cold_start_test.csv"

    # COLD START 2: Evict again
    _DATASET_CACHE.clear()

    # Request 3: Validate after cold start
    val_req = DatasetValidateRequest(
        feature_columns=["rr_interval_ms", "qrs_duration_ms", "r_peak_mv", "st_segment_mv"],
        target_column="arrhythmia_label",
        imputation_strategy="mean",
        seed=42,
    )
    val_res = validate_dataset(ds_id, val_req)
    assert val_res.status == "valid"

    # COLD START 3: Evict again
    _DATASET_CACHE.clear()

    # Request 4: Train model on dataset after cold start
    train_req = TrainModelRequest(
        dataset_id=ds_id,
        feature_columns=["rr_interval_ms", "qrs_duration_ms", "r_peak_mv", "st_segment_mv"],
        target_column="arrhythmia_label",
        epochs=5,
        batch_size=10,
        seed=42,
    )
    train_res = train_model(train_req)
    model_id = train_res.model_id
    assert model_id.startswith("vqc_")

    # COLD START 4: Evict again
    _MODEL_CACHE.clear()

    # Request 5: Run experiment and check run retrieval
    run_req = ExperimentRequest(
        processor="A",
        mitigation_method="none",
        shots=256,
    )
    run_res = run_experiment(run_req)
    run_id = run_res.run_id

    # COLD START 5: Evict again
    _RUN_CACHE.clear()

    # Retrieval after cold start
    retrieved_run = get_experiment_run(run_id)
    assert retrieved_run["run_id"] == run_id


def test_experiment_unpersisted_audit_failure_tolerance():
    """Confirms real quantum calculation is returned even if audit log persistence crashes."""
    with patch("backend.app.api.routes.save_run", side_effect=OSError("Read-only filesystem error")):
        run_req = ExperimentRequest(
            processor="A",
            mitigation_method="zne",
            shots=256,
        )
        res = run_experiment(run_req)
        # Result must not fail with 500 error; returns real quantum results
        assert res.run_id.startswith("ephem_")
        assert res.is_persisted is False
        assert res.durability == "unpersisted"
        assert "Audit log persistence failed" in res.storage_warning
        assert 0.0 <= res.probability_arrhythmia <= 1.0
        assert res.predicted_label in (0, 1)

        # Batch evaluation persistence failure
        batch_req = BatchEvaluateRequest(
            processor="A",
            mitigation_method="none",
            shots=256,
        )
        batch_res = evaluate_batch_experiment(batch_req)
        assert batch_res.run_id.startswith("ephem_")
        assert batch_res.is_persisted is False
        assert batch_res.durability == "unpersisted"
        assert "Audit log persistence failed" in batch_res.storage_warning
        assert batch_res.ml_metrics["accuracy"] >= 0.0


def test_csv_upload_size_limit_rejection():
    """Confirms files exceeding 10MB limit are cleanly rejected with HTTP 400."""
    from fastapi import HTTPException
    large_csv = "a,b,c,d,target\n" + ("1.0,2.0,3.0,4.0,0\n" * 700000)  # ~12.6 MB
    upload_req = DatasetUploadRequest(raw_csv=large_csv, filename="oversized.csv")
    with pytest.raises(HTTPException) as exc_info:
        upload_dataset(upload_req)
    assert exc_info.value.status_code == 400
    assert "10MB size limit" in exc_info.value.detail


def test_all_mitigation_methods_produce_valid_results():
    """Verifies that none, readout, zne, and dual mitigation methods all execute and return metrics."""
    for method in ["none", "readout", "zne", "dual"]:
        run_req = ExperimentRequest(
            processor="A",
            mitigation_method=method,
            sample_id="PAT-1000",
            shots=256,
            seed=42,
        )
        res = run_experiment(run_req)
        assert res.predicted_label in (0, 1)
        assert 0.0 <= res.probability_arrhythmia <= 1.0
        assert res.circuits_executed >= 1


def test_custom_dataset_train_and_batch_evaluate_pipeline():
    """Tests end-to-end training with custom uploaded dataset and batch evaluation."""
    from backend.app.api.routes import train_model
    from backend.app.models.schemas import TrainModelRequest

    # Upload
    upload_req = DatasetUploadRequest(raw_csv=SAMPLE_CSV, filename="custom_full_pipeline.csv")
    upload_res = upload_dataset(upload_req)
    ds_id = upload_res.dataset_id

    # Train Custom Model
    train_req = TrainModelRequest(
        dataset_id=ds_id,
        feature_columns=["rr_interval_ms", "qrs_duration_ms", "r_peak_mv", "st_segment_mv"],
        target_column="arrhythmia_label",
        epochs=5,
        batch_size=10,
        model_name="Custom Pipeline VQC",
        seed=42,
    )
    train_res = train_model(train_req)
    model_id = train_res.model_id
    assert train_res.train_accuracy >= 0.0

    # Batch Evaluate with Custom Dataset and Model
    batch_req = BatchEvaluateRequest(
        dataset_id=ds_id,
        model_id=model_id,
        feature_columns=["rr_interval_ms", "qrs_duration_ms", "r_peak_mv", "st_segment_mv"],
        target_column="arrhythmia_label",
        processor="A",
        mitigation_method="dual",
        shots=256,
        seed=42,
    )
    batch_res = evaluate_batch_experiment(batch_req)
    assert batch_res.dataset_source == "custom_uploaded_dataset"
    assert batch_res.ml_metrics["sample_count"] > 0
    assert 0.0 <= batch_res.ml_metrics["accuracy"] <= 1.0
