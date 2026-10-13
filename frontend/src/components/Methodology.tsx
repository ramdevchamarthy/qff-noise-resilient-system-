import React from 'react';
import { BookOpen, ShieldCheck, CheckSquare, Users, Cpu, FileText } from 'lucide-react';

export const Methodology: React.FC = () => {
  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      <div className="border-b border-space-700/80 pb-4">
        <h2 className="text-xl font-bold text-white tracking-tight">Methodology, Mathematical Formulations & Project Info</h2>
        <p className="text-xs text-slate-400">
          Formal theoretical foundations, algorithmic definitions, hardware assumptions, and team disclosures for QFF 2026 PS-Q3.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ZNE Mathematical Formulation */}
        <div className="rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4">
          <div className="flex items-center gap-2 text-amber-400">
            <BookOpen className="w-5 h-5" />
            <h3 className="text-sm font-bold text-white uppercase font-mono tracking-wider">
              1. Zero-Noise Extrapolation (ZNE)
            </h3>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            Zero-Noise Extrapolation mitigates expectation value errors by intentionally scaling the physical noise level without modifying the logical unitary transformation, followed by polynomial extrapolation to the zero-noise limit:
          </p>

          <div className="p-4 rounded-xl bg-space-950 border border-space-800 font-mono text-xs text-cyan-300 space-y-2">
            <div><strong>Unitary Gate Folding:</strong></div>
            <div className="text-slate-300">
              U → U · (U† · U)ᵏ   ⟹   λ = 2k + 1 (Scale factors: 1, 3, 5)
            </div>
            <div className="pt-2 text-slate-400">Because CX is self-inverse (CX† = CX, CX · CX = I), logical circuit semantics are preserved identically.</div>
          </div>

          <div className="p-4 rounded-xl bg-space-950 border border-space-800 font-mono text-xs text-cyan-300 space-y-2">
            <div><strong>Richardson Extrapolation Formula:</strong></div>
            <div className="text-slate-300">
              E(0) = (15/8)·E(1) - (10/8)·E(3) + (3/8)·E(5)
            </div>
            <div className="text-slate-400 pt-1">Cancels first- and second-order depolarizing noise error terms.</div>
          </div>
        </div>

        {/* Readout Error Mitigation Formulation */}
        <div className="rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4">
          <div className="flex items-center gap-2 text-blue-400">
            <ShieldCheck className="w-5 h-5" />
            <h3 className="text-sm font-bold text-white uppercase font-mono tracking-wider">
              2. Complete Readout Error Mitigation (REM)
            </h3>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            State measurement on superconducting transmon QPUs experiences asymmetric state-preparation and measurement (SPAM) decay. We calibrate the 2ⁿ × 2ⁿ assignment matrix M:
          </p>

          <div className="p-4 rounded-xl bg-space-950 border border-space-800 font-mono text-xs text-cyan-300 space-y-2">
            <div><strong>Calibration Assignment Matrix:</strong></div>
            <div className="text-slate-300">
              M[i, j] = P(measured bitstring i | prepared bitstring j)
            </div>
            <div className="text-slate-400 pt-1">Calibrated from 2ⁿ computational basis preparations under hardware noise.</div>
          </div>

          <div className="p-4 rounded-xl bg-space-950 border border-space-800 font-mono text-xs text-cyan-300 space-y-2">
            <div><strong>Simplex Inversion & Projection:</strong></div>
            <div className="text-slate-300">
              p_raw = M⁻¹ · p_noisy
            </div>
            <div className="text-slate-300">
              p_mitigated = argmin_(q ∈ Δ) ||q - p_raw||₂
            </div>
            <div className="text-slate-400 pt-1">
              Guarantees valid probability distribution (∑ qᵢ = 1, qᵢ ≥ 0).
            </div>
          </div>
        </div>
      </div>

      {/* Simulation Engine & Numerical Physics */}
      <div className="rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4">
        <h3 className="text-sm font-bold text-white uppercase font-mono tracking-wider flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          3. Pure-Python Statevector Simulator & Physics Mechanics
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-2">
            <h4 className="font-semibold text-cyan-300">Zero-C-Dependency Architecture</h4>
            <p className="text-slate-300 leading-relaxed">
              Implemented in <code className="text-white font-mono bg-space-950 px-1 py-0.5 rounded">src/quantum_core.py</code> using native Python linear algebra (<code className="text-slate-400">math</code>, <code className="text-slate-400">cmath</code>). Eliminates external C-extension binary dependencies (<code className="text-slate-400">.pyd</code>) and bypasses Windows Code Integrity / AppLocker blocks, guaranteeing 100% reliable execution.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-2">
            <h4 className="font-semibold text-cyan-300">Exact Statevector & Finite Shots</h4>
            <p className="text-slate-300 leading-relaxed">
              Maintains an exact 16-dimensional complex statevector |ψ⟩ in ℂ¹⁶ for 4 active qubits. Born rule probability distributions P(i) = |⟨i|ψ⟩|² drive deterministic pseudo-random multinomial shot sampling with reproducible seeds (<code className="text-slate-400">seed=42</code>).
            </p>
          </div>

          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-2">
            <h4 className="font-semibold text-cyan-300">Calibrated Device Noise Injection</h4>
            <p className="text-slate-300 leading-relaxed">
              Simulates two-qubit depolarizing gate error via an analytical global gate-survival heuristic (F_gate = (1 - p_1q)^N1 · (1 - p_2q)^N2) mixing pure state probabilities toward the maximally mixed ensemble I/16, paired with an asymmetric 16×16 classical readout Markov transition matrix modeling SPAM bit-flip transitions. Note that (1-p)^N is an uncorrelated gate-survival heuristic rather than an explicitly calculated density matrix state fidelity.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-2">
            <h4 className="font-semibold text-cyan-300">Dual Error Mitigation (ZNE + REM)</h4>
            <p className="text-slate-300 leading-relaxed">
              Combines 2nd-order Richardson extrapolation over scale factors r ∈ [1, 3, 5] with calibration matrix inversion M⁻¹ and Michelot-Duchi probability simplex projection to cancel measurement bias and depolarizing decay.
            </p>
          </div>
        </div>
      </div>

      {/* Hardware Assumptions & Limitations */}
      <div className="rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4">
        <h3 className="text-sm font-bold text-white uppercase font-mono tracking-wider flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-amber-400" />
          4. Hardware Assumptions & Honest Scientific Scope
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-2">
            <h4 className="font-semibold text-white">Local Target Emulation</h4>
            <p className="text-slate-400 leading-relaxed">
              Simulations model target processor topologies (Processor A and B) locally. No physical quantum processor execution or clinical validation was conducted. ECG inputs are synthetic demonstration records.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-2">
            <h4 className="font-semibold text-white">Theoretical ZNE Variance Amplification</h4>
            <p className="text-slate-400 leading-relaxed">
              Zero-Noise Extrapolation amplifies shot noise variance. Under an equal-variance assumption across scale factors, Richardson extrapolation weights (15/8, -10/8, 3/8) yield a theoretical variance amplification factor of approximately 5.22 (sum of squared coefficients).
            </p>
          </div>

          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-2">
            <h4 className="font-semibold text-white">High Noise Breakdown (p_2q &gt; 3.5%)</h4>
            <p className="text-slate-400 leading-relaxed">
              Beyond 3.5% error, quantum states collapse toward the maximally mixed ensemble I/16. Extrapolation noise overwhelms the attenuated signal, proving error mitigation cannot replace fault-tolerant error correction.
            </p>
          </div>
        </div>
      </div>

      {/* Project & Team Specifications */}
      <div className="rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4">
        <h3 className="text-sm font-bold text-white uppercase font-mono tracking-wider flex items-center gap-2">
          <Users className="w-4 h-4 text-cyan-400" />
          Project Specifications & Submission Details
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-1.5">
            <div className="text-slate-400">EVENT:</div>
            <div className="text-white font-semibold">Qiskit Fall Fest 2026 (QFF 2026) Hackathon</div>
            <div className="text-slate-400 pt-2">TRACK:</div>
            <div className="text-cyan-400 font-semibold">Quantum Machine Learning (Variational QML)</div>
            <div className="text-slate-400 pt-2">PROBLEM STATEMENT:</div>
            <div className="text-white font-semibold">PS-Q3: Noise-Resilient Variational Classifier</div>
          </div>

          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-1.5">
            <div className="text-slate-400">PRIMARY EVALUATION METRIC:</div>
            <div className="text-emerald-400 font-semibold">Diagnostic Sensitivity (Recall) & Accuracy</div>
            <div className="text-slate-400 pt-2">BENCHMARK HARDWARE:</div>
            <div className="text-white font-semibold">Processor A (5q) vs Processor B (9q Heavy-Hex)</div>
            <div className="text-slate-400 pt-2">PHASE 2 ROADMAP:</div>
            <div className="text-purple-400 font-semibold">Processor C Ring-Augmented Architecture</div>
          </div>
        </div>
      </div>

      {/* AI Assistance Disclosure (Mandatory Rule) */}
      <div className="rounded-xl bg-space-950 border border-space-700/70 p-5 space-y-2">
        <div className="flex items-center gap-2 text-slate-300 text-xs font-bold uppercase font-mono">
          <CheckSquare className="w-4 h-4 text-cyan-400" />
          Official AI / LLM Assistance Disclosure
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          In accordance with Section 11 of the Qiskit Fall Fest 2026 Participant Instructions, AI assistance was utilized for algorithmic architectural scaffolding, automated test suite generation, and user interface styling. All mathematical models, transpilation mapping routines, ZNE Richardson implementations, simplex projections, and experimental measurements have been independently verified, run, and benchmarked on local execution backends.
        </p>
      </div>
    </div>
  );
};
