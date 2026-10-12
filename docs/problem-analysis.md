# Problem Analysis — PS-Q3: Noise-Resilient Variational Classifier
## Domain: Quantum Machine Learning (QML) & NISQ Biomedical Diagnostic Systems

---

### 1. The Core Engineering Problem
Variational Quantum Classifiers (VQCs) represent one of the flagship applications of Near-Term Intermediate-Scale Quantum (NISQ) computing. In theory, quantum feature maps embed classical data into exponentially large Hilbert spaces, allowing linear hyperplanes in quantum state space to separate non-linearly separable patterns.

However, a fundamental disconnect exists between algorithmic design and real-world deployment:
* **The Noise Degradation Gap**: A VQC trained on an ideal (statevector) simulator suffers severe degradation when executed on physical quantum processors.
* **Entanglement Vulnerability**: Multi-qubit entangling gates ($CX$) are orders of magnitude noisier than single-qubit gates (typical two-qubit gate error rates are $0.5\% - 2.0\%$ vs $0.05\% - 0.1\%$ for single-qubit gates).
* **Routing Overhead (SWAP Explosion)**: Real quantum processors have constrained coupling topologies. Mapping an all-to-all or linear ansatz onto sparse graphs (such as IBM's Heavy-Hex lattice or star-graphs) forces the transpiler to insert $SWAP$ gates. Because each $SWAP = 3 \times CX$, routing triples the hardware noise exposure.
* **Measurement Readout Noise**: Physical state readout suffers from thermal relaxation and measurement apparatus misclassification (typically $1.0\% - 3.0\%$ flip probability), destroying expectation values and corrupting decision boundaries.

In clinical diagnostics (such as cardiac arrhythmia screening from electrocardiogram [ECG] waveforms), this noise causes fatal false-negative classifications, drastically dropping diagnostic **Recall**.

---

### 2. Who Experiences It?
1. **Clinical Diagnostic Teams & Medical Device Engineers**: Clinical screening systems require high sensitivity (recall $\ge 90\%$). Hardware noise corrupts classification thresholds, misdiagnosing high-risk arrhythmic patients as normal.
2. **QML Researchers & Hardware Developers**: Teams attempting to demonstrate quantum utility on physical quantum processing units (QPUs) find their algorithms dominated by decoherence and gate infidelities.
3. **Quantum Cloud Practitioners**: Developers migrating algorithms between different cloud topologies (e.g. 5-qubit linear-star vs 9-qubit heavy-hex) experience unexplained performance divergence due to unquantified SWAP overhead.

---

### 3. Why Conventional Approaches Fail
* **Naive Re-training under Noise**: Training noisy circuits directly in the loop is sample-inefficient, computationally intractable on cloud queues, and often succumbs to noise-induced barren plateaus where cost gradients vanish exponentially.
* **Full Fault-Tolerant Quantum Error Correction (QEC)**: Surface codes require thousands of physical qubits per logical qubit and fault-tolerant thresholds not attainable in the NISQ era.
* **Classical Heuristic Filtering**: Post-hoc classical smoothing cannot unentangle the non-unitary phase damping and depolarizing transitions that occurred during circuit depth execution.

---

### 4. Proposed Solution & Architecture
We propose a **Dual-Layer Geometry-Aware Quantum Error Mitigation System** integrated into an end-to-end VQC:
1. **Layer 1: Unitary Zero-Noise Extrapolation (ZNE)**:
   - Systematically amplify coherent and incoherent noise without altering the logical unitary by replacing two-qubit gates $U$ with folded sequences: $U \to U (U^\dagger U)^n$ for noise scale factors $r \in \{1, 3, 5\}$.
   - Fit expectation values across noise scale factors to a Richardson or second-order polynomial model and extrapolate backwards to the zero-noise limit ($r \to 0$).
2. **Layer 2: Complete Readout Error Mitigation (REM)**:
   - Construct a pre-calibrated $2^n \times 2^n$ transition assignment matrix $M$, where $M_{i,j} = P(\text{measured } i \mid \text{prepared } j)$.
   - Invert the assignment matrix and apply probability simplex projection: $\vec{p}_{mitigated} = \Pi_{\Delta} [M^{-1} \vec{p}_{noisy}]$.
3. **Geometry-Aware Transpilation Optimization**:
   - Transpile specifically to the target coupling graph (**Processor A** vs **Processor B**), analyzing the exact SWAP insertion penalty and depth scaling.

---

### 5. Technical Approach & Workflow
```
[Raw ECG Biomedical Signal]
         ↓
[Feature Extraction & Preprocessing (HRV, QRS, R-Peak, ST)]
         ↓
[Quantum Feature Map (Angle / ZZ Encoding into 4 Qubits)]
         ↓
[Trained Parameterized Variational Ansatz (SU2 + CX)]
         ↓
┌───────────────────────┴───────────────────────┐
↓                                               ↓
[Transpiled onto Processor A]       [Transpiled onto Processor B]
(5-Qubit Star-Linear Topology)      (9-Qubit Heavy-Hex Lattice)
         ↓                                       ↓
[Calibrated Depolarizing Noise]     [Calibrated Heavy-Hex Noise]
         ↓                                       ↓
┌───────────────────────┬───────────────────────┐
↓                       ↓                       ↓
[Unmitigated Noisy]    [ZNE Mitigated]     [Dual-Mitigated (ZNE + REM)]
         ↓                       ↓                       ↓
[Expectation & Probabilities Reconstruction with Simplex Projection]
         ↓
[Clinical Decision Boundary: Normal (0) vs Arrhythmia (1)]
         ↓
[Benchmarking: Accuracy, Recall, F1, CX Count, SWAP Count, Latency]
```

---

### 6. Expected Measurable Benefits
1. **Accuracy & Recall Recovery**: Under $0.5\%$ gate depolarizing error and $1.5\%$ readout error, unmitigated VQC accuracy drops by $15\% - 25\%$. The dual-mitigated pipeline recovers $70\% - 85\%$ of the ideal simulator accuracy.
2. **Clinical Reliability**: Restores Arrhythmia detection recall from $\approx 65\%$ back to $\ge 88\%$, preventing missed cardiac events.
3. **Transparent Overhead Accounting**: Explicitly measures the trade-off: ZNE requires $3\times$ circuit evaluations and REM requires $2^n$ calibration shots, fully tracked in the resource table.
4. **Architectural Insight**: Reveals why Processor A (linear-star) requires 4 additional SWAP gates compared to Processor B's heavy-hex routing when executing 4-qubit cyclic entanglers.

---

### 7. Limitations & Honest Scope
* **Not Fault-Tolerant**: Error mitigation does not correct individual quantum errors in real-time; it statistically infers the ideal expectation value from noisy ensembles.
* **Sampling Overhead / Variance Escalation**: ZNE extrapolation increases the statistical variance $\sigma^2$ of expectation values, requiring higher shot counts ($N \ge 1024$) to suppress shot noise.
* **High Noise Breakdown**: Beyond $p_{2q} > 0.04$ (4% gate error), the expectation value approaches the maximally mixed state ($I/2^n$), causing exponential loss of signal-to-noise ratio.
* **Scalability of Readout Matrix**: Full $2^n \times 2^n$ matrix inversion scales exponentially with $n$; for $n > 10$, tensored local readout mitigation is required.

---

### 8. Live Demonstration Scenario
1. **Baseline Ingestion**: Load a real patient ECG signal segment from the MIT-BIH dataset. Show the clean 4-feature extraction.
2. **Ideal Reference Execution**: Run the VQC on the ideal simulator (yielding $92\%$ accuracy, $94\%$ recall).
3. **Hardware Noise Injection**: Inject Processor A's calibrated noise model. Observe the degradation: accuracy falls to $74\%$, recall drops to $68\%$, misclassifying abnormal heartbeats.
4. **Resilience Activation**: Enable Readout Mitigation and ZNE. Watch the decision boundary shift, restoring accuracy to $87\%$ and recall to $91\%$.
5. **A vs B Hardware Comparison**: Toggle from Processor A to Processor B. Inspect the heavy-hex coupling diagram, routing paths, SWAP counts, and circuit depth differences.
6. **Robustness Stress Test**: Run the Robustness Lab noise sweep from $0\%$ to $5\%$ error rate, observing the exact curve where unmitigated collapses while resilient maintains stability.
