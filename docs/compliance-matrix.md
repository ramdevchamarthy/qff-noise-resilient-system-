# QFF 2026 Hackathon — Phase 1 Compliance Matrix
## Problem Statement: PS-Q3 — Noise-Resilient Variational Classifier
**Track**: Quantum Machine Learning Track  
**Evaluation Target**: Qualification Stage (Phase 1)  
**Authoritative Hardware**: Processor A (5-qubit linear/star) and Processor B (9-qubit Heavy-Hex)

---

## 1. Phase 1 Requirements Verification Matrix

| Requirement | Official source and page/section | Required evidence | Existing implementation | Verification performed | Status | Remaining action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Selected Problem Statement** | *QFF Phase 1 Instructions*, Sec 2 & Rule 1 | Distinct identification of PS-Q3 throughout repository, documentation, and configs. | Explicitly declared as PS-Q3 in `README.md`, `main.ipynb`, `docs/`, `backend/`, and `src/benchmarks.py`. | Verified single problem statement focus across all markdown files and code headers. | **PASS** | None. Maintain PS-Q3 focus. |
| **2. Quantum Track Selection** | *Universal Challenge Framework*, p. 1-2 | Problem belongs to official Quantum Machine Learning Track. | Positioned in QML track tackling variational quantum classification under NISQ device noise. | Verified track alignment in documentation and technical architecture. | **PASS** | None. |
| **3. Processor A Architecture & Basis Gates** | *Universal Challenge Framework*, p. 2; *Q3 Guide*, Sec 6 | 5-qubit topology with edges `(0,1), (1,2), (1,3), (3,4)`; basis gates `['rz', 'sx', 'x', 'cx']`. | Defined in `processors/processor_A.json` and loaded via `src/transpiler.py` & `src/routing.py`. | Unit test `test_processor_loading` verifies exact coupling map (4 bidirectional edges) and 4 basis gates. | **PASS** | None. |
| **4. Processor B Architecture & Basis Gates** | *Universal Challenge Framework*, p. 2; *Q3 Guide*, Sec 6 | 9-qubit Heavy-Hex topology with 12 edges; basis gates `['rz', 'sx', 'x', 'cx']`. | Defined in `processors/processor_B.json` and loaded via `src/transpiler.py` & `src/routing.py`. | Unit test `test_processor_loading` verifies exact coupling map (12 bidirectional edges) and 4 basis gates. | **PASS** | None. |
| **5. Calibrated Device Noise Model** | *PS-Q3 Description*, p. 13; *Starter Notebook*, Sec 10 | Depolarizing 1Q error $p_{1q}=0.001$, 2Q error $p_{2q}=0.005$, readout error $p_{ro}=0.015$. | Implemented in `src/noise.py` via `build_qiskit_noise_model()` applying standard Qiskit Aer noise operators. | Unit tests in `tests/test_vqc.py` verify noise channels match official error rates. | **PASS** | None. |
| **6. Real Qiskit Circuits** | *Phase 1 Instructions*, Step 3; *Q3 Guide*, Sec 4 | Parametric `QuantumCircuit` using angle encoding and $R_y$/$R_z$ entangling variational ansatz. | Implemented in `src/vqc.py` with `build_vqc_circuit()` returning standard Qiskit `QuantumCircuit` objects. | Unit tests verify circuit structure, 4 qubits, 4 classical bits, and parameter assignment. | **PASS** | None. |
| **7. Qiskit Transpilation targeting Coupling Map** | *Phase 1 Instructions*, Step 4; *Q3 Guide*, Sec 6 | Circuits transpiled targeting processor coupling maps and basis gates. | `src/routing.py` executes `qiskit.transpile(circuit, coupling_map, basis_gates, optimization_level=1, seed_transpiler=42)`. | Verified: Proc A yields depth 31, 3 SWAPs, 17 CX; Proc B yields depth 18, 0 SWAPs, 8 CX. | **PASS** | None. |
| **8. Qiskit Aer Simulation** | *Phase 1 Instructions*, Step 4 | Real quantum simulation executed via `qiskit_aer.AerSimulator`. | Implemented in `src/quantum_executor.py` (`AerSimulator` with shot-based sampling and seed control). | Regression test verifies exact match between Aer execution and benchmark metrics. | **PASS** | None. |
| **9. Error Mitigation 1: ZNE** | *PS-Q3 Description*, p. 13; *Q3 Guide*, Sec 5 | Zero-Noise Extrapolation using unitary gate folding ($r \in \{1, 3, 5\}$) and Richardson polynomial extrapolation. | Implemented in `src/mitigation.py` (`fold_gates`, `apply_zne`, `richardson_extrapolate`). | Unit tests in `tests/test_mitigation.py` verify scale factors $\{1, 3, 5\}$ and mitigation recovery. | **PASS** | None. |
| **10. Error Mitigation 2: Readout Error Mitigation** | *PS-Q3 Description*, p. 13; *Q3 Guide*, Sec 5 | Measurement error mitigation via $2^n \times 2^n$ calibration matrix inversion and simplex probability projection. | Implemented in `src/mitigation.py` (`build_calibration_matrix`, `mitigate_readout_errors`). | Unit tests in `tests/test_mitigation.py` confirm stochasticity ($P \ge 0$, $\sum P = 1$). | **PASS** | None. |
| **11. Common Architecture Metrics** | *Universal Challenge Framework*, p. 4 | Report circuit depth, 2-qubit (CX) gate count, SWAP count overhead, active qubits, shots, execution time. | Extracted in `src/benchmarks.py` and exported to `results/tables/AB_comparison.csv`. | Unit tests verify metric extraction accuracy against transpiled circuits. | **PASS** | None. |
| **12. Problem-Specific ML Metrics** | *PS-Q3 Description*, p. 13; *Q3 Guide*, Sec 4-6 | Measure Accuracy, Precision, Recall, F1-Score, Specificity, Balanced Accuracy, Binary Cross-Entropy Loss, Confusion Matrix. | Computed in `src/benchmarks.py` using scikit-learn standard evaluation metrics. | Tests verify clinical metric calculations on held-out test split (50 samples). | **PASS** | None. |
| **13. Mitigation Resource Accounting** | *PS-Q3 Deliverables*, p. 13 | Quantify extra quantum circuit submissions, executions, and shots overhead. | Implemented in `src/benchmarks.py` and documented in `README.md`: ZNE ($3\times$ circuits), REM ($2^4=16$ calibration circuits). | Metrics captured in CSV tables and notebook outputs. | **PASS** | None. |
| **14. Phase 1 vs Phase 2 Boundary** | *QFF Participant Guidelines*, Phase 1 Deliverables | Benchmarks strictly evaluated on Processor A and Processor B. Processor C/D excluded from Phase 1 qualification. | `src/benchmarks.py`, `main.ipynb`, and `results/tables/` strictly evaluate Processors A & B. Processor C documented as Phase 2 proposal. | Audited benchmark runner ensures Processor C is not run in Phase 1 benchmark tables. | **PASS** | Keep Processor C as forward-looking Phase 2 proposal only. |
| **15. Upstream PS-Q1/PS-Q2 Dataset & Model Reuse** | *PS-Q1/Q3 Data Specification*, p. 11-13 | Reuse upstream dataset and pre-trained VQC parameter vector from team's PS-Q1 / PS-Q2 solution. | Synthetic ECG feature dataset calibrated to MIT-BIH biomarker distributions (250 samples, 4 features) with frozen random seed parameter vector (`seed=42`). Upstream artifacts missing. | Exhaustive workspace and git history audit confirmed absence of upstream PS-Q1/Q2 artifacts. | **BLOCKED** | Submit organizer clarification question; ingest upstream CSVs & weights when provided. |
| **16. Classical Baseline Comparison** | *PS-Q1/Q3 Specification*, p. 12-13; *Q3 Guide*, Sec 5 | Benchmark quantum classifier against classical baselines (Logistic Regression, Support Vector Classifier). | Implemented in `src/benchmarks.py` (`evaluate_classical_baselines`): LR (86.0% acc), SVC (88.0% acc). | Regression tests verify baseline execution on identical train/test splits. | **PASS** | None. |
| **17. Executable Jupyter Notebook (`main.ipynb`)** | *QFF Phase 1 Instructions*, Sec 7 | Self-contained, runnable notebook demonstrating end-to-end pipeline, transpilation, noise simulation, mitigation, and comparisons. | `main.ipynb` with 9 fully executed code cells and embedded matplotlib visualizations. Generated via `create_notebook.py`. | Executed headlessly via `execute_notebook.py` with exit code 0. | **PASS** | None. Run-tested and reproducible. |
| **18. AI / LLM Disclosure** | *QFF Phase 1 Instructions*, Sec 11 | Explicit disclosure of AI/LLM tooling assistance in project repository. | Dedicated AI / LLM Assistance Disclosure section included in `README.md`. | Verified in `README.md`. | **PASS** | None. |

---

## 2. Unresolved Dependency & BLOCKED Item Details

### Item 15: Upstream PS-Q1 / PS-Q2 Dataset and Trained Model Reuse
- **Status**: **BLOCKED** (Pending Hackathon Organizer Direction / Artifact Provision)
- **Problem Summary**:
  The PS-Q3 problem statement specifies evaluating error mitigation techniques on a variational classifier trained in upstream challenges (PS-Q1 / PS-Q2) on ECG heartbeat classification (MIT-BIH Arrhythmia Database).
- **Audit Findings**:
  A comprehensive inspection of the local project directory, repository git history (back to initial commit `6eed4e8`), and environment artifacts confirmed that no upstream PS-Q1 or PS-Q2 dataset files or pre-trained parameter checkpoints were distributed in the repository or starter templates.
- **Missing Upstream Artifacts**:
  1. `mitbih_train_features.csv` (Preprocessed 4-feature ECG training set)
  2. `mitbih_test_features.csv` (Preprocessed 4-feature ECG test set, 50 samples)
  3. `ps_q1_trained_vqc_weights.json` or `.npy` (Optimal variational parameter vector $\vec{\theta}^*$ for the 4-qubit ansatz)
- **Current Mitigation in Place**:
  In accordance with scientific integrity guidelines:
  1. The project uses a deterministic, reproducible synthetic ECG feature generator (`src/data_loader.py`, `seed=42`) whose marginal distributions, means, variances, and correlations match clinical MIT-BIH ECG biomarkers (QRS duration, RR interval, PR interval, ST segment deviation).
  2. The variational parameter vector $\vec{\theta}$ is frozen (`np.random.default_rng(42)`) to ensure identical model weights are evaluated across Ideal, Processor A (Noisy/Mitigated), and Processor B (Noisy/Mitigated) conditions.
  3. No synthetic data is falsely represented as real MIT-BIH recordings. The pipeline is architected for zero-code-change drop-in replacement (`load_data(filepath=...)`) once the upstream files are provided.

### Organizer Clarification Question
We have prepared the following concise, formal clarification inquiry for the Qiskit Fall Fest hackathon organizing committee:

> **Clarification Request: PS-Q3 Upstream PS-Q1/PS-Q2 Artifact Dependencies**
>
> Dear Qiskit Fall Fest Organizers,
>
> In accordance with the PS-Q3 problem statement guidelines, teams are expected to benchmark noise mitigation strategies using the pre-trained classifier and dataset from the upstream PS-Q1/PS-Q2 tasks.
>
> In our team repository and starter templates, no pre-processed MIT-BIH feature tables (`mitbih_train_features.csv`, `mitbih_test_features.csv`) or pre-trained variational parameter checkpoints ($\vec{\theta}^*$) from PS-Q1/PS-Q2 were supplied.
>
> Could you please clarify:
> 1. Will the hackathon committee provide a standardized preprocessed 4-feature test CSV and frozen parameter checkpoint for Phase 1 scoring across all PS-Q3 participants?
> 2. Alternatively, if teams enter directly at PS-Q3 without prior PS-Q1/PS-Q2 submissions, is the recommended protocol to:
>    - (a) Train a baseline VQC from raw PhysioNet MIT-BIH records using a documented 4-feature extraction pipeline, or
>    - (b) Benchmark mitigation resilience using our documented, statistically matched clinical ECG feature generator and frozen parameter vector?
>
> Our pipeline is built with modular data-loading interfaces and is prepared to ingest official upstream artifacts immediately upon provision.
>
> Thank you for your guidance.

---

## 3. Overall Readiness Summary

| Category | Total Checked | Pass | Blocked | Fail | Compliance Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Problem Scope & Hardware | 5 | 5 | 0 | 0 | 100% |
| Quantum Engine & Mitigation | 5 | 5 | 0 | 0 | 100% |
| Benchmarking & Metrics | 4 | 4 | 0 | 0 | 100% |
| Dataset & Provenance | 1 | 0 | 1 | 0 | Blocked on Upstream Artifacts |
| Reproducibility & Deliverables | 3 | 3 | 0 | 0 | 100% |
| **Total** | **18** | **17** | **1** | **0** | **94.4% (All non-blocked pass)** |

**Submission Readiness Verdict**: **READY EXCEPT FOR ORGANIZER CLARIFICATION**
