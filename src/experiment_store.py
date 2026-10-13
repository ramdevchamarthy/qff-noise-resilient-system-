"""
Experiment and Model Persistence Store for Q-ResQ.
Persists experiment runs and trained models to data/experiments/ and data/models/.
Generates verifiable, reproducible CSV exports for downstream auditing.
"""

import csv
import io
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.storage import (
    save_experiment_run,
    load_experiment_run,
    list_experiment_runs,
    save_trained_model,
    load_trained_model,
    list_trained_models,
    get_writable_dir,
    get_read_dirs,
)

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "data" / "experiments"
MODELS_DIR = Path(__file__).resolve().parent.parent / "data" / "models"


def init_store_dirs():
    """Ensures storage directories exist safely."""
    get_writable_dir("experiments")
    get_writable_dir("models")


def save_run(run_data: Dict[str, Any]) -> str:
    """Saves an experiment run record to persistent storage and returns run_id."""
    return save_experiment_run(run_data)


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an experiment run record by run_id from persistent storage."""
    return load_experiment_run(run_id)


def list_runs(limit: int = 15) -> List[Dict[str, Any]]:
    """Returns recent experiment runs sorted newest first across all storage tiers."""
    return list_experiment_runs(limit=limit)


def export_run_csv(run_id: str) -> str:
    """
    Generates a structured multi-section CSV for a given run_id containing:
    1. Header metadata (Run ID, Processor, Noise, Mitigation, Resource accounting)
    2. Summary metrics (Accuracy, Recall, Precision, F1, Specificity, ROC-AUC)
    3. Sample-by-sample predictions and probabilities
    """
    run = get_run(run_id)
    if not run:
        raise FileNotFoundError(f"Run {run_id} not found.")

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["# Q-ResQ — Noise-Resilient Quantum Classifier Experiment Report"])
    writer.writerow(["# Generated", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())])
    writer.writerow([])

    writer.writerow(["--- METADATA & CONFIGURATION ---"])
    writer.writerow(["Field", "Value"])
    writer.writerow(["Run ID", run.get("run_id")])
    writer.writerow(["Timestamp", run.get("timestamp")])
    writer.writerow(["Target Processor", run.get("processor_name", run.get("processor"))])
    writer.writerow(["Mitigation Method", run.get("mitigation_method")])
    writer.writerow(["Noise Rate (p_2q)", run.get("noise_rate_2q", run.get("noise_rate"))])
    writer.writerow(["Readout Error Rate (p_ro)", run.get("readout_error_rate")])
    writer.writerow(["Circuits Executed", run.get("circuits_executed")])
    writer.writerow(["Total Shots Sampled", run.get("total_shots")])
    writer.writerow(["Transpiled Depth", run.get("circuit_depth")])
    writer.writerow(["SWAP Count", run.get("swap_count")])
    writer.writerow(["Physical CX Count", run.get("total_physical_cx")])
    writer.writerow(["Execution Latency (ms)", run.get("latency_ms")])
    writer.writerow(["Dataset Source", run.get("dataset_source", "official_benchmark")])
    if "dataset_fingerprint" in run:
        writer.writerow(["Dataset Fingerprint", run.get("dataset_fingerprint")])
    writer.writerow([])

    if "ml_metrics" in run:
        m = run["ml_metrics"]
        writer.writerow(["--- AGGREGATE EVALUATION METRICS ---"])
        writer.writerow(["Metric", "Score (%)"])
        writer.writerow(["Accuracy", f"{m.get('accuracy', 0.0) * 100:.2f}"])
        writer.writerow(["Recall (Sensitivity)", f"{m.get('recall', 0.0) * 100:.2f}"])
        writer.writerow(["Precision", f"{m.get('precision', 0.0) * 100:.2f}"])
        writer.writerow(["F1 Score", f"{m.get('f1_score', 0.0) * 100:.2f}"])
        writer.writerow(["Specificity", f"{m.get('specificity', 0.0) * 100:.2f}"])
        if "roc_auc" in m and m["roc_auc"] is not None:
            writer.writerow(["ROC AUC", f"{m.get('roc_auc', 0.0):.4f}"])
        writer.writerow([])

    if "detailed_samples" in run:
        writer.writerow(["--- HELD-OUT TEST SAMPLES PREDICTIONS ---"])
        writer.writerow(["Sample ID", "Ground Truth", "Predicted Label", "Arrhythmia Prob", "Status"])
        for s in run["detailed_samples"]:
            writer.writerow([
                s.get("id"),
                s.get("ground_truth"),
                s.get("predicted"),
                f"{s.get('probability', 0.0):.4f}",
                "CORRECT" if s.get("ground_truth") == s.get("predicted") else "MISCLASSIFIED",
            ])

    return output.getvalue()


def save_model(model_data: Dict[str, Any]) -> str:
    """Saves a trained VQC model configuration and parameters to persistent storage."""
    return save_trained_model(model_data)


def get_model(model_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a model by model_id from persistent storage."""
    return load_trained_model(model_id)


def list_models() -> List[Dict[str, Any]]:
    """Lists saved models from persistent storage."""
    return list_trained_models()
