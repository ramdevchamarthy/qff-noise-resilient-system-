# Verification & Testing Strategy — Noise-Resilient System

---

### 1. Test Suite Architecture
The test suite is structured into multi-tiered validation layers under `tests/`:

1. **`test_data.py`**:
   - Validates data loading from CSV/JSON.
   - Tests sample counts, feature dimensionality ($4$ clinical features), label distribution (Normal: $0$, Arrhythmia: $1$).
   - Tests normalization to $[0, \pi]$ range.
   - Tests handling of corrupted, empty, or out-of-range inputs.

2. **`test_circuits.py`**:
   - Tests 4-qubit statevector initialization.
   - Tests gate operations: $H$, $X$, $Y$, $Z$, $RX(\theta)$, $RY(\theta)$, $RZ(\theta)$, $CX$, $SWAP$.
   - Validates statevector normalization ($\sum |\psi_i|^2 = 1.0$).
   - Validates expected analytical Bell state output: $|\Phi^+\rangle = \frac{|00\rangle + |11\rangle}{\sqrt{2}}$.

3. **`test_processors_and_transpiler.py`**:
   - Loads and parses `processor_A.json`, `processor_B.json`, and `processor_C.json`.
   - Checks node counts (5 for A, 9 for B, 8 for C) and coupling adjacency lists.
   - Tests topological distance calculation via shortest path (BFS / Dijkstra).
   - Validates transpilation of non-adjacent 2-qubit gates into routed circuits with explicit SWAP insertion.
   - Verifies that on Processor A, gate $(0, 4)$ requires at least 2 SWAPs ($6$ CX gates).

4. **`test_noise_and_mitigation.py`**:
   - Tests depolarizing noise channel application.
   - Tests readout confusion matrix construction and asymmetric flip probabilities.
   - Validates Zero-Noise Extrapolation (ZNE) gate folding: ensures folded sequence $U (U^\dagger U)^k$ is logically equivalent to $U$ under zero noise.
   - Tests Richardson extrapolation mathematical convergence back to uncorrupted expectation values.
   - Tests Complete Readout Error Mitigation ($M^{-1}$) matrix inversion and simplex projection.

5. **`test_vqc_and_baselines.py`**:
   - Validates VQC training loop and parameter convergence.
   - Validates classical Logistic Regression baseline training and inference.
   - Confirms that error mitigation improves noisy VQC classification accuracy and recall.

6. **`test_api.py`**:
   - Uses FastAPI `TestClient` to test all REST endpoints:
     - `GET /api/health`
     - `GET /api/samples`
     - `GET /api/processors`
     - `POST /api/experiments/run`
     - `POST /api/robustness/sweep`
     - `POST /api/transpile`
   - Validates JSON payload schemas and HTTP 200 responses.

---

### 2. Execution Instructions
To run the automated test suite locally:
```bash
python -m pytest tests/ -v
```
All tests execute deterministically with fixed random seeds.
