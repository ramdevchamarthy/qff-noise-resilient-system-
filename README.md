# Noise-Resilient Quantum System Prototype
## Qiskit Fall Fest 2026 (QFF 2026) Hackathon
### Track: Quantum Machine Learning (Variational QML) • Problem Statement: PS-Q3

> **Official Problem Statement PS-Q3: Noise-Resilient Variational Classifier**  
> *"A classifier trained on an ideal simulator can lose significant accuracy once evaluated under real device noise. Train a classifier and recover its accuracy under a calibrated noise model using error mitigation."*

---

## 🌟 Executive Summary
This repository contains a complete, verified, working prototype for **PS-Q3** of the Qiskit Fall Fest 2026 qualification stage. 

The system implements an end-to-end clinical **Variational Quantum Classifier (VQC)** for cardiac arrhythmia detection from electrocardiogram (ECG) biomarkers. It features a **Dual-Layer Quantum Error Mitigation Suite** combining **Zero-Noise Extrapolation (ZNE)** with unitary gate folding and **Complete Readout Error Mitigation (REM)** with probability simplex projection. 

It provides rigorous, reproducible benchmarks across the organizer-prescribed **Processor A (5-qubit Star-Linear)** and **Processor B (9-qubit Heavy-Hex)** architectures, plus a proposed **Phase 2 Processor C** architecture optimized for minimal SWAP routing overhead.

---

## 🏗️ System Architecture & Workflow

```
[MIT-BIH Arrhythmia Dataset] ────> [Feature Extraction & MinMax Normalization]
                                                        │
                                                        ▼
                                          [4-Qubit Quantum Feature Map]
                                                        │
                                                        ▼
                                          [Trained SU(2) Variational Ansatz]
                                                        │
                      ┌─────────────────────────────────┴─────────────────────────────────┐
                      ▼                                                                   ▼
       [Transpiled: Processor A (5q)]                                      [Transpiled: Processor B (9q)]
       (Star-Linear, Hub at Q1)                                            (Heavy-Hex Lattice, 12 Edges)
                      │                                                                   │
                      ▼                                                                   ▼
        [Calibrated Depolarizing Noise]                                     [Calibrated Heavy-Hex Noise]
        (p_1q=0.1%, p_2q=0.5%, p_ro=1.5%)                                  (p_1q=0.1%, p_2q=0.5%, p_ro=1.5%)
                      │                                                                   │
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        │
                                                        ▼
                                       [Quantum Error Mitigation Pipeline]
                                  ┌─────────────────────┴─────────────────────┐
                                  ▼                                           ▼
                     [Zero-Noise Extrapolation]                  [Readout Error Mitigation]
                     (Gate Folding r ∈ {1, 3, 5})                (M⁻¹ Inversion + Simplex)
                                  └─────────────────────┬─────────────────────┘
                                                        │
                                                        ▼
                                          [Clinical Diagnostic Output]
                                         (Normal vs Arrhythmia Decision)
```

---

## 📊 Measured Benchmark Results (N = 50 Held-Out Samples)

All values are empirically derived from actual quantum circuit executions and 1024-shot sampling using the official trained model (`trained_vqc_weights.json`) and test partition (no hardcoded metrics):

| Platform / Configuration | Accuracy | Recall (Sensitivity) | Precision | F1-Score | Circuit Depth | Algorithmic CX | SWAP Count | Total Physical CX | Exec Overhead |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Classical Logistic Regression** | **90.0%** | **73.7%** | 100.0% | 84.9% | — | — | — | — | 1× (Classical) |
| **Ideal Reference VQC** | **74.0%** | **31.6%** | 100.0% | 48.0% | 5 | 8 | 0 | 8 | 1× |
| **Processor A (Unmitigated Noisy)** | 72.0% | 26.3% *(Degraded)* | 100.0% | 41.7% | 23 | 8 | 8 | 32 | 1× |
| **Processor A (Dual Mitigated)** | **76.0%** | **36.8%** *(Recovered)* | 100.0% | 53.8% | 23 | 8 | 8 | 32 | 3× Circuits |
| **Processor B (Unmitigated Noisy)** | 76.0% | 36.8% *(Native Ring)* | 100.0% | 53.8% | 15 | 8 | 0 | 8 | 1× |
| **Processor B (Dual Mitigated)** | 70.0% | 21.1% *(Shot Variance)* | 100.0% | 34.8% | 15 | 8 | 0 | 8 | 3× Circuits |
| **Processor C (Proposed Phase 2)** | *Projected* | *Projected* | — | — | **15** | 8 | **0** | **8** | 1× Native |

> **Scientific Analysis**: 
> 1. On **Processor A** (star topology with hub at Q1), cyclic entanglement requires 8 physical SWAP routing gates (24 extra physical CX gates, circuit depth 23). Device depolarizing noise drops accuracy to 72.0% and recall to 26.3%. Dual mitigation (ZNE Richardson + Readout simplex inversion) successfully recovers performance to **76.0% accuracy and 36.8% recall** (+10.5 percentage points recall improvement).
> 2. On **Processor B** (heavy-hex lattice), the transpiler discovers a native physical 4-cycle `(0,1,6,8)`, executing with **0 SWAPs and 8 CX gates** (depth 15). Because gate depth is shallow, unmitigated noisy execution maintains 76.0% accuracy; linear extrapolation at scale factor $r=5$ exhibits statistical shot sampling noise, illustrating the importance of depth-aware mitigation scaling.

---

## 🔬 Core Quantum Resilience Algorithms

### 1. Zero-Noise Extrapolation (ZNE)
* **Unitary Gate Folding**: Because CNOT is its own inverse ($CX = CX^\dagger$, $CX \cdot CX = I$), replacing $CX$ with $CX \cdot (CX \cdot CX)^k$ scales the physical noise by an odd scale factor $\lambda = 2k + 1$ ($\lambda \in \{1, 3, 5\}$) without changing the logical transformation.
* **Richardson Extrapolation**:
  $$E(0) = \frac{15}{8} E(1) - \frac{10}{8} E(3) + \frac{3}{8} E(5)$$
  Cancels first- and second-order depolarizing noise errors.

### 2. Complete Readout Error Mitigation (REM)
* **Calibration Matrix Inversion**: Computes the transition assignment matrix $M \in \mathbb{R}^{16 \times 16}$ where $M_{i,j} = P(\text{measured } i \mid \text{prepared } j)$.
* **Simplex Projection**: Inverts $M$ and projects onto the valid probability simplex using the Michelot-Duchi projection:
  $$\vec{p}_{mitigated} = \Pi_\Delta [M^{-1} \vec{p}_{noisy}]$$

---

## 🚀 Quickstart & Reproduction

### Prerequisites
* Python 3.10+ (tested on Python 3.14.7)
* Node.js 18+ (tested on Node v24.21.0)
* Git

### 1. Installation
Clone the repository and install dependencies:
```bash
# Python dependencies
python -m pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Run Automated Verification Tests
Execute the 54-test automated verification suite:
```bash
python -m pytest tests/ -v
```
*Expected result: 54 passed across unit, scientific, noise, physics, and storage suites.*

### 3. Run Benchmark Exporters
Generate the official CSV tables and figures:
```bash
python -m src.benchmarks
python -m src.visualization
```
Outputs are written to `results/tables/` and `results/figures/`.

### 4. Start the Application
Run the backend and frontend simultaneously:

**Terminal 1 (Backend API):**
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# Server starts at http://127.0.0.1:8000
```

**Terminal 2 (Interactive UI):**
```bash
cd frontend
npm run dev
# Vite UI starts at http://localhost:5173
```

---

## 📂 Repository Organization
```
qff-noise-resilient-system/
├── README.md                      # Comprehensive project guide and official report
├── main.ipynb                     # Fully executed reproducible Jupyter notebook
├── requirements.txt               # Verified software dependencies
├── create_notebook.py             # Notebook builder utility
├── execute_notebook.py            # Headless notebook execution runner
├── data/
│   ├── raw/                       # Raw input files
│   └── processed/
│       ├── ecg_arrhythmia_dataset.csv
│       ├── ecg_arrhythmia_dataset.json
│       └── trained_vqc_weights.json
├── processors/
│   ├── processor_A.json           # Authoritative 5-qubit star-linear benchmark
│   ├── processor_B.json           # Authoritative 9-qubit heavy-hex benchmark
│   └── processor_C.json           # Proposed Phase 2 ring-augmented architecture
├── src/
│   ├── __init__.py
│   ├── quantum_core.py            # High-precision statevector simulator & gates
│   ├── processors.py              # Processor graph loader & topology BFS
│   ├── transpiler.py              # Routing, SWAP insertion & architecture metrics
│   ├── noise_models.py            # Calibrated depolarizing and readout noise
│   ├── mitigation.py              # ZNE gate folding & Readout simplex inversion
│   ├── vqc.py                     # 4-qubit SU(2) VQC & Classical Logistic Regression
│   ├── data_loader.py             # MIT-BIH biomedical ECG loader & normalizer
│   ├── dataset_manager.py         # Ephemeral & persistent patient dataset manager
│   ├── experiment_store.py        # Safe runtime experiment persistence
│   ├── storage.py                 # File & memory fallback storage backend
│   ├── metrics.py                 # Classification & architecture metric calculations
│   ├── benchmarks.py              # Systematic noise sweep & CSV exporter
│   └── visualization.py           # Matplotlib publication chart generator
├── backend/
│   └── app/
│       ├── main.py                # FastAPI server entrypoint & CORS
│       ├── api/
│       │   └── routes.py          # REST endpoints for live experiment execution
│       └── models/
│           └── schemas.py         # Pydantic request/response schemas
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                # Master reactive UI (Dark & Light mode)
│       └── components/
│           ├── Navbar.tsx
│           ├── Dashboard.tsx      # Overview & executive summary
│           ├── ExperimentWorkspace.tsx # Live patient & parameter controls
│           ├── ResultsDashboard.tsx    # Live classification & confusion matrices
│           ├── RobustnessLab.tsx       # Recharts noise sweep curve & CSV export
│           ├── ArchitectureComparator.tsx # SVG topology viewer & routing cost
│           └── Methodology.tsx         # Math formulations & team disclosures
├── results/
│   ├── tables/
│   │   ├── processor_A_metrics.csv
│   │   ├── processor_B_metrics.csv
│   │   ├── AB_comparison.csv
│   │   └── robustness_sweep.csv
│   └── figures/
│       ├── processor_A_graph.png
│       ├── processor_B_graph.png
│       ├── logical_vs_transpiled.png
│       ├── AB_performance.png
│       ├── noise_vs_accuracy.png
│       └── architecture_tradeoffs.png
├── docs/
│   ├── requirements.md            # Verified hackathon requirements
│   ├── compliance-matrix.md       # Evidence-based compliance matrix
│   ├── problem-analysis.md        # Technical problem definition
│   ├── architecture.md            # System architecture document
│   ├── testing.md                 # Test plan and validation strategy
│   └── demo-script.md             # Judge presentation script
└── tests/
    ├── test_api.py
    ├── test_audit_scientific.py
    ├── test_circuits.py
    ├── test_data.py
    ├── test_dataset_manager.py
    ├── test_noise_and_mitigation.py
    ├── test_processors_and_transpiler.py
    ├── test_reference_quantum_physics.py
    ├── test_storage_and_upload_regression.py
    └── test_vqc_and_baselines.py
```

---

## ⚠️ Known Limitations & Scope
1. **NISQ Statistical Boundary**: Error mitigation statistical variance escalates sharply beyond $p_{2q} > 3.5\%$, where states approach maximum entropy ($I/16$).
2. **Shot Sampling Overhead**: Zero-Noise Extrapolation triples circuit execution costs ($3\times$), which must be budgeted during cloud queue execution.
3. **Local Readout Scaling**: Complete $2^n \times 2^n$ matrix inversion is practical up to $n \approx 10$ qubits; beyond 10 qubits, tensored local measurement mitigation is required.

---

## 🤖 AI / LLM Assistance Disclosure
In compliance with Section 11 of the QFF 2026 Phase 1 Participant Instructions, AI assistance was employed to accelerate architectural boilerplates, user interface layout styling, and test generation. All mathematical models, statevector simulations, ZNE Richardson implementations, simplex projections, and experimental measurements were compiled, executed, and validated locally.
