"""
Pydantic Schemas for FastAPI Backend.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    track: str = "Quantum Machine Learning"
    problem_statement: str = "PS-Q3: Noise-Resilient Variational Classifier"
    event: str = "Qiskit Fall Fest 2026"


class ECGFeatures(BaseModel):
    rr_interval_ms: float = Field(..., description="R-R interval in ms")
    qrs_duration_ms: float = Field(..., description="QRS duration in ms")
    r_peak_mv: float = Field(..., description="R-peak amplitude in mV")
    st_segment_mv: float = Field(..., description="ST segment elevation/depression in mV")


class ExperimentRequest(BaseModel):
    sample_id: Optional[str] = "PAT-1000"
    custom_features: Optional[ECGFeatures] = None
    processor: str = Field(default="A", description="Processor 'A' (5q) or 'B' (9q)")
    noise_enabled: bool = True
    noise_intensity_multiplier: float = Field(default=1.0, ge=0.0, le=5.0)
    custom_p_2q: Optional[float] = Field(default=None, ge=0.0, le=0.10)
    custom_p_ro: Optional[float] = Field(default=None, ge=0.0, le=0.10)
    mitigation_method: str = Field(default="dual", description="'none', 'readout', 'zne', 'dual'")
    shots: int = Field(default=1024, ge=256, le=8192)
    seed: Optional[int] = 42


class ExperimentResponse(BaseModel):
    sample_id: str
    waveform_type: str
    ground_truth_label: int
    predicted_label: int
    is_correct: bool
    probability_arrhythmia: float
    expectation_z0: float
    ideal_expectation_z0: float
    ideal_prediction: int
    mitigation_method: str
    processor_name: str
    noise_rate_2q: float
    readout_error_rate: float
    circuits_executed: int
    total_shots: int
    circuit_depth: int
    swap_count: int
    total_physical_cx: int
    latency_ms: float


class SweepRequest(BaseModel):
    processor: str = "A"
    shots: int = 1024
    seed: Optional[int] = 42


class TranspileRequest(BaseModel):
    layers: int = 2
    num_qubits: int = 4
