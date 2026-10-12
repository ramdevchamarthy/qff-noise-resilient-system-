# Hackathon Demonstration Script — Noise-Resilient System
## Qiskit Fall Fest 2026 | Track: QML | Problem Statement: Q3

---

### Timing & Structure (5–7 Minute Presentation)
This script provides a concise, repeatable, step-by-step demonstration for hackathon judges, technical evaluators, and reviewers.

---

### Step 1: Introduction & Problem Context (1 Minute)
* **Spoken Pitch**:
  > "Hello Judges. Welcome to our presentation on **PS-Q3: The Noise-Resilient Variational Classifier** for Qiskit Fall Fest 2026.
  > Today, variational quantum algorithms show great promise for machine learning. But in practice, there is a severe deployment gap: a quantum classifier trained on an ideal simulator loses dramatic accuracy on real NISQ hardware.
  > In clinical diagnostics—specifically automated cardiac arrhythmia detection—noise isn't just an engineering inconvenience; it's dangerous. A false negative means a patient with ventricular tachycardia goes undetected."
* **Action on Screen**:
  - Show the **Dashboard** panel. Point to the problem definition card, workflow diagram, and the official QFF 2026 Problem Statement badge (Q3).

---

### Step 2: Ingest Real Biomedical Data (1 Minute)
* **Spoken Pitch**:
  > "Rather than using synthetic toy data, we benchmark on real clinical ECG segments derived from the MIT-BIH Arrhythmia benchmark. We extract 4 diagnostic biomarkers: Heart Rate Variability (RR interval), QRS Complex Duration, R-Peak Amplitude, and ST Segment Deviation, normalized into quantum angles $[0, \pi]$."
* **Action on Screen**:
  - Switch to the **Experiment Workspace** tab.
  - Select "Patient Record #108 (Arrhythmic)" or "Patient Record #100 (Normal)".
  - Show the feature values and the interactive ECG waveform visualization.

---

### Step 3: Run the Ideal Simulator vs Physical Hardware Noise (1.5 Minutes)
* **Spoken Pitch**:
  > "First, we run the baseline VQC on the ideal statevector simulator.
  > Under zero noise, our 4-qubit SU(2) variational classifier achieves **92.5% accuracy** and **94.1% recall**.
  > Now, let's inject real hardware noise based on the organizer's calibration data for **Processor A (5-qubit Star-Linear)** and **Processor B (9-qubit Heavy-Hex)**: 0.1% single-qubit error, 0.5% two-qubit gate error, and 1.5% readout error."
* **Action on Screen**:
  - In the Experiment Workspace, set Noise Intensity to **Calibrated Device Noise** (or use the custom slider).
  - Select **Processor A**.
  - Leave Error Mitigation set to **Unmitigated Noisy**.
  - Click **'Run Experiment'**.
  - Switch to **Results Dashboard**. Show how accuracy drops to **73.3%** and Recall drops to **64.7%**. Point out the confusion matrix showing missed arrhythmic cases.

---

### Step 4: Activate Dual-Layer Quantum Error Mitigation (1.5 Minutes)
* **Spoken Pitch**:
  > "To recover clinical fidelity without requiring fault-tolerant error correction, we apply our **Dual-Layer Quantum Resilience Pipeline**:
  > 1. **Unitary Zero-Noise Extrapolation (ZNE)**: We perform pulse/gate folding with scale factors $r = 1, 3, 5$ and extrapolate using Richardson polynomial regression back to $r \to 0$.
  > 2. **Complete Readout Error Mitigation (REM)**: We invert the $16 \times 16$ empirical calibration matrix with simplex projection to remove measurement bias."
* **Action on Screen**:
  - Set Error Mitigation to **Dual-Layer (ZNE + Readout)**.
  - Click **'Run Experiment'**.
  - Show the updated **Results Dashboard**:
    - Accuracy recovers to **86.7%** (recovering +13.4% accuracy).
    - Recall recovers to **91.2%**, restoring clinical safety!
    - Point out the **Resource Accounting Table**: show the honest trade-off: $3\times$ circuit evaluations and 16 calibration basis states.

---

### Step 5: Hardware Architecture Comparison (Processor A vs Processor B) (1 Minute)
* **Spoken Pitch**:
  > "The central theme of QFF 2026 is **Algorithm ↔ Architecture Co-design**. Let's examine how physical topology alters execution."
* **Action on Screen**:
  - Open the **Architecture & Hardware Comparator** tab.
  - Show the interactive graph of **Processor A** (star-linear, hub at qubit 1) vs **Processor B** (heavy-hex, 12 edges).
  - Review the transpiled metrics table:
    - Processor A requires 4 extra SWAP gates (12 additional CX gates) to route non-adjacent interactions.
    - Processor B's heavy-hex lattice provides alternate cycles, reducing routing overhead for distributed qubits.
  - Highlight our **Phase 2 Processor C Proposal**: an 8-qubit ring-augmented architecture optimized for 4-qubit cyclic ansätze that eliminates SWAP overhead completely.

---

### Step 6: Robustness Lab Stress Test & Conclusion (1 Minute)
* **Spoken Pitch**:
  > "Finally, does this hold up across varying noise intensities?
  > In the **Robustness Lab**, we sweep two-qubit gate error rates from 0% up to 5%.
  > As you see on the live graph, the unmitigated model decays rapidly towards random guessing (50%), whereas our Dual-Mitigated classifier maintains high accuracy and recall up to 2.5% noise.
  > In conclusion: we have delivered a fully reproducible, scientifically grounded, end-to-end prototype for PS-Q3 that bridges NISQ hardware reality with clinical quantum machine learning."
* **Action on Screen**:
  - Show the live Recharts curve in **Robustness Lab**.
  - Click **'Export Benchmark CSV'**.
  - Conclude and take questions from the judges.
