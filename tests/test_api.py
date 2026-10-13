import pytest
from backend.app.api.routes import (
    get_health,
    get_samples,
    get_processors,
    run_experiment,
    transpile_comparison,
)
from backend.app.models.schemas import ExperimentRequest, TranspileRequest


def test_api_health():
    res = get_health()
    assert res.status == "ok"
    assert "PS-Q3" in res.problem_statement


def test_api_samples():
    samples = get_samples()
    assert isinstance(samples, list)
    assert len(samples) > 0
    assert "waveform" in samples[0]
    assert "features" in samples[0]


def test_api_processors():
    procs = get_processors()
    assert "A" in procs
    assert "B" in procs
    assert "C" in procs
    assert procs["A"]["num_qubits"] == 5
    assert procs["B"]["num_qubits"] == 9


def test_api_experiment_run():
    req = ExperimentRequest(
        sample_id="PAT-1000",
        processor="A",
        noise_enabled=True,
        mitigation_method="dual",
        shots=512,
        seed=42
    )
    res = run_experiment(req)
    assert res.predicted_label in [0, 1]
    assert 0.0 <= res.probability_arrhythmia <= 1.0
    assert res.circuits_executed == 3
    assert res.processor_name == "Processor A"


def test_api_transpile_comparison():
    req = TranspileRequest(layers=2, num_qubits=4)
    res = transpile_comparison(req)
    assert "A" in res
    assert "B" in res
    assert "C" in res
    assert res["A"]["total_physical_cx"] >= 8


def test_api_results_summary():
    from backend.app.api.routes import get_results_summary
    res = get_results_summary()
    assert "classical_baseline" in res
    assert "ideal_vqc" in res
    assert "processor_a_unmitigated" in res
    assert "processor_a_mitigated" in res
    assert "processor_b_unmitigated" in res
    assert "processor_b_mitigated" in res
    assert res["classical_baseline"]["ml_metrics"]["sample_count"] == 50
    assert 0.0 <= res["processor_a_mitigated"]["ml_metrics"]["accuracy"] <= 1.0


def test_api_robustness_sweep():
    from backend.app.api.routes import get_robustness_sweep
    from backend.app.models.schemas import SweepRequest
    req = SweepRequest(processor="A", shots=256, seed=42)
    res = get_robustness_sweep(req)
    assert res["processor"] == "Processor A"
    assert len(res["points"]) == 7
    p0 = res["points"][0]
    assert p0["noise_rate_pct"] == 0.0
    assert "dual_accuracy" in p0
    assert "unmitigated_accuracy" in p0


def test_api_custom_patient_features():
    from backend.app.models.schemas import ECGFeatures
    custom_f = ECGFeatures(
        rr_interval_ms=520.0,
        qrs_duration_ms=135.0,
        r_peak_mv=1.75,
        st_segment_mv=-0.22,
    )
    req = ExperimentRequest(
        sample_id="CUSTOM",
        custom_features=custom_f,
        processor="B",
        noise_enabled=True,
        mitigation_method="dual",
        shots=512,
        seed=42,
    )
    res = run_experiment(req)
    assert res.sample_id == "CUSTOM-PATIENT"
    assert res.waveform_type == "Custom User Signal"
    assert res.ground_truth_label == 1
    assert res.predicted_label in [0, 1]
    assert res.processor_name == "Processor B"

