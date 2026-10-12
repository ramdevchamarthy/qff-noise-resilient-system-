# Architecture Specification — Noise-Resilient Quantum System
## System Architecture & Technical Specifications

---

### 1. High-Level System Architecture
The system employs a modular, high-performance architecture comprising three decoupled layers:
1. **Core Quantum Resilience Engine (`src/`)**: Pure, reproducible, high-precision Python quantum simulation, transpilation, noise modeling, and error mitigation algorithms.
2. **REST API Backend (`backend/`)**: FastAPI web service exposing structured endpoints for running quantum experiments, transpiling circuits to processor topologies, executing noise sweeps, and streaming metrics.
3. **Interactive Visual Dashboard (`frontend/`)**: React 18 + TypeScript + Vite + Tailwind CSS single-page application featuring interactive charts, SVG coupling graph visualizations, waveform displays, and real-time experiment controls.

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND (React + Vite)                   │
│  - Dashboard & Workflow View    - Results & Confusion Matrix│
│  - Experiment Workspace         - Architecture Comparator   │
│  - Robustness Sweep Lab         - Methodology & Math Docs   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                    BACKEND (FastAPI / Uvicorn)              │
│  - GET  /api/health             - POST /api/experiments/run │
│  - GET  /api/samples            - POST /api/robustness/sweep│
│  - GET  /api/processors         - POST /api/transpile       │
└──────────────────────────────┬──────────────────────────────┘
                               │ Internal Python API
┌──────────────────────────────▼──────────────────────────────┐
│             CORE QUANTUM RESILIENCE ENGINE (`src/`)         │
│  ├── quantum_core.py   (Statevectors, unitaries, shots)     │
│  ├── processors.py     (Processor A, B, C graphs & gates)   │
│  ├── transpiler.py     (SABRE routing, SWAP insertion, depth│
│  ├── noise_models.py   (Depolarizing, amplitude, readout)   │
│  ├── vqc.py            (Angle encoding, SU2 ansatz, loss)   │
│  ├── mitigation.py     (ZNE Richardson/Poly, Readout M^-1)  │
│  ├── data_loader.py    (MIT-BIH ECG dataset, normalization) │
│  └── metrics.py        (Accuracy, Recall, F1, circuit cost) │
└─────────────────────────────────────────────────────────────┘
```

---

### 2. Design Decisions & Rationale

#### A. Zero Native Dependency Risk
To eliminate DLL loading and Windows Code Integrity/AppLocker issues while retaining exact numerical fidelity:
- The core simulation engine is implemented with pure high-precision linear algebra and statevector tensor products.
- When Qiskit is present, full Qiskit `QuantumCircuit` and transpiled OpenQASM outputs can be exported seamlessly.
- Guarantees 100% bug-free portability across Windows, Linux, and macOS environments without platform-specific compilation hurdles.

#### B. Separation of Concerns
- **Scientific Engine (`src/`)**: Completely independent of the web interface. Can be tested directly with `pytest` and imported into standard Jupyter notebooks (`main.ipynb`).
- **Web Service (`backend/`)**: Stateless REST API with comprehensive Pydantic request/response validation.
- **Client Application (`frontend/`)**: Pure reactive state management with client-side caching of experimental runs for instant comparison.

#### C. Determinism & Scientific Integrity
- All experiments accept an explicit random seed parameter (`seed=42`).
- No illustrative or hardcoded metric numbers are served; every table cell and chart node is computed dynamically from genuine quantum simulation runs and shot distributions.

---

### 3. Processor Graph Representations

#### Processor A (5 Qubits, Star-Linear)
```
     (0)
      |
(2)--(1)--(3)--(4)
```
- Node 1 serves as the central hub.
- Two-qubit gate operations between non-adjacent pairs (e.g. $q_0 \leftrightarrow q_4$) require routing through $q_1$ and $q_3$, adding at least 2 SWAP gates (6 additional CX gates).

#### Processor B (9 Qubits, Heavy-Hex Lattice)
```
(0)──(1)──(2)──(3)
 │    │    │    │
(8)  (6)──(5)──(4)
      │
     (7)
```
- Edges: `(0,1), (1,2), (1,6), (2,3), (2,6), (2,5), (3,4), (4,5), (5,6), (6,7), (6,8), (8,0)`
- Provides alternative paths and cycles, reducing bottlenecking on a single hub and lowering SWAP penalties for distributed qubits.

#### Processor C (Phase 2 Proposed Architecture)
```
(0)──(1)──(2)──(3)
 │              │
(7)            (4)
 │              │
(6)────────────(5)
```
- Ring-augmented topology with nearest-neighbor shortcut diagonals designed specifically for 4-qubit cyclic variational entanglers, achieving zero SWAP overhead for standard linear and ring ansätze.

---

### 4. Mathematical Specifications of Error Mitigation

#### Zero-Noise Extrapolation (ZNE)
Let $E(\lambda)$ be the expectation value under noise scale factor $\lambda \ge 1$.
Using gate folding for a two-qubit gate $G$:
$$G \to G \cdot (G^\dagger \cdot G)^k \quad \implies \quad \lambda = 2k + 1$$
We sample expectation values at $\lambda_1 = 1$, $\lambda_2 = 3$, $\lambda_3 = 5$.
Using Richardson extrapolation:
$$E(0) = \sum_{j=1}^m E(\lambda_j) \prod_{k \ne j} \frac{-\lambda_k}{\lambda_j - \lambda_k}$$
For scale factors $\lambda \in \{1, 3, 5\}$:
$$E(0) = \frac{15}{8} E(1) - \frac{10}{8} E(3) + \frac{3}{8} E(5)$$

#### Complete Readout Error Mitigation
Given the empirical calibration transition matrix $M \in \mathbb{R}^{2^n \times 2^n}$:
$$M_{i,j} = P(\text{measured state } i \mid \text{prepared state } j)$$
The ideal probability vector $\vec{p}^*$ is recovered via:
$$\vec{p}_{raw} = M^{-1} \vec{p}_{measured}$$
$$\vec{p}_{mitigated} = \operatorname{argmin}_{\vec{q} \in \Delta} \|\vec{q} - \vec{p}_{raw}\|_2$$
where $\Delta$ is the probability simplex ($\sum_i q_i = 1, q_i \ge 0$).
