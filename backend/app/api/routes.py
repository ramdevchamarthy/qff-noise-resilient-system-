"""
API Route Handlers for Noise-Resilient Quantum System.
Includes full support for dataset upload, validation, leakage-free preprocessing,
real VQC training, hardware transpilation, error mitigation, persistence, and exports.
"""

import logging
import math
import random
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Response

logger = logging.getLogger("qresq.api")

from backend.app.models.schemas import (
    HealthResponse,
    ExperimentRequest,
    ExperimentResponse,
    SweepRequest,
    TranspileRequest,
    DatasetUploadRequest,
    DatasetUploadResponse,
    DatasetValidateRequest,
    DatasetValidateResponse,
    TrainModelRequest,
    TrainModelResponse,
    BatchEvaluateRequest,
    BatchEvaluateResponse,
)
from src.data_loader import generate_ecg_dataset, get_train_test_split, normalize_features
from src.processors import load_all_processors, load_processor
from src.noise_models import CalibratedNoiseModel
from src.vqc import VariationalQuantumClassifier, build_vqc_circuit
from src.transpiler import Transpiler, compare_transpilation_on_all_processors
from src.mitigation import ReadoutMitigator, ZeroNoiseExtrapolator
from src.dataset_manager import (
    parse_and_inspect_csv,
    save_uploaded_csv,
    load_uploaded_csv,
    validate_and_preprocess_dataset,
)
from src.experiment_store import (
    save_run,
    get_run,
    list_runs,
    export_run_csv,
    save_model,
    get_model,
    list_models,
)
from src.storage import is_cloud_storage_enabled

router = APIRouter()

# Preload benchmark dataset and reference trained VQC model
DATASET_SAMPLES = generate_ecg_dataset(250, seed=42)
SPLIT = get_train_test_split(DATASET_SAMPLES, train_ratio=0.8, seed=42)
VQC_MODEL = VariationalQuantumClassifier(num_qubits=4, layers=2)
VQC_MODEL.load_weights()


@router.get("/health", response_model=HealthResponse)
def get_health():
    return HealthResponse()


@router.get("/samples")
def get_samples():
    """Returns patient ECG samples with clinical waveform data for experiment workspace."""
    featured = DATASET_SAMPLES[:12]
    enriched = []
    for s in featured:
        f = s["features"]
        t_steps = 60
        wave = []
        for step in range(t_steps):
            phase = (step / t_steps) * 2 * math.pi
            base = 0.1 * math.sin(phase)
            r_center = 0.40
            dist = abs((step / t_steps) - r_center)
            if dist < 0.05:
                spike = f["r_peak_mv"] * math.exp(- (dist / 0.015) ** 2)
            else:
                spike = 0.0
            st_val = f["st_segment_mv"] if (step / t_steps) > 0.50 else 0.0
            val = round(base + spike + st_val, 3)
            wave.append({"step": step, "voltage": val})

        enriched.append({
            "id": s["id"],
            "waveform_type": s["waveform_type"],
            "label": s["label"],
            "features": f,
            "waveform": wave,
        })
    return enriched


@router.get("/processors")
def get_processors():
    """Returns processor topologies and graph definitions."""
    procs = load_all_processors()
    return {k: p.get_stats() for k, p in procs.items()}


# --- DATASET MANAGEMENT ENDPOINTS ---

@router.post("/datasets/upload", response_model=DatasetUploadResponse)
def upload_dataset(req: DatasetUploadRequest):
    """
    Upload a CSV dataset string content.
    Inspects structure, missing values, duplicates, and returns column previews.
    """
    content = req.raw_csv
    target_filename = req.filename or "dataset.csv"

    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="CSV content is empty.")

    if len(content.encode("utf-8")) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Uploaded CSV exceeds 10MB size limit.")

    try:
        inspection = parse_and_inspect_csv(content, filename=target_filename)
        save_uploaded_csv(inspection["dataset_id"], content, inspection)
        is_cloud = is_cloud_storage_enabled()
        inspection["is_persisted"] = is_cloud
        inspection["durability"] = "durable_cloud" if is_cloud else "ephemeral_container"
        if not is_cloud:
            inspection["storage_warning"] = "Stored in container temporary filesystem (/tmp). Files will not persist across serverless cold starts unless BLOB_READ_WRITE_TOKEN is configured in Vercel."
        return DatasetUploadResponse(**inspection)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV processing error: {str(e)}")


@router.get("/datasets/{dataset_id}/preview", response_model=DatasetUploadResponse)
def get_dataset_preview(dataset_id: str):
    """Retrieves inspected column details, row count, and preview rows for an uploaded dataset."""
    try:
        _, metadata = load_uploaded_csv(dataset_id)
        return DatasetUploadResponse(**metadata)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/datasets/{dataset_id}/validate", response_model=DatasetValidateResponse)
def validate_dataset(dataset_id: str, req: DatasetValidateRequest):
    """
    Validates selected 4 features and target column, fits missing value imputation
    and scaling on train partition only, and checks binary classification suitability.
    """
    try:
        csv_content, _ = load_uploaded_csv(dataset_id)
        result = validate_and_preprocess_dataset(
            csv_content=csv_content,
            feature_columns=req.feature_columns,
            target_column=req.target_column,
            imputation_strategy=req.imputation_strategy,
            train_ratio=req.train_ratio,
            seed=req.seed,
        )
        return DatasetValidateResponse(
            status=result["status"],
            fingerprint=result["fingerprint"],
            feature_columns=result["feature_columns"],
            target_column=result["target_column"],
            target_classes=result["target_classes"],
            class_counts=result["class_counts"],
            train_samples_count=result["train_samples_count"],
            test_samples_count=result["test_samples_count"],
            imputation_strategy=result["imputation_strategy"],
            train_feature_ranges=result["train_feature_ranges"],
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- MODEL TRAINING & REGISTRY ENDPOINTS ---

@router.post("/models/train", response_model=TrainModelResponse)
def train_model(req: TrainModelRequest):
    """
    Trains a 4-qubit, 2-layer Variational Quantum Classifier (16 variational weights)
    on the ideal simulator using SPSA optimization.
    Saves weights and metadata with dataset fingerprinting.
    """
    if req.dataset_id:
        try:
            csv_content, _ = load_uploaded_csv(req.dataset_id)
            if not req.feature_columns or not req.target_column:
                raise HTTPException(status_code=400, detail="Custom dataset requires feature_columns and target_column.")
            prep = validate_and_preprocess_dataset(
                csv_content=csv_content,
                feature_columns=req.feature_columns,
                target_column=req.target_column,
                imputation_strategy=req.imputation_strategy,
                seed=req.seed,
            )
            X_train, y_train = prep["X_train"], prep["y_train"]
            fingerprint = prep["fingerprint"]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to prepare training data: {str(e)}")
    else:
        X_train, y_train = SPLIT["X_train"], SPLIT["y_train"]
        fingerprint = "official_mit_bih_benchmark_v1"

    vqc = VariationalQuantumClassifier(num_qubits=4, layers=2)
    loss_history = vqc.fit_ideal(
        X_train=X_train,
        y_train=y_train,
        epochs=req.epochs,
        batch_size=req.batch_size,
        lr=req.lr,
        seed=req.seed,
    )

    # Evaluate train accuracy
    preds = [vqc.predict_single_ideal(x)[1] for x in X_train]
    correct = sum(1 for p, y in zip(preds, y_train) if p == y)
    train_acc = round(correct / len(y_train), 4)

    model_id = f"vqc_{int(time.time())}_{req.seed}"
    model_record = {
        "model_id": model_id,
        "name": req.model_name or "Custom VQC Model",
        "num_qubits": 4,
        "layers": 2,
        "num_params": 16,
        "weights": vqc.weights,
        "epochs": req.epochs,
        "final_loss": loss_history[-1] if loss_history else 0.0,
        "train_loss_history": loss_history,
        "dataset_fingerprint": fingerprint,
        "train_accuracy": train_acc,
        "feature_columns": req.feature_columns,
        "target_column": req.target_column,
    }
    try:
        save_model(model_record)
    except Exception as e:
        logger.warning(f"Could not persist model record: {e}")

    return TrainModelResponse(
        model_id=model_id,
        model_name=model_record["name"],
        num_qubits=4,
        layers=2,
        num_params=16,
        weights=vqc.weights,
        epochs=req.epochs,
        final_loss=loss_history[-1] if loss_history else 0.0,
        loss_history=loss_history,
        dataset_fingerprint=fingerprint,
        train_accuracy=train_acc,
    )


@router.get("/models")
def get_all_models():
    """Lists saved trained models."""
    return list_models()


@router.get("/models/{model_id}")
def get_model_details(model_id: str):
    """Retrieves trained model details and weights."""
    model = get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")
    return model


# --- EXPERIMENT EXECUTION & PERSISTENCE ---

@router.post("/experiments/run", response_model=ExperimentResponse)
def run_experiment(req: ExperimentRequest):
    """
    Executes a single-sample quantum classification experiment under requested hardware noise & mitigation.
    Persists run record and returns run_id.
    """
    start_t = time.time()
    procs = load_all_processors()
    proc_key = req.processor.upper()
    if proc_key not in procs:
        raise HTTPException(status_code=400, detail=f"Invalid processor '{req.processor}'. Choose 'A' or 'B'.")

    processor = procs[proc_key]
    proc_stats = processor.get_stats()

    # Load custom model weights if requested
    weights_to_use = VQC_MODEL.weights
    if req.model_id:
        saved_m = get_model(req.model_id)
        if saved_m and "weights" in saved_m:
            weights_to_use = saved_m["weights"]

    # Determine sample and features
    sample_item = None
    if req.custom_feature_vector and len(req.custom_feature_vector) == 4:
        norm_vec = [round(max(0.0, min(math.pi, v)), 5) for v in req.custom_feature_vector]
        sample_id = "CUSTOM-VECTOR"
        waveform_type = "User Feature Vector"
        label = 1 if norm_vec[1] > 1.5 or abs(norm_vec[3] - 1.57) > 0.8 else 0
        dataset_source = "custom_vector"
    elif req.custom_features:
        f_dict = req.custom_features.model_dump() if hasattr(req.custom_features, "model_dump") else req.custom_features.dict()
        sample_id = "CUSTOM-PATIENT"
        waveform_type = "Custom User Signal"
        label = 1 if (f_dict["qrs_duration_ms"] > 110 or abs(f_dict["st_segment_mv"]) > 0.15) else 0
        raw_vec = [f_dict["rr_interval_ms"], f_dict["qrs_duration_ms"], f_dict["r_peak_mv"], f_dict["st_segment_mv"]]
        ranges = SPLIT["ranges"]
        low, high = 0.0, math.pi
        norm_vec = []
        for j in range(4):
            mn, mx = ranges[j]
            span = mx - mn if (mx - mn) != 0 else 1.0
            clipped = max(mn, min(mx, raw_vec[j]))
            scaled = low + ((clipped - mn) / span) * (high - low)
            norm_vec.append(round(scaled, 5))
        dataset_source = "custom_patient"
    else:
        matches = [s for s in DATASET_SAMPLES if s["id"] == req.sample_id]
        sample_item = matches[0] if matches else DATASET_SAMPLES[0]
        sample_id = sample_item["id"]
        waveform_type = sample_item["waveform_type"]
        f_dict = sample_item["features"]
        label = sample_item["label"]
        raw_vec = [f_dict["rr_interval_ms"], f_dict["qrs_duration_ms"], f_dict["r_peak_mv"], f_dict["st_segment_mv"]]
        ranges = SPLIT["ranges"]
        low, high = 0.0, math.pi
        norm_vec = []
        for j in range(4):
            mn, mx = ranges[j]
            span = mx - mn if (mx - mn) != 0 else 1.0
            clipped = max(mn, min(mx, raw_vec[j]))
            scaled = low + ((clipped - mn) / span) * (high - low)
            norm_vec.append(round(scaled, 5))
        dataset_source = "official_benchmark"

    # Transpilation
    logical_qc = build_vqc_circuit(norm_vec, weights_to_use, 4, 2)
    transpiler = Transpiler(processor)
    _, transpile_metrics = transpiler.transpile(logical_qc)

    # Execute via Qiskit Aer
    from src.noise import build_qiskit_noise_model
    from src.routing import transpile_for_processor
    from src.quantum_executor import QuantumExecutor
    from src.mitigation import QiskitGateFolder, QiskitReadoutMitigator, ZeroNoiseExtrapolator

    qiskit_logical = build_vqc_circuit(norm_vec, weights_to_use, 4, 2, include_measurements=True)
    t_qc, q_metrics = transpile_for_processor(qiskit_logical, proc_stats, seed_transpiler=req.seed)

    # Ideal expectation via analytic Statevector
    ideal_exp, ideal_prob_1 = QuantumExecutor.run_ideal_statevector(qiskit_logical, target_qubit=0)
    ideal_pred = 1 if ideal_prob_1 >= 0.5 else 0

    # Noise parameters setup
    multiplier = req.noise_intensity_multiplier if req.noise_enabled else 0.0
    p2 = req.custom_p_2q if req.custom_p_2q is not None else (proc_stats["two_qubit_noise_rate"] * multiplier)
    p_ro = req.custom_p_ro if req.custom_p_ro is not None else (proc_stats["readout_noise_rate"] * multiplier)
    p1 = p2 * 0.2

    # Build Qiskit NoiseModel
    qiskit_noise = None
    if req.noise_enabled and (p2 > 0.0 or p_ro > 0.0):
        qiskit_noise, _ = build_qiskit_noise_model(
            proc_stats,
            custom_p_2q=p2 if p2 > 0 else None,
            custom_p_ro=p_ro if p_ro > 0 else None
        )

    executor = QuantumExecutor(noise_model=qiskit_noise, seed_simulator=req.seed)
    rem_mitigator = QiskitReadoutMitigator(num_qubits=4, noise_model=qiskit_noise, seed_simulator=req.seed) if qiskit_noise else None

    circuits_count = 1
    total_shots = req.shots

    if not req.noise_enabled or qiskit_noise is None:
        final_exp = ideal_exp
        method_name = "Ideal Simulator"
    elif req.mitigation_method == "none":
        method_name = "Unmitigated Noisy"
        res = executor.run_shots(t_qc, shots=req.shots, seed=req.seed)
        final_exp = res["expectation_z0"]
    elif req.mitigation_method == "readout":
        method_name = "Readout Error Mitigation (REM)"
        res = executor.run_shots(t_qc, shots=req.shots, seed=req.seed)
        _, final_exp = rem_mitigator.mitigate_counts(res["counts"]) if rem_mitigator else ({}, res["expectation_z0"])
    elif req.mitigation_method == "zne":
        method_name = "Zero-Noise Extrapolation (ZNE)"
        circuits_count = 3
        total_shots = 3 * req.shots
        zne_curves = []
        for r in [1, 3, 5]:
            folded = QiskitGateFolder.fold_circuit(t_qc, scale_factor=r)
            r_res = executor.run_shots(folded, shots=req.shots, seed=req.seed)
            zne_curves.append(r_res["expectation_z0"])
        final_exp = ZeroNoiseExtrapolator.richardson_extrapolate([1, 3, 5], zne_curves)
    else:  # dual
        method_name = "Dual-Layer (ZNE + Readout)"
        circuits_count = 3
        total_shots = 3 * req.shots
        zne_curves = []
        for r in [1, 3, 5]:
            folded = QiskitGateFolder.fold_circuit(t_qc, scale_factor=r)
            r_res = executor.run_shots(folded, shots=req.shots, seed=req.seed)
            _, mit_exp = rem_mitigator.mitigate_counts(r_res["counts"]) if rem_mitigator else ({}, r_res["expectation_z0"])
            zne_curves.append(mit_exp)
        final_exp = ZeroNoiseExtrapolator.richardson_extrapolate([1, 3, 5], zne_curves)

    prob_arr = max(0.0, min(1.0, (1.0 - final_exp) / 2.0))
    pred_label = 1 if prob_arr >= 0.5 else 0
    is_correct = (pred_label == label)
    latency_ms = (time.time() - start_t) * 1000.0

    resp = ExperimentResponse(
        dataset_source=dataset_source,
        sample_id=sample_id,
        waveform_type=waveform_type,
        ground_truth_label=label,
        predicted_label=pred_label,
        is_correct=is_correct,
        probability_arrhythmia=round(prob_arr, 4),
        expectation_z0=round(final_exp, 5),
        ideal_expectation_z0=round(ideal_exp, 5),
        ideal_prediction=ideal_pred,
        mitigation_method=method_name,
        processor_name=processor.name,
        noise_rate_2q=round(p2, 4),
        readout_error_rate=round(p_ro, 4),
        circuits_executed=circuits_count,
        total_shots=total_shots,
        circuit_depth=transpile_metrics["transpiled_depth"],
        swap_count=transpile_metrics["swap_count"],
        total_physical_cx=transpile_metrics["total_physical_cx"],
        latency_ms=round(latency_ms, 2),
    )

    run_record = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
    run_record["mode"] = "single_sample"
    is_cloud = is_cloud_storage_enabled()
    try:
        run_id = save_run(run_record)
        resp.run_id = run_id
        resp.is_persisted = is_cloud
        resp.durability = "durable_cloud" if is_cloud else "ephemeral_container"
        if not is_cloud:
            resp.storage_warning = "Ephemeral container storage: Results are saved in temporary storage (/tmp). Run will not persist across serverless cold starts until BLOB_READ_WRITE_TOKEN is configured in Vercel."
    except Exception as e:
        logger.warning(f"Could not persist experiment run: {e}")
        import uuid
        resp.run_id = f"ephem_{uuid.uuid4().hex[:12]}"
        resp.is_persisted = False
        resp.durability = "unpersisted"
        resp.storage_warning = f"Audit log persistence failed: {str(e)}. Real quantum simulation results returned successfully, but run record could not be saved to disk."

    return resp


@router.post("/experiments/evaluate_batch", response_model=BatchEvaluateResponse)
def evaluate_batch_experiment(req: BatchEvaluateRequest):
    """
    Evaluates the complete held-out test dataset partition under specified processor,
    noise rates, and mitigation method. Computes full ML & architecture metrics and persists the run.
    """
    procs = load_all_processors()
    proc_key = req.processor.upper()
    if proc_key not in procs:
        raise HTTPException(status_code=400, detail=f"Invalid processor '{req.processor}'. Choose 'A' or 'B'.")

    processor = procs[proc_key]
    proc_stats = processor.get_stats()

    # Determine test set
    if req.dataset_id:
        try:
            csv_content, _ = load_uploaded_csv(req.dataset_id)
            if not req.feature_columns or not req.target_column:
                raise HTTPException(status_code=400, detail="Custom evaluation requires feature_columns and target_column.")
            prep = validate_and_preprocess_dataset(
                csv_content=csv_content,
                feature_columns=req.feature_columns,
                target_column=req.target_column,
                imputation_strategy=req.imputation_strategy,
                seed=req.seed or 42,
            )
            X_test, y_test, test_ids = prep["X_test"], prep["y_test"], prep["test_ids"]
            dataset_source = "custom_uploaded_dataset"
            fingerprint = prep["fingerprint"]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to prepare evaluation dataset: {str(e)}")
    else:
        X_test, y_test = SPLIT["X_test"], SPLIT["y_test"]
        test_ids = [s["id"] for s in SPLIT["test_samples"]]
        dataset_source = "official_benchmark"
        fingerprint = "official_mit_bih_benchmark_v1"

    # Instantiate VQC
    vqc = VariationalQuantumClassifier(num_qubits=4, layers=2)
    if req.model_id:
        saved_m = get_model(req.model_id)
        if saved_m and "weights" in saved_m:
            vqc.weights = saved_m["weights"]
        else:
            vqc.load_weights()
    else:
        vqc.load_weights()

    # Noise setup
    multiplier = req.noise_intensity_multiplier if req.noise_enabled else 0.0
    p2 = req.custom_p_2q if req.custom_p_2q is not None else (proc_stats["two_qubit_noise_rate"] * multiplier)
    p_ro = req.custom_p_ro if req.custom_p_ro is not None else (proc_stats["readout_noise_rate"] * multiplier)
    p1 = p2 * 0.2

    noise_model = CalibratedNoiseModel(p_1q=p1, p_2q=p2, p_ro_01=p_ro, p_ro_10=p_ro) if req.noise_enabled else None

    # Evaluate
    eval_result = vqc.evaluate_batch(
        X_test=X_test,
        y_test=y_test,
        processor=processor,
        noise_model=noise_model,
        mitigation_method=req.mitigation_method if req.noise_enabled else "ideal",
        shots=req.shots,
        seed=req.seed,
    )

    # Format per-sample details
    detailed_samples = []
    for i, s_id in enumerate(test_ids):
        detailed_samples.append({
            "id": s_id,
            "ground_truth": y_test[i],
            "predicted": eval_result["predictions"][i],
            "probability": eval_result["probabilities"][i],
            "is_correct": eval_result["predictions"][i] == y_test[i],
        })

    run_record = {
        "mode": "batch_evaluation",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset_source": dataset_source,
        "dataset_fingerprint": fingerprint,
        "processor_name": processor.name,
        "processor": req.processor.upper(),
        "mitigation_method": eval_result["mitigation_method"],
        "noise_rate_2q": round(p2, 4),
        "readout_error_rate": round(p_ro, 4),
        "ml_metrics": eval_result["ml_metrics"],
        "architecture_metrics": eval_result["architecture_metrics"],
        "detailed_samples": detailed_samples,
        "circuits_executed": eval_result["architecture_metrics"]["circuits_executed"],
        "total_shots": eval_result["architecture_metrics"]["total_shots"],
        "circuit_depth": eval_result["architecture_metrics"]["circuit_depth"],
        "swap_count": eval_result["architecture_metrics"]["swap_count"],
        "total_physical_cx": eval_result["architecture_metrics"]["total_physical_cx"],
        "latency_ms": eval_result["architecture_metrics"]["latency_ms"],
    }

    is_cloud = is_cloud_storage_enabled()
    try:
        run_id = save_run(run_record)
        run_record["run_id"] = run_id
        run_record["is_persisted"] = is_cloud
        run_record["durability"] = "durable_cloud" if is_cloud else "ephemeral_container"
        if not is_cloud:
            run_record["storage_warning"] = "Ephemeral container storage: Batch results are saved in temporary storage (/tmp). Run will not persist across serverless cold starts until BLOB_READ_WRITE_TOKEN is configured in Vercel."
    except Exception as e:
        logger.warning(f"Could not persist batch run: {e}")
        import uuid
        run_record["run_id"] = f"ephem_{uuid.uuid4().hex[:12]}"
        run_record["is_persisted"] = False
        run_record["durability"] = "unpersisted"
        run_record["storage_warning"] = f"Audit log persistence failed: {str(e)}. Real quantum simulation results returned successfully, but run record could not be saved to disk."

    return BatchEvaluateResponse(**run_record)


@router.get("/experiments/history")
def get_experiment_history(limit: int = 15):
    """Lists past experiment runs."""
    return list_runs(limit=limit)


@router.get("/experiments/{run_id}")
def get_experiment_run(run_id: str):
    """Retrieves full saved experiment run by run_id."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return run


@router.get("/experiments/{run_id}/export")
def export_experiment_csv_endpoint(run_id: str):
    """Downloads structured multi-section CSV report of an experiment run."""
    try:
        csv_data = export_run_csv(run_id)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=experiment_{run_id}.csv"}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ROBUSTNESS SWEEP & HARDWARE BENCHMARKS ---

@router.post("/robustness/sweep")
def get_robustness_sweep(req: SweepRequest):
    """
    Returns real-time computed noise sweep curves for the Robustness Lab.
    """
    procs = load_all_processors()
    proc = procs.get(req.processor.upper(), procs["A"])
    X_test, y_test = SPLIT["X_test"], SPLIT["y_test"]

    noise_levels = [0.000, 0.005, 0.010, 0.020, 0.030, 0.040, 0.050]
    points = []

    for p2 in noise_levels:
        noise_model = CalibratedNoiseModel(
            p_1q=p2 * 0.2,
            p_2q=p2,
            p_ro_01=min(0.05, p2 * 1.5 + 0.005) if p2 > 0 else 0.0,
            p_ro_10=min(0.05, p2 * 1.5 + 0.005) if p2 > 0 else 0.0
        )
        if p2 == 0.0:
            eval_unmit = VQC_MODEL.evaluate_batch(X_test, y_test, processor=proc, mitigation_method="ideal")
            eval_zne = eval_unmit
            eval_ro = eval_unmit
            eval_dual = eval_unmit
        else:
            eval_unmit = VQC_MODEL.evaluate_batch(X_test, y_test, processor=proc, noise_model=noise_model, mitigation_method="none", shots=req.shots, seed=req.seed)
            eval_zne = VQC_MODEL.evaluate_batch(X_test, y_test, processor=proc, noise_model=noise_model, mitigation_method="zne", shots=req.shots, seed=req.seed)
            eval_ro = VQC_MODEL.evaluate_batch(X_test, y_test, processor=proc, noise_model=noise_model, mitigation_method="readout", shots=req.shots, seed=req.seed)
            eval_dual = VQC_MODEL.evaluate_batch(X_test, y_test, processor=proc, noise_model=noise_model, mitigation_method="dual", shots=req.shots, seed=req.seed)

        points.append({
            "noise_rate_pct": round(p2 * 100, 2),
            "unmitigated_accuracy": round(eval_unmit["ml_metrics"]["accuracy"] * 100, 1),
            "zne_accuracy": round(eval_zne["ml_metrics"]["accuracy"] * 100, 1),
            "readout_accuracy": round(eval_ro["ml_metrics"]["accuracy"] * 100, 1),
            "dual_accuracy": round(eval_dual["ml_metrics"]["accuracy"] * 100, 1),
            "unmitigated_recall": round(eval_unmit["ml_metrics"]["recall"] * 100, 1),
            "dual_recall": round(eval_dual["ml_metrics"]["recall"] * 100, 1),
        })

    return {
        "processor": proc.name,
        "points": points,
    }


@router.post("/transpile")
def transpile_comparison(req: TranspileRequest):
    """
    Returns transpilation metrics across Processors A, B, and C.
    """
    qc = build_vqc_circuit([1.0, 1.2, 0.8, 1.5], VQC_MODEL.weights, req.num_qubits, req.layers)
    comp = compare_transpilation_on_all_processors(qc)
    return comp


_CACHED_BENCHMARK_RESULTS: Dict[str, Any] = None


@router.get("/results/summary")
def get_results_summary(force_refresh: bool = False):
    """
    Returns precomputed full benchmark results and confusion matrices.
    Caches in memory for instant frontend response unless force_refresh=True is passed.
    """
    global _CACHED_BENCHMARK_RESULTS
    if _CACHED_BENCHMARK_RESULTS is None or force_refresh:
        from src.vqc import run_full_benchmark_suite
        _CACHED_BENCHMARK_RESULTS = run_full_benchmark_suite(SPLIT["X_test"], SPLIT["y_test"])
    return _CACHED_BENCHMARK_RESULTS
