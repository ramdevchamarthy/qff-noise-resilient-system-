# Qiskit Fall Fest 2026 (QFF 2026) — Verified Requirements Document
## Track: Quantum Machine Learning (Variational QML)
## Problem Statement Code: Q3 — Noise-Resilient Variational Classifier

---

### 1. Executive Summary & Challenge Context
The **Qiskit Fall Fest 2026 (QFF 2026) Hackathon** is organized around the theme **"Algorithm ↔ Architecture Co-Design"**. In Phase 1 (Online Qualification Stage, Oct 8–13, 2026), teams must select exactly one problem statement, implement the quantum/quantum-safe solution, execute and benchmark it across two organizer-defined fixed quantum hardware architectures (**Processor A** and **Processor B**), and analyze how physical processor architecture (coupling topology, SWAP overhead, circuit depth, noise characteristics) affects algorithmic execution.

Our selected problem statement is **Q3: Noise-Resilient Variational Classifier** from the **Quantum Machine Learning Track (Variational QML)**.

---

### 2. Official Problem Statement Definition (PS-Q3)
* **Title**: Noise-Resilient Variational Classifier
* **Problem**: A classifier trained on an ideal simulator can lose significant accuracy once evaluated under real device noise. Train a classifier and recover its accuracy under a calibrated noise model using error mitigation.
* **Motivation**: This addresses the critical practical gap between NISQ-era (Noisy Intermediate-Scale Quantum) QML theoretical research and realistic hardware deployment.
* **Baseline Task**:
  1. Train a Variational Quantum Classifier (VQC) on an ideal reference statevector simulator.
  2. Evaluate the same trained model under realistic calibrated device noise models derived from hardware calibration data on **Processor A** (5-qubit online benchmark) and **Processor B** (9-qubit heavy-hex online benchmark).
  3. Apply at least two quantum error mitigation techniques (Zero-Noise Extrapolation [ZNE] and Readout Error Mitigation / Measurement Error Correction).
  4. Compare performance against classical baselines (Logistic Regression and Support Vector Machines).
  5. Formulate a Phase 2 **Processor C** proposal aimed at improving noise resilience (e.g. shallower ansatz, reduced two-qubit gate overhead, tailored coupling graph).
* **Deliverables**:
  - Reproducible codebase and Jupyter notebook (`main.ipynb` / Python scripts).
  - Organizer-specified `processors/` definition files (`processor_A.json`, `processor_B.json`, `processor_C.json`).
  - Quantitative benchmark results (`results/tables/`) and visualizations (`results/figures/`).
  - Full technical report and documentation.
  - Interactive demonstration application for judges.

---

### 3. Architecture & Processor Specifications (Source of Truth)

#### Processor A (Fixed 5-Qubit Online Benchmark)
* **Qubits**: 5 qubits ($q_0, q_1, q_2, q_3, q_4$)
* **Coupling Edges**: `(0,1), (1,2), (1,3), (3,4)`
* **Topology**: Star-linear hybrid topology centered at qubit 1.
* **Basis Gates**: `["rz", "sx", "x", "cx"]`
* **Calibrated Noise Parameters**:
  - Single-qubit depolarizing gate error: $p_{1q} \approx 0.1\%$ ($0.001$)
  - Two-qubit CNOT depolarizing gate error: $p_{2q} \approx 0.5\%$ ($0.005$)
  - Readout error rate: $p_{ro} \approx 1.5\%$ ($P(0|1)=0.015, P(1|0)=0.015$)

#### Processor B (Fixed 9-Qubit Heavy-Hex Benchmark)
* **Qubits**: 9 qubits ($q_0, \dots, q_8$)
* **Coupling Edges**: `(0,1), (1,2), (1,6), (2,3), (2,6), (2,5), (3,4), (4,5), (5,6), (6,7), (6,8), (8,0)`
* **Topology**: IBM Heavy-Hex inspired unit-cell layout with vertex and bridge qubits designed to suppress crosstalk.
* **Basis Gates**: `["rz", "sx", "x", "cx"]`
* **Calibrated Noise Parameters**:
  - Single-qubit depolarizing gate error: $p_{1q} \approx 0.1\%$ ($0.001$)
  - Two-qubit CNOT depolarizing gate error: $p_{2q} \approx 0.5\%$ ($0.005$)
  - Readout error rate: $p_{ro} \approx 1.5\%$ ($P(0|1)=0.015, P(1|0)=0.015$)

#### Processor C (Phase 2 Roadmap Continuation)
* **Qubits**: 8–10 qubits
* **Topology**: Geometric all-to-nearest ring / triangle-augmented lattice tailored to minimize SWAP routing overhead for variational ansätze.

---

### 4. Mandatory Features & Functional Requirements
1. **End-to-End Quantum Machine Learning Pipeline**:
   - Feature preprocessing, normalization to $[0, \pi]$.
   - Quantum feature map encoding (4-qubit Angle Encoding / ZZ Feature Map).
   - Parameterized ansatz with single-qubit rotations ($RY(\theta)$) and entangling CX layers.
   - Classification decision boundary via expectation value $\langle Z_0 \rangle$ or measurement parity.
2. **Error Mitigation Suite (At Least Two Techniques)**:
   - **Technique 1: Zero-Noise Extrapolation (ZNE)**: Unitary gate folding ($CX \to CX \cdot CX^\dagger \cdot CX$) at scale factors $r \in [1, 3, 5]$, followed by polynomial / Richardson extrapolation to the zero-noise limit ($r \to 0$).
   - **Technique 2: Readout Error Mitigation**: Measurement calibration matrix $M$ inversion with probability simplex projection: $\vec{p}_{mitigated} = M^{-1} \vec{p}_{noisy}$.
3. **Controlled Architecture Benchmark (A vs B)**:
   - Transpilation with routing and SWAP gate insertion.
   - Circuit metrics: Transpiled Depth, 2-qubit (CX) Gate Count, SWAP Count, Physical Qubit Allocation.
   - Performance metrics: Classification Accuracy, Recall, Precision, F1-Score, Loss.
4. **Hardware Robustness Lab**:
   - Parameterized noise sweep over $p_{2q} \in [0.00, 0.05]$ to measure error degradation and mitigation recovery thresholds.
   - Variance quantification across repeated shots and seeds.
5. **Interactive Full-Stack Web Application**:
   - Polished dark-mode UI (Charcoal/Navy + Cyan/Blue accents).
   - Real-time simulation, file upload, chart rendering, confusion matrix, and architecture visualization.
   - Zero mock data in final experiment views.

---

### 5. Technical Constraints & Verification Rules
* **No invented requirements**: Grounded strictly in QFF 2026 Executive Summary, Universal Challenge Framework, and Q3 Prototype Guide.
* **Reproducibility**: Clean installation via `requirements.txt`, deterministic random seeds, exported CSV tables.
* **Separation of Common Benchmark & Optional Studies**: Common benchmark strictly adheres to organizer definitions.
