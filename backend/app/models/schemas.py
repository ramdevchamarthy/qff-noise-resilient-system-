"""
Pydantic Schemas for FastAPI Backend.
Supports official benchmark and real dataset upload, validation, training, and evaluation workflows.
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
    custom_feature_vector: Optional[List[float]] = None
    model_id: Optional[str] = None
    processor: str = Field(default="A", description="Processor 'A' (5q) or 'B' (9q)")
    noise_enabled: bool = True
    noise_intensity_multiplier: float = Field(default=1.0, ge=0.0, le=5.0)
    custom_p_2q: Optional[float] = Field(default=None, ge=0.0, le=0.10)
    custom_p_ro: Optional[float] = Field(default=None, ge=0.0, le=0.10)
    mitigation_method: str = Field(default="dual", description="'none', 'readout', 'zne', 'dual'")
    shots: int = Field(default=1024, ge=256, le=8192)
    seed: Optional[int] = 42


class ExperimentResponse(BaseModel):
    run_id: Optional[str] = None
    dataset_source: Optional[str] = "official_benchmark"
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
    is_persisted: bool = False
    durability: str = "ephemeral_container"
    storage_warning: Optional[str] = None


class SweepRequest(BaseModel):
    processor: str = "A"
    shots: int = 1024
    seed: Optional[int] = 42


class TranspileRequest(BaseModel):
    layers: int = 2
    num_qubits: int = 4


# --- DATASET & MODEL SCHEMAS ---

class DatasetUploadRequest(BaseModel):
    raw_csv: str = Field(..., description="Raw CSV string content")
    filename: Optional[str] = "dataset.csv"


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    headers: List[str]
    columns: List[Dict[str, Any]]
    duplicate_rows: int
    total_missing_cells: int
    preview_rows: List[Dict[str, Any]]
    fingerprint: str
    is_persisted: bool = False
    durability: str = "ephemeral_container"
    storage_warning: Optional[str] = None


class DatasetValidateRequest(BaseModel):
    dataset_id: Optional[str] = None
    csv_content: Optional[str] = None
    feature_columns: List[str] = Field(..., min_length=4, max_length=4)
    target_column: str
    imputation_strategy: str = Field(default="mean", description="'mean', 'median', 'drop'")
    train_ratio: float = Field(default=0.8, ge=0.5, le=0.95)
    seed: int = 42


class DatasetValidateResponse(BaseModel):
    status: str
    fingerprint: str
    feature_columns: List[str]
    target_column: str
    target_classes: List[Any]
    class_counts: Dict[str, int]
    train_samples_count: int
    test_samples_count: int
    imputation_strategy: str
    train_feature_ranges: List[Dict[str, Any]]


class TrainModelRequest(BaseModel):
    dataset_id: Optional[str] = None
    feature_columns: Optional[List[str]] = None
    target_column: Optional[str] = None
    imputation_strategy: str = "mean"
    epochs: int = Field(default=25, ge=5, le=150)
    batch_size: int = Field(default=30, ge=8, le=100)
    lr: float = Field(default=0.20, ge=0.01, le=1.0)
    seed: int = 42
    model_name: Optional[str] = "Custom VQC Model"


class TrainModelResponse(BaseModel):
    model_id: str
    model_name: str
    num_qubits: int
    layers: int
    num_params: int
    weights: List[float]
    epochs: int
    final_loss: float
    loss_history: List[float]
    dataset_fingerprint: str
    train_accuracy: float


class BatchEvaluateRequest(BaseModel):
    dataset_id: Optional[str] = None
    model_id: Optional[str] = None
    feature_columns: Optional[List[str]] = None
    target_column: Optional[str] = None
    imputation_strategy: str = "mean"
    processor: str = "A"
    noise_enabled: bool = True
    noise_intensity_multiplier: float = 1.0
    custom_p_2q: Optional[float] = None
    custom_p_ro: Optional[float] = None
    mitigation_method: str = "dual"
    shots: int = 1024
    seed: Optional[int] = 42


class BatchEvaluateResponse(BaseModel):
    run_id: str
    timestamp: str
    dataset_source: str
    dataset_fingerprint: Optional[str] = None
    processor_name: str
    mitigation_method: str
    noise_rate_2q: float
    readout_error_rate: float
    ml_metrics: Dict[str, Any]
    architecture_metrics: Dict[str, Any]
    detailed_samples: List[Dict[str, Any]]
    is_persisted: bool = False
    durability: str = "ephemeral_container"
    storage_warning: Optional[str] = None
