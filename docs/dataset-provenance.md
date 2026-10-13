# Dataset and Model Provenance Report
## Problem Statement: PS-Q3 — Noise-Resilient Variational Classifier
**Project**: Q-ResQ  
**Hackathon**: Qiskit Fall Fest 2026

---

## 1. Executive Summary

This document provides a transparent, rigorous provenance record for the dataset and variational quantum classifier (VQC) model evaluated in the Q-ResQ Phase 1 submission.

- **Current Evaluation Dataset**: Statistically calibrated synthetic ECG feature dataset (`src/data_loader.py`) modeling 4 clinical biomarkers from the MIT-BIH Arrhythmia Database.
- **Current Model Parameters**: Deterministic frozen parameter vector ($\vec{\theta} \in \mathbb{R}^{12}$, `seed=42`) evaluated under identical conditions across Ideal, Processor A (Noisy/Mitigated), and Processor B (Noisy/Mitigated).
- **Compliance Status**: **BLOCKED** on upstream artifact provision (PS-Q1/PS-Q2 upstream outputs were not distributed in team workspace or repository).
- **Integrity Guarantee**: In strict accordance with hackathon ethics, **synthetic data is explicitly disclosed** and never falsely presented as real PhysioNet WFDB records.

---

## 2. Exhaustive Search for Upstream Artifacts

A systematic audit was conducted across the local workspace, environment paths, and Git history back to the initial commit (`6eed4e8`):
1. **Workspace Root & Subdirectories**: Searched for `.csv`, `.h5`, `.npy`, `.pkl`, `.pt`, `.json` data files.
2. **Git Commit History**: Inspected all file trees and deleted commits.
3. **Artifact Result**: No upstream files from PS-Q1 or PS-Q2 (`mitbih_train_features.csv`, `mitbih_test_features.csv`, pre-trained model weights) were present in the repository or starter materials.

---

## 3. Current Implementation Details

### 3.1 Feature Space & Clinical Grounding
The 4 features extracted/generated model key electrophysiological indicators used for arrhythmia classification:
1. **Feature 0 (QRS Duration)**: Normal ventricular depolarization typically spans 80–120 ms; widened QRS (>120 ms) indicates bundle branch block or ventricular ectopic beats.
2. **Feature 1 (RR Interval)**: Interval between successive R-peaks, measuring heart rate and rhythm variability.
3. **Feature 2 (PR Interval)**: Atrioventricular conduction time, normally 120–200 ms.
4. **Feature 3 (ST Segment Deviation)**: Elevation or depression indicating myocardial ischemia or injury.

### 3.2 Statistical Parameter Matching
In `src/data_loader.py`, the synthetic generator is parameterized as follows:
- **Sample Count**: $N=250$ total (200 training samples, 50 test samples).
- **Class Balance**: 50% Normal Sinus Rhythm (Class 0), 50% Arrhythmic/Ectopic (Class 1).
- **Feature Normalization**: Min-Max scaled to $[0, \pi]$ for angle encoding via $R_y$ gates on 4 qubits.
- **Reproducibility**: Controlled via fixed seed (`seed=42`).

### 3.3 Variational Model Parameters
- **Architecture**: 4 qubits, 2 variational layers ($R_y$ and $R_z$ rotations) with full circular entangling $CX$ gates.
- **Parameter Count**: $4 \times 3 = 12$ variational parameters.
- **Freezing**: Parameters are initialized with fixed seed (`seed=42`) and held strictly constant across all noisy and mitigated benchmark evaluations to isolate the pure effect of hardware noise and error mitigation.

---

## 4. Missing Upstream Artifacts Specification

The following artifacts would be required for strict upstream PS-Q1/PS-Q2 reuse:
1. `mitbih_train_features.csv`: 4-column feature matrix with binary classification labels (200+ samples).
2. `mitbih_test_features.csv`: 4-column feature matrix with binary classification labels (50 test samples).
3. `ps_q1_model_weights.json` (or `.npy`): 12-element trained parameter vector $\vec{\theta}^*$.

---

## 5. Drop-in Replacement Architecture

The codebase has been designed with clean dependency injection so that when the official files are supplied, no pipeline refactoring is required:
```python
from src.data_loader import load_data

# Currently loads calibrated synthetic dataset:
X_train, X_test, y_train, y_test = load_data()

# Drop-in loading of upstream CSV when provided:
# X_train, X_test, y_train, y_test = load_data(filepath="data/mitbih_test_features.csv")
```

---

## 6. Formal Organizer Clarification Question

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
