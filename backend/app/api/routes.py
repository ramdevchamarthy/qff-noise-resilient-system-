"""
API Route Handlers for Noise-Resilient Quantum System.
"""

import math
import random
import time
from pathlib import Path
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    HealthResponse,
    ExperimentRequest,
    ExperimentResponse,
    SweepRequest,
    TranspileRequest,
)
from src.data_loader import generate_ecg_dataset, get_train_test_split, normalize_features
from src.processors import load_all_processors, load_processor
from src.noise_models import CalibratedNoiseModel
from src.vqc import VariationalQuantumClassifier, build_vqc_circuit
from src.transpiler import Transpiler, compare_transpilation_on_all_processors
from src.mitigation import ReadoutMitigator, ZeroNoiseExtrapolator

router = APIRouter()

# Preload dataset and trained VQC model
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
    # Synthetic ECG preview points for waveform visualization
    enriched = []
    for s in featured:
        f = s["features"]
        is_arr = s["label"] == 1
        # Generate representative ECG waveform cycle points (P, Q, R, S, T)
        t_steps = 60
        wave = []
        for step in range(t_steps):
            phase = (step / t_steps) * 2 * math.pi
            # Base rhythm
            base = 0.1 * math.sin(phase)
            # QRS spike around 40%
            r_center = 0.40
            dist = abs((step / t_steps) - r_center)
            if dist < 0.05:
                spike = f["r_peak_mv"] * math.exp(- (dist / 0.015) ** 2)
            else:
                spike = 0.0
            # ST deviation
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


@router.post("/experiments/run", response_model=ExperimentResponse)
def run_experiment(req: ExperimentRequest):
    """
    Executes a single-sample quantum classification experiment under requested hardware noise & mitigation.
    """
    start_t = time.time()
    procs = load_all_processors()
    proc_key = req.processor.upper()
    if proc_key not in procs:
        raise HTTPException(status_code=400, detail=f"Invalid processor '{req.processor}'. Choose 'A' or 'B'.")

    processor = procs[proc_key]
    proc_stats = processor.get_stats()

    # Determine sample and features
    sample_item = None
    if req.custom_features:
        f_dict = req.custom_features.dict()
        sample_id = "CUSTOM-PATIENT"
        waveform_type = "Custom User Signal"
        label = 1 if (f_dict["qrs_duration_ms"] > 110 or abs(f_dict["st_segment_mv"]) > 0.15) else 0
    else:
        # Find sample by ID
        matches = [s for s in DATASET_SAMPLES if s["id"] == req.sample_id]
        sample_item = matches[0] if matches else DATASET_SAMPLES[0]
        sample_id = sample_item["id"]
        waveform_type = sample_item["waveform_type"]
        f_dict = sample_item["features"]
        label = sample_item["label"]

    # Normalize feature vector
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

    # Transpilation
    logical_qc = build_vqc_circuit(norm_vec, VQC_MODEL.weights, 4, 2)
    transpiler = Transpiler(processor)
    _, transpile_metrics = transpiler.transpile(logical_qc)

    # Ideal expectation
    from src.quantum_core import StatevectorSimulator
    sim = StatevectorSimulator(4)
    sim.execute_circuit(logical_qc)
    ideal_probs = sim.probabilities()
    ideal_exp = sim.expectation_value_z(0)
    ideal_pred = 1 if ((1.0 - ideal_exp) / 2.0) >= 0.5 else 0

    # Noise model setup
    multiplier = req.noise_intensity_multiplier if req.noise_enabled else 0.0
    p2 = req.custom_p_2q if req.custom_p_2q is not None else (proc_stats["two_qubit_noise_rate"] * multiplier)
    p_ro = req.custom_p_ro if req.custom_p_ro is not None else (proc_stats["readout_noise_rate"] * multiplier)
    p1 = p2 * 0.2

    noise_model = CalibratedNoiseModel(p_1q=p1, p_2q=p2, p_ro_01=p_ro, p_ro_10=p_ro)

    # Physical circuit execution
    phys_cx = transpile_metrics["total_physical_cx"]
    phys_1q = sum(cnt for op, cnt in logical_qc.count_ops().items() if op not in ["cx", "swap"])
    rem = ReadoutMitigator(noise_model, 4)
    rng = random.Random(req.seed)
    dim = 16
    mixed_p = 1.0 / dim

    circuits_count = 1
    total_shots = req.shots

    if not req.noise_enabled or (p2 == 0.0 and p_ro == 0.0):
        final_exp = ideal_exp
        method_name = "Ideal Simulator"
    elif req.mitigation_method == "none":
        method_name = "Unmitigated Noisy"
        F_gate = ((1.0 - p1) ** phys_1q) * ((1.0 - p2) ** phys_cx)
        p_noisy = [F_gate * p + (1.0 - F_gate) * mixed_p for p in ideal_probs]
        cal_matrix = noise_model.get_readout_calibration_matrix(4)
        p_dev = [sum(cal_matrix[r][c] * p_noisy[c] for c in range(dim)) for r in range(dim)]
        indices = rng.choices(range(dim), weights=p_dev, k=req.shots)
        n_counts: Dict[str, int] = {}
        for idx in indices:
            b_str = format(idx, "04b")
            n_counts[b_str] = n_counts.get(b_str, 0) + 1
        final_exp = sum((1.0 if int(b[-1]) == 0 else -1.0) * (c / req.shots) for b, c in n_counts.items())

    elif req.mitigation_method == "readout":
        method_name = "Readout Error Mitigation (REM)"
        F_gate = ((1.0 - p1) ** phys_1q) * ((1.0 - p2) ** phys_cx)
        p_noisy = [F_gate * p + (1.0 - F_gate) * mixed_p for p in ideal_probs]
        cal_matrix = noise_model.get_readout_calibration_matrix(4)
        p_dev = [sum(cal_matrix[r][c] * p_noisy[c] for c in range(dim)) for r in range(dim)]
        indices = rng.choices(range(dim), weights=p_dev, k=req.shots)
        n_counts = {}
        for idx in indices:
            b_str = format(idx, "04b")
            n_counts[b_str] = n_counts.get(b_str, 0) + 1
        _, final_exp = rem.mitigate_counts(n_counts)

    elif req.mitigation_method == "zne":
        method_name = "Zero-Noise Extrapolation (ZNE)"
        circuits_count = 3
        total_shots = 3 * req.shots
        zne_curves = []
        for r in [1, 3, 5]:
            r_cx = r * phys_cx
            F_r = ((1.0 - p1) ** phys_1q) * ((1.0 - p2) ** r_cx)
            p_r = [F_r * p + (1.0 - F_r) * mixed_p for p in ideal_probs]
            cal_matrix = noise_model.get_readout_calibration_matrix(4)
            p_dev = [sum(cal_matrix[row][c] * p_r[c] for c in range(dim)) for row in range(dim)]
            indices = rng.choices(range(dim), weights=p_dev, k=req.shots)
            r_counts = {}
            for idx in indices:
                b_str = format(idx, "04b")
                r_counts[b_str] = r_counts.get(b_str, 0) + 1
            r_exp = sum((1.0 if int(b[-1]) == 0 else -1.0) * (c / req.shots) for b, c in r_counts.items())
            zne_curves.append(r_exp)
        final_exp = ZeroNoiseExtrapolator.richardson_extrapolate([1, 3, 5], zne_curves)

    else:  # dual
        method_name = "Dual-Layer (ZNE + Readout)"
        circuits_count = 3
        total_shots = 3 * req.shots
        zne_curves = []
        for r in [1, 3, 5]:
            r_cx = r * phys_cx
            F_r = ((1.0 - p1) ** phys_1q) * ((1.0 - p2) ** r_cx)
            p_r = [F_r * p + (1.0 - F_r) * mixed_p for p in ideal_probs]
            cal_matrix = noise_model.get_readout_calibration_matrix(4)
            p_dev = [sum(cal_matrix[row][c] * p_r[c] for c in range(dim)) for row in range(dim)]
            indices = rng.choices(range(dim), weights=p_dev, k=req.shots)
            r_counts = {}
            for idx in indices:
                b_str = format(idx, "04b")
                r_counts[b_str] = r_counts.get(b_str, 0) + 1
            _, r_exp_mit = rem.mitigate_counts(r_counts)
            zne_curves.append(r_exp_mit)
        final_exp = ZeroNoiseExtrapolator.richardson_extrapolate([1, 3, 5], zne_curves)

    # Compute predicted probability and classification label
    prob_arr = max(0.0, min(1.0, (1.0 - final_exp) / 2.0))
    pred_label = 1 if prob_arr >= 0.5 else 0
    is_correct = (pred_label == label)
    latency_ms = (time.time() - start_t) * 1000.0

    return ExperimentResponse(
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


@router.get("/results/summary")
def get_results_summary():
    """
    Returns precomputed full benchmark results and confusion matrices.
    """
    from src.vqc import run_full_benchmark_suite
    results = run_full_benchmark_suite()
    return results
