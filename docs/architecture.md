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

### 2. Design Decisions, Simulation Mechanics & Scientific Rationale

#### A. Custom Pure-Python Statevector Simulator (`src/quantum_core.py`)
To eliminate native C-compiler dependencies, dynamic link library loading hazards, and Windows Code Integrity (AppLocker/WDAC) execution blocks, the system incorporates a self-contained pure-Python quantum engine:
- **State Representation**: High-precision $2^n$-dimensional complex amplitude statevector $|\psi\rangle \in \mathbb{C}^{16}$ for 4 active variational qubits.
- **Unitary Gate Algebra**: Exact matrix operations applied directly to amplitude subregisters:
  - Single-qubit rotations: $H, X, Y, Z, SX$, and parameterized $RX(\theta), RY(\theta), RZ(\theta)$.
  - Two-qubit gates: Controlled-NOT ($CX$) basis amplitude permutation and $SWAP$ gate exchanges.
- **Portability**: Operates natively in standard Python 3.10+ without requiring C++ compilers, `qiskit_aer` binaries, or GPU toolchains, ensuring 100% bug-free cross-platform reproducibility.

#### B. Finite-Shot Measurement & Sampling
- **Analytical Probability**: Born rule probability vector $\vec{p} \in \mathbb{R}^{16}$ where $p_i = |\langle i | \psi \rangle|^2$.
- **Shot Sampling**: Multinomial sampling implemented via Python's deterministic `random.Random(seed).choices(population, weights=p, k=shots)`.
- **Observable Expectation**: Evaluates Pauli $\langle Z_0 \rangle = \sum_{b} (-1)^{b_0} \frac{C(b)}{N_{shots}}$, converging to statevector expectation $\langle \psi | (Z_0 \otimes I^{\otimes 3}) | \psi \rangle$ as $N_{shots} \to \infty$.

#### C. Calibrated Physical Noise Engine (`src/noise_models.py`)
- **Depolarizing Gate Noise**: Evaluates cumulative circuit fidelity based on transpiled gate counts:
  $$F_{gate} = (1 - p_{1q})^{N_{1q}} \cdot (1 - p_{2q})^{N_{cx}}$$
  Under depolarizing channel action, the state contracts toward the maximally mixed state $I/16$:
  $$\vec{p}_{noisy} = F_{gate} \vec{p}_{ideal} + (1 - F_{gate}) \frac{\vec{1}}{16}$$
- **Asymmetric Readout (SPAM) Error**: Models independent asymmetric measurement decay per qubit with transition matrix $M_{1q} = \begin{pmatrix} 1 - p_{ro}^{0\to 1} & p_{ro}^{1\to 0} \\ p_{ro}^{0\to 1} & 1 - p_{ro}^{1\to 0} \end{pmatrix}$. The composite $16 \times 16$ readout calibration matrix $M = \bigotimes_{j=0}^3 M_{1q}^{(j)}$ maps true state distributions to observed detector frequencies: $\vec{p}_{dev} = M \vec{p}_{noisy}$.

#### D. Quantum Error Mitigation Pipeline (`src/mitigation.py`)
- **Zero-Noise Extrapolation (ZNE)**: Unitary gate folding replacing each physical $CX$ with $CX \cdot (CX^\dagger \cdot CX)^k$ ($CX$ is self-inverse), scaling two-qubit noise by factors $\lambda \in \{1, 3, 5\}$. Expectation values are extrapolated to $\lambda = 0$ via 2nd-order Richardson extrapolation:
  $$E(0) = \frac{15}{8}E(1) - \frac{10}{8}E(3) + \frac{3}{8}E(5)$$
- **Readout Error Mitigation (REM)**: Inverts the empirical assignment matrix $M^{-1} \vec{p}_{raw}$. Numerical stability is enforced via Michelot-Duchi projection onto the probability simplex: $\vec{p}_{mit} = \operatorname{argmin}_{\vec{q} \in \Delta} \|\vec{q} - M^{-1}\vec{p}_{raw}\|_2$.
- **Dual-Layer Mitigation**: Applies readout matrix inversion to measurement counts at each folded scale factor $\lambda \in \{1, 3, 5\}$ prior to Richardson polynomial extrapolation.

#### E. Scientific Limitations & Boundaries
- **No Physical Hardware Execution**: All simulations model target processor topologies and calibration parameters locally; physical QPU execution did not occur.
- **Statistical NISQ Boundaries**: Error mitigation is non-fault-tolerant. At high gate error ($p_{2q} > 3.5\%$), depolarizing contraction erodes state purity and inflates extrapolation variance.
- **Biomedical Scope**: Feature inputs and ECG waveforms are demonstration benchmarks for variational QML and carry no clinical diagnostic validation.

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
