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

