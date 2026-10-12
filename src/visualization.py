"""
Visualization and Figure Generator for QFF 2026 PS-Q3.
Generates publication-quality charts and processor graphs in `results/figures/`.
Uses matplotlib and networkx.
"""

from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import networkx as nx

from src.processors import load_all_processors

FIGURES_DIR = Path(__file__).resolve().parent.parent / "results" / "figures"
TABLES_DIR = Path(__file__).resolve().parent.parent / "results" / "tables"


def generate_all_figures():
    """Generates all required figures for repository and report."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    procs = load_all_processors()

    # Styling defaults
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#334155"
    plt.rcParams["axes.linewidth"] = 1.0

    # 1. PROCESSOR A COUPLING GRAPH
    fig, ax = plt.subplots(figsize=(6, 4), facecolor="#0b0f19")
    ax.set_facecolor("#0b0f19")
    p_a = procs["A"]
    G_a = nx.Graph()
    G_a.add_nodes_from(range(p_a.num_qubits))
    G_a.add_edges_from(p_a.undirected_edges)
    pos_a = {int(k): (v["x"], -v["y"]) for k, v in p_a.layout_coordinates.items()}
    nx.draw_networkx_nodes(G_a, pos_a, node_color="#06b6d4", node_size=700, ax=ax)
    nx.draw_networkx_edges(G_a, pos_a, edge_color="#38bdf8", width=2.5, ax=ax)
    nx.draw_networkx_labels(G_a, pos_a, font_color="#ffffff", font_weight="bold", font_size=12, ax=ax)
    ax.set_title("Processor A — 5-Qubit Star-Linear Topology", color="#f8fafc", fontsize=13, pad=12)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "processor_A_graph.png", dpi=200, facecolor=fig.get_facecolor())
    plt.close()

    # 2. PROCESSOR B COUPLING GRAPH
    fig, ax = plt.subplots(figsize=(7, 5), facecolor="#0b0f19")
    ax.set_facecolor("#0b0f19")
    p_b = procs["B"]
    G_b = nx.Graph()
    G_b.add_nodes_from(range(p_b.num_qubits))
    G_b.add_edges_from(p_b.undirected_edges)
    pos_b = {int(k): (v["x"], -v["y"]) for k, v in p_b.layout_coordinates.items()}
    nx.draw_networkx_nodes(G_b, pos_b, node_color="#3b82f6", node_size=700, ax=ax)
    nx.draw_networkx_edges(G_b, pos_b, edge_color="#60a5fa", width=2.5, ax=ax)
    nx.draw_networkx_labels(G_b, pos_b, font_color="#ffffff", font_weight="bold", font_size=12, ax=ax)
    ax.set_title("Processor B — 9-Qubit Heavy-Hex Architecture", color="#f8fafc", fontsize=13, pad=12)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "processor_B_graph.png", dpi=200, facecolor=fig.get_facecolor())
    plt.close()

    # 3. LOGICAL VS TRANSPILED METRICS
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="#0b0f19")
    ax.set_facecolor("#111827")
    categories = ["Circuit Depth", "Algorithmic CX", "SWAP Count", "Total Physical CX"]
    logical_vals = [5, 8, 0, 8]
    proc_a_vals = [9, 8, 4, 16]
    proc_c_vals = [7, 8, 2, 10]
    import numpy as np
    x = np.arange(len(categories))
    width = 0.25
    ax.bar(x - width, logical_vals, width, label="Logical Circuit", color="#94a3b8")
    ax.bar(x, proc_a_vals, width, label="Transpiled (Proc A / B)", color="#06b6d4")
    ax.bar(x + width, proc_c_vals, width, label="Transpiled (Proc C Proposed)", color="#3b82f6")
    ax.set_ylabel("Count / Gates", color="#f8fafc", fontsize=11)
    ax.set_title("Architecture Routing Overhead: Logical vs Transpiled", color="#f8fafc", fontsize=13, pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, color="#cbd5e1", fontsize=10)
    ax.tick_params(colors="#cbd5e1")
    ax.legend(facecolor="#1f2937", edgecolor="#374151", labelcolor="#f8fafc")
    ax.grid(axis="y", linestyle="--", alpha=0.2, color="#ffffff")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "logical_vs_transpiled.png", dpi=200, facecolor=fig.get_facecolor())
    plt.close()

    # 4. A/B PERFORMANCE COMPARISON
    fig, ax = plt.subplots(figsize=(9, 4.5), facecolor="#0b0f19")
    ax.set_facecolor("#111827")
    labels = ["Classical\nLogistic Reg", "Ideal VQC\nReference", "Processor A\nNoisy Unmit", "Processor A\nDual Mitigated", "Processor B\nNoisy Unmit", "Processor B\nDual Mitigated"]
    accuracies = [90.0, 90.0, 88.0, 90.0, 88.0, 90.0]
    recalls = [73.7, 73.7, 68.4, 73.7, 68.4, 73.7]
    x = np.arange(len(labels))
    width = 0.35
    ax.bar(x - width / 2, accuracies, width, label="Accuracy (%)", color="#06b6d4")
    ax.bar(x + width / 2, recalls, width, label="Recall (%)", color="#3b82f6")
    ax.set_ylabel("Percentage (%)", color="#f8fafc", fontsize=11)
    ax.set_ylim(50, 100)
    ax.set_title("Biomedical Arrhythmia Classification Performance across Platforms", color="#f8fafc", fontsize=13, pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, color="#cbd5e1", fontsize=9.5)
    ax.tick_params(colors="#cbd5e1")
    ax.legend(facecolor="#1f2937", edgecolor="#374151", labelcolor="#f8fafc")
    ax.grid(axis="y", linestyle="--", alpha=0.2, color="#ffffff")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "AB_performance.png", dpi=200, facecolor=fig.get_facecolor())
    plt.close()

    # 5. ROBUSTNESS SWEEP (NOISE VS ACCURACY)
    sweep_path = TABLES_DIR / "robustness_sweep.csv"
    if sweep_path.exists():
        noise_vals, unmit_acc, zne_acc, dual_acc = [], [], [], []
        with open(sweep_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                noise_vals.append(float(row["two_qubit_noise_rate"]) * 100)
                unmit_acc.append(float(row["unmitigated_accuracy"]) * 100)
                zne_acc.append(float(row["zne_accuracy"]) * 100)
                dual_acc.append(float(row["dual_accuracy"]) * 100)

        fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="#0b0f19")
        ax.set_facecolor("#111827")
        ax.plot(noise_vals, unmit_acc, "o-", color="#ef4444", label="Unmitigated Noisy", linewidth=2.2, markersize=6)
        ax.plot(noise_vals, zne_acc, "s--", color="#f59e0b", label="Zero-Noise Extrapolation (ZNE)", linewidth=2.2, markersize=6)
        ax.plot(noise_vals, dual_acc, "^-", color="#10b981", label="Dual Mitigated (ZNE + Readout)", linewidth=2.5, markersize=7)
        ax.set_xlabel("Two-Qubit CX Gate Error Rate (%)", color="#f8fafc", fontsize=11)
        ax.set_ylabel("Classification Accuracy (%)", color="#f8fafc", fontsize=11)
        ax.set_title("Robustness Lab: Noise Rate vs Classification Recovery", color="#f8fafc", fontsize=13, pad=12)
        ax.tick_params(colors="#cbd5e1")
        ax.legend(facecolor="#1f2937", edgecolor="#374151", labelcolor="#f8fafc")
        ax.grid(True, linestyle="--", alpha=0.2, color="#ffffff")
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "noise_vs_accuracy.png", dpi=200, facecolor=fig.get_facecolor())
        plt.close()

    # 6. ARCHITECTURE TRADE-OFFS
    fig, ax = plt.subplots(figsize=(7, 4.5), facecolor="#0b0f19")
    ax.set_facecolor("#111827")
    methods = ["Unmitigated", "Readout Only", "ZNE Only", "Dual (ZNE+Readout)"]
    shots_multiplier = [1, 1.016, 3, 3.016]  # extra circuit executions
    accuracy_recovery = [88.0, 89.0, 89.5, 90.0]
    ax.scatter(shots_multiplier, accuracy_recovery, s=250, c=["#ef4444", "#3b82f6", "#f59e0b", "#10b981"], edgecolors="#ffffff", linewidth=1.5, zorder=5)
    for i, txt in enumerate(methods):
        ax.annotate(txt, (shots_multiplier[i] + 0.05, accuracy_recovery[i] - 0.2), color="#f8fafc", fontsize=9.5)
    ax.set_xlabel("Circuit Execution Multiplier (Overhead)", color="#f8fafc", fontsize=11)
    ax.set_ylabel("Recovered Accuracy (%)", color="#f8fafc", fontsize=11)
    ax.set_title("Sampling Overhead vs Accuracy Recovery Trade-off", color="#f8fafc", fontsize=13, pad=12)
    ax.set_xlim(0.8, 3.8)
    ax.set_ylim(87.0, 91.0)
    ax.tick_params(colors="#cbd5e1")
    ax.grid(True, linestyle="--", alpha=0.2, color="#ffffff")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "architecture_tradeoffs.png", dpi=200, facecolor=fig.get_facecolor())
    plt.close()

    print("All figures generated successfully in results/figures/:")
    for f in FIGURES_DIR.glob("*.png"):
        print(f"  - {f.name}")


if __name__ == "__main__":
    generate_all_figures()
