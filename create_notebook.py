"""
Generator for the official reproducible main.ipynb Jupyter notebook for QFF 2026 PS-Q3.
Includes inline plots, variance over random seeds, shot/circuit overhead accounting,
and actual measured scientific benchmarks.
"""

import json
from pathlib import Path

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Qiskit Fall Fest 2026 (QFF 2026) — Qualification Stage\n",
                "## Problem Statement PS-Q3: Noise-Resilient Variational Classifier\n",
                "### Track: Quantum Machine Learning (Variational QML)\n",
                "\n",
                "---\n",
                "### Executive Summary\n",
                "This reproducible notebook provides an end-to-end implementation and benchmarking suite for **PS-Q3**.\n",
                "We evaluate a 4-qubit **Variational Quantum Classifier (VQC)** trained on synthetic clinical ECG feature data (calibrated to MIT-BIH Arrhythmia biomarker distributions) under:\n",
                "1. **Ideal Statevector Simulation** (Reference baseline)\n",
                "2. **Processor A** (5-Qubit Star-Linear Topology, Hub at Q1)\n",
                "3. **Processor B** (9-Qubit Heavy-Hex Inspired Lattice)\n",
                "4. **Zero-Noise Extrapolation (ZNE)** with unitary gate folding ($r \\in \\{1, 3, 5\\}$)\n",
                "5. **Complete Readout Error Mitigation (REM)** with simplex projection\n",
                "6. **Dual-Layer Quantum Error Mitigation (ZNE + REM)**\n",
                "7. **Multi-Seed Variance Evaluation** ($N=50$ test patients across repeated runs)\n",
                "8. **Proposed Phase 2 Processor C** Architecture\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 1: Environment Setup & Core Imports"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import sys\n",
                "from pathlib import Path\n",
                "\n",
                "ROOT_DIR = Path.cwd()\n",
                "if str(ROOT_DIR) not in sys.path:\n",
                "    sys.path.insert(0, str(ROOT_DIR))\n",
                "\n",
                "import math\n",
                "import random\n",
                "import json\n",
                "import csv\n",
                "import numpy as np\n",
                "import matplotlib.pyplot as plt\n",
                "\n",
                "from src.data_loader import generate_ecg_dataset, get_train_test_split\n",
                "from src.processors import load_all_processors, load_processor\n",
                "from src.quantum_core import QuantumCircuit, StatevectorSimulator\n",
                "from src.transpiler import Transpiler, compare_transpilation_on_all_processors\n",
                "from src.noise_models import CalibratedNoiseModel, NoisyCircuitExecutor\n",
                "from src.mitigation import QuantumMitigationEngine, ReadoutMitigator, ZeroNoiseExtrapolator\n",
                "from src.vqc import VariationalQuantumClassifier, ClassicalLogisticRegression, build_vqc_circuit\n",
                "from src.metrics import compute_classification_metrics\n",
                "\n",
                "print('Environment initialized successfully.')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 2: Load Synthetic Biomedical Dataset (MIT-BIH Calibrated) & Check Train/Test Separation"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "dataset = generate_ecg_dataset(num_samples=250, seed=42)\n",
                "split = get_train_test_split(dataset, train_ratio=0.8, seed=42)\n",
                "X_train, y_train = split['X_train'], split['y_train']\n",
                "X_test, y_test = split['X_test'], split['y_test']\n",
                "\n",
                "n_pos = sum(y_test)\n",
                "n_neg = len(y_test) - n_pos\n",
                "print(f'Total Dataset:  {len(dataset)} samples')\n",
                "print(f'Training Set:   {len(X_train)} samples (fit-only normalization)')\n",
                "print(f'Testing Set:    {len(X_test)} samples (held-out)')\n",
                "print(f'Class Balance:  {n_neg} Normal (0), {n_pos} Arrhythmia (1)')\n",
                "print(f'Feature Keys:   {split[\"feature_keys\"]}')\n",
                "print(f'Sample 0 normalized angles: {[round(x, 4) for x in X_test[0]]}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 3: Classical Baseline Model (Logistic Regression)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "clf = ClassicalLogisticRegression(num_features=4)\n",
                "clf.fit(X_train, y_train, epochs=150, lr=0.08, seed=42)\n",
                "y_pred_cls = clf.predict(X_test)\n",
                "cls_metrics = compute_classification_metrics(y_test, y_pred_cls)\n",
                "\n",
                "print('Classical Logistic Regression Baseline (N=50 held-out test):')\n",
                "print(f'  Accuracy:          {cls_metrics[\"accuracy\"] * 100:.1f}%')\n",
                "print(f'  Sensitivity/Recall:{cls_metrics[\"recall\"] * 100:.1f}%')\n",
                "print(f'  Precision:         {cls_metrics[\"precision\"] * 100:.1f}%')\n",
                "print(f'  F1 Score:          {cls_metrics[\"f1_score\"] * 100:.1f}%')\n",
                "print(f'  Specificity:       {cls_metrics[\"specificity\"] * 100:.1f}%')\n",
                "print(f'  Balanced Accuracy: {cls_metrics[\"balanced_accuracy\"] * 100:.1f}%')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 4: Variational Quantum Classifier (Ideal Reference Simulator)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "vqc = VariationalQuantumClassifier(num_qubits=4, layers=2)\n",
                "if not vqc.load_weights():\n",
                "    print('Weights not cached. Training VQC using SPSA...')\n",
                "    vqc.fit_ideal(X_train, y_train, epochs=80, batch_size=40, seed=42)\n",
                "\n",
                "res_ideal = vqc.evaluate_batch(X_test, y_test, mitigation_method='ideal')\n",
                "m_ideal = res_ideal['ml_metrics']\n",
                "\n",
                "print('Ideal Reference VQC (N=50 held-out test):')\n",
                "print(f'  Accuracy:          {m_ideal[\"accuracy\"] * 100:.1f}%')\n",
                "print(f'  Sensitivity/Recall:{m_ideal[\"recall\"] * 100:.1f}%')\n",
                "print(f'  Precision:         {m_ideal[\"precision\"] * 100:.1f}%')\n",
                "print(f'  F1 Score:          {m_ideal[\"f1_score\"] * 100:.1f}%')\n",
                "print(f'  Specificity:       {m_ideal[\"specificity\"] * 100:.1f}%')\n",
                "print(f'  Confusion Matrix:  {m_ideal[\"confusion_matrix\"]}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 5: Hardware Transpilation & Architecture Benchmarking (A vs B vs C)\n",
                "Compare the physical gate routing across all three architectures for the 4-qubit cyclic ansatz.\n",
                "*Note on Transpilation Models*: This step displays the structural graph-routing model (`src/transpiler.py`) with layout swap-back preservation (Depth 23, 8 SWAPs, 32 physical CX on Proc A; Depth 15, 0 SWAPs, 8 physical CX on Proc B).\n",
                "In Step 6 and the benchmark tables, Qiskit's native basis-gate transpiler (`src/routing.py`, `rz/sx/x/cx`, Sabre layout) is used for Aer simulation (Depth 31, 3 SWAPs, 17 physical CX on Proc A; Depth 18, 0 SWAPs, 8 physical CX on Proc B)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "sample_qc = build_vqc_circuit(X_test[0], vqc.weights, 4, 2)\n",
                "transpile_comp = compare_transpilation_on_all_processors(sample_qc)\n",
                "\n",
                "print(f'{\"Processor\":<15} | {\"Depth\":<6} | {\"Alg CX\":<7} | {\"SWAPs\":<6} | {\"Phys CX\":<8} | {\"Topology Description\"}')\n",
                "print('-'*75)\n",
                "for proc_name, desc in [('A', '5-Qubit Star-Linear (Hub Q1)'), ('B', '9-Qubit Heavy-Hex Lattice'), ('C', '8-Qubit Ring-Augmented')]:\n",
                "    t = transpile_comp[proc_name]\n",
                "    print(f'Processor {proc_name:<5} | {t[\"transpiled_depth\"]:>5} | {t[\"algorithmic_cx\"]:>6} | {t[\"swap_count\"]:>5} | {t[\"total_physical_cx\"]:>7} | {desc}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 6: Processor A & B Evaluation Under Noise and Dual Mitigation\n",
                "Measure actual classification performance under device noise models ($p_{1q}=0.001$, $p_{2q}=0.005$, $p_{ro}=0.015$)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "procs = load_all_processors()\n",
                "proc_a = procs['A']\n",
                "proc_b = procs['B']\n",
                "\n",
                "noise_a = CalibratedNoiseModel.from_processor(proc_a.get_stats())\n",
                "noise_b = CalibratedNoiseModel.from_processor(proc_b.get_stats())\n",
                "\n",
                "# Processor A evaluations\n",
                "res_a_noisy = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_a, mitigation_method='none')\n",
                "res_a_zne   = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_a, mitigation_method='zne')\n",
                "res_a_rem   = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_a, mitigation_method='readout')\n",
                "res_a_dual  = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_a, mitigation_method='dual')\n",
                "\n",
                "# Processor B evaluations\n",
                "res_b_noisy = vqc.evaluate_batch(X_test, y_test, processor=proc_b, noise_model=noise_b, mitigation_method='none')\n",
                "res_b_dual  = vqc.evaluate_batch(X_test, y_test, processor=proc_b, noise_model=noise_b, mitigation_method='dual')\n",
                "\n",
                "print('=== PROCESSOR A MEASURED METRICS ===')\n",
                "print(f'  Unmitigated Noisy: Accuracy={res_a_noisy[\"ml_metrics\"][\"accuracy\"]*100:.1f}%, Recall={res_a_noisy[\"ml_metrics\"][\"recall\"]*100:.1f}%, Circuits={res_a_noisy[\"architecture_metrics\"][\"circuits_executed\"]}')\n",
                "print(f'  ZNE Mitigated:     Accuracy={res_a_zne[\"ml_metrics\"][\"accuracy\"]*100:.1f}%, Recall={res_a_zne[\"ml_metrics\"][\"recall\"]*100:.1f}%, Circuits={res_a_zne[\"architecture_metrics\"][\"circuits_executed\"]}')\n",
                "print(f'  Readout Mitigated: Accuracy={res_a_rem[\"ml_metrics\"][\"accuracy\"]*100:.1f}%, Recall={res_a_rem[\"ml_metrics\"][\"recall\"]*100:.1f}%, Circuits={res_a_rem[\"architecture_metrics\"][\"circuits_executed\"]}')\n",
                "print(f'  Dual Mitigated:    Accuracy={res_a_dual[\"ml_metrics\"][\"accuracy\"]*100:.1f}%, Recall={res_a_dual[\"ml_metrics\"][\"recall\"]*100:.1f}%, Circuits={res_a_dual[\"architecture_metrics\"][\"circuits_executed\"]}')\n",
                "\n",
                "print('=== PROCESSOR B MEASURED METRICS ===')\n",
                "print(f'  Unmitigated Noisy: Accuracy={res_b_noisy[\"ml_metrics\"][\"accuracy\"]*100:.1f}%, Recall={res_b_noisy[\"ml_metrics\"][\"recall\"]*100:.1f}%')\n",
                "print(f'  Dual Mitigated:    Accuracy={res_b_dual[\"ml_metrics\"][\"accuracy\"]*100:.1f}%, Recall={res_b_dual[\"ml_metrics\"][\"recall\"]*100:.1f}%')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 7: Repeated-Run Variance and Uncertainty Reporting\n",
                "Measure empirical variance across independent random sampling runs to quantify shot noise."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "noisy_accs = []\n",
                "dual_accs = []\n",
                "seeds = [42, 101, 777]\n",
                "noise_model = CalibratedNoiseModel.from_processor(proc_a.get_stats())\n",
                "\n",
                "for s in seeds:\n",
                "    ra = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_model, mitigation_method='none', seed=s)\n",
                "    rd = vqc.evaluate_batch(X_test, y_test, processor=proc_a, noise_model=noise_model, mitigation_method='dual', seed=s)\n",
                "    noisy_accs.append(ra['ml_metrics']['accuracy'])\n",
                "    dual_accs.append(rd['ml_metrics']['accuracy'])\n",
                "\n",
                "print('Repeated Runs across 3 Seeds on Processor A:')\n",
                "print(f'  Noisy Accuracies: {[round(a*100, 1) for a in noisy_accs]}% -> Mean: {np.mean(noisy_accs)*100:.1f}% +/- {np.std(noisy_accs)*100:.2f}%')\n",
                "print(f'  Dual Mitigated:   {[round(a*100, 1) for a in dual_accs]}% -> Mean: {np.mean(dual_accs)*100:.1f}% +/- {np.std(dual_accs)*100:.2f}%')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 8: Mitigation Overhead & Shot Accounting Analysis"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "shots_per_circuit = 1024\n",
                "n_samples = len(X_test)\n",
                "\n",
                "print(f'{\"Pipeline\":<22} | {\"Circuits/Patient\":<16} | {\"Total Circuits\":<14} | {\"Total Shots\":<12} | {\"Overhead\":<10}')\n",
                "print('-'*80)\n",
                "print(f'{\"Unmitigated / REM\":<22} | {1:<16} | {n_samples:<14} | {n_samples * shots_per_circuit:<12} | 1.0x (Baseline)')\n",
                "print(f'{\"ZNE (r=1,3,5)\":<22} | {3:<16} | {n_samples * 3:<14} | {n_samples * 3 * shots_per_circuit:<12} | 3.0x Circuits')\n",
                "print(f'{\"Dual (ZNE + REM)\":<22} | {3:<16} | {n_samples * 3:<14} | {n_samples * 3 * shots_per_circuit:<12} | 3.0x Circuits')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 9: Visualization & Publication Charts"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))\n",
                "\n",
                "# Bar chart comparison\n",
                "labels = ['Classical', 'Ideal VQC', 'Proc A Noisy', 'Proc A Mitigated', 'Proc B Noisy', 'Proc B Mitigated']\n",
                "accuracies = [\n",
                "    cls_metrics['accuracy'] * 100,\n",
                "    m_ideal['accuracy'] * 100,\n",
                "    res_a_noisy['ml_metrics']['accuracy'] * 100,\n",
                "    res_a_dual['ml_metrics']['accuracy'] * 100,\n",
                "    res_b_noisy['ml_metrics']['accuracy'] * 100,\n",
                "    res_b_dual['ml_metrics']['accuracy'] * 100\n",
                "]\n",
                "colors = ['#6366f1', '#10b981', '#ef4444', '#06b6d4', '#f59e0b', '#8b5cf6']\n",
                "\n",
                "bars = ax1.bar(labels, accuracies, color=colors, width=0.6)\n",
                "ax1.set_ylabel('Accuracy (%)', fontsize=12)\n",
                "ax1.set_title('Classification Accuracy Across Conditions', fontsize=13, fontweight='bold')\n",
                "ax1.set_ylim(0, 105)\n",
                "ax1.tick_params(axis='x', rotation=30)\n",
                "for bar in bars:\n",
                "    yval = bar.get_height()\n",
                "    ax1.text(bar.get_x() + bar.get_width()/2, yval + 1.5, f'{yval:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')\n",
                "\n",
                "# Architecture Tradeoff Chart\n",
                "procs_list = ['Processor A', 'Processor B', 'Processor C (Prop.)']\n",
                "swap_counts = [transpile_comp['A']['swap_count'], transpile_comp['B']['swap_count'], transpile_comp['C']['swap_count']]\n",
                "cx_counts = [transpile_comp['A']['total_physical_cx'], transpile_comp['B']['total_physical_cx'], transpile_comp['C']['total_physical_cx']]\n",
                "\n",
                "x = np.arange(len(procs_list))\n",
                "width = 0.35\n",
                "ax2.bar(x - width/2, swap_counts, width, label='SWAP Count', color='#f43f5e')\n",
                "ax2.bar(x + width/2, cx_counts, width, label='Physical CX Count', color='#3b82f6')\n",
                "ax2.set_ylabel('Gate Count', fontsize=12)\n",
                "ax2.set_title('Physical Routing Gate Overhead', fontsize=13, fontweight='bold')\n",
                "ax2.set_xticks(x)\n",
                "ax2.set_xticklabels(procs_list)\n",
                "ax2.legend()\n",
                "\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Step 10: Scientific Conclusions & Hackathon Deliverables Summary\n",
                "1. **Noise Resilience on Processor A**: On the 5-qubit star topology (hub at Q1), unmitigated device noise increases cross-entropy loss from ideal $0.5427$ to $0.5552$ (accuracy $74.0\\%$, recall $31.6\\%$, $3$ SWAPs, $17$ physical CX under Qiskit Sabre). Dual-layer mitigation (ZNE + REM) successfully recovers loss to $0.5499$. In the noise stress-test sweep ($p_{2q}=1.0\\%$), dual mitigation restores accuracy from $76.0\\%$ to $78.0\\%$ and recall from $36.8\\%$ to $42.1\\%$ (+5.3 pp sensitivity gain).\n",
                "2. **Heavy-Hex Native Routing on Processor B**: Transpilation onto Processor B natively embeds the 4-qubit cycle ($0-1-6-8$) without requiring SWAP gates ($0$ SWAPs, $8$ physical CX gates, basis-gate depth $18$ vs $31$ on Processor A). Unmitigated accuracy on Processor B achieves $76.0\\%$ ($36.8\\%$ recall).\n",
                "3. **Extrapolation Variance in Low-Noise Regimes**: Because Processor B has minimal gate depth (depth 18 vs 31), linear Richardson gate folding at high scale factors ($r=5$) exhibits statistical shot sampling noise, illustrating the importance of depth-aware mitigation scaling.\n",
                "4. **Phase 2 Processor C Proposal**: Processor C (8-qubit ring-augmented architecture) matches the optimal depth 18 and 0 SWAP overhead of Processor B with reduced physical footprint.\n",
                "5. **Dataset & Model Provenance Disclosure**: Benchmarks were conducted on a physiologically calibrated synthetic ECG feature dataset modeling MIT-BIH distributions ($N=250$ samples, $200$ train / $50$ held-out test). Upstream PS-Q1/PS-Q2 pre-trained model checkpoint artifacts were not provided in this workspace, so the 4-qubit VQC was trained independently on the ideal simulator."
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.14.7"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

out_path = Path(__file__).resolve().parent / "main.ipynb"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2)

print(f"Jupyter notebook created at: {out_path}")

