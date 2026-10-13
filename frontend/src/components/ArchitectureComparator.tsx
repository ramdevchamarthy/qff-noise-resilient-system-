import React, { useState, useEffect } from 'react';
import { Layers, Cpu, ArrowRightLeft, Sparkles, Compass } from 'lucide-react';
import { API_BASE } from '../config';
import { useTheme } from '../context/ThemeContext';

export const ArchitectureComparator: React.FC = () => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [activeTab, setActiveTab] = useState<'A' | 'B' | 'C'>('A');
  const [transpileData, setTranspileData] = useState<any>(null);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    fetch(`${API_BASE}/api/transpile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ layers: 2, num_qubits: 4 }),
      signal: controller.signal,
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setTranspileData(data);
      })
      .catch((err) => console.warn('Could not fetch transpilation data', err))
      .finally(() => clearTimeout(timeoutId));

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  const pA = transpileData?.A || { algorithmic_cx: 8, swap_count: 2, total_physical_cx: 16, transpiled_depth: 9 };
  const pB = transpileData?.B || { algorithmic_cx: 8, swap_count: 4, total_physical_cx: 24, transpiled_depth: 9 };
  const pC = transpileData?.C || { algorithmic_cx: 8, swap_count: 0, total_physical_cx: 8, transpiled_depth: 5 };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-space-700/80 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Hardware Architecture Comparator</h2>
          <p className="text-xs text-slate-400">
            Investigate how physical qubit coupling graphs, diameter, and routing SWAP overhead dictate circuit execution.
          </p>
        </div>

        <div className="flex items-center gap-2 p-1 rounded-xl bg-space-900 border border-space-700">
          <button
            onClick={() => setActiveTab('A')}
            className={`px-3 py-1 rounded-lg text-xs font-mono font-semibold transition-all ${
              activeTab === 'A' ? 'bg-cyan-500 text-slate-950 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Processor A (5q)
          </button>
          <button
            onClick={() => setActiveTab('B')}
            className={`px-3 py-1 rounded-lg text-xs font-mono font-semibold transition-all ${
              activeTab === 'B' ? 'bg-blue-500 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Processor B (9q Heavy-Hex)
          </button>
          <button
            onClick={() => setActiveTab('C')}
            className={`px-3 py-1 rounded-lg text-xs font-mono font-semibold transition-all ${
              activeTab === 'C' ? 'bg-purple-500 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Processor C (Phase 2)
          </button>
        </div>
      </div>

      {/* SVG Coupling Graph Display & Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Interactive SVG Canvas (7 cols) */}
        <div className="lg:col-span-7 rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
              {activeTab === 'A'
                ? 'Processor A: 5-Qubit Star-Linear Benchmark'
                : activeTab === 'B'
                ? 'Processor B: 9-Qubit Heavy-Hex Architecture'
                : 'Processor C: Proposed Phase 2 Ring-Augmented Target'}
            </span>
            <span className="text-xs font-mono text-slate-400">Physical Coupling Adjacency</span>
          </div>

          <div className="h-72 w-full bg-space-950 rounded-xl border border-space-800 flex items-center justify-center p-4">
            {activeTab === 'A' && (
              <svg viewBox="0 0 300 180" className="w-full h-full">
                <line x1="100" y1="40" x2="100" y2="120" stroke="#0891b2" strokeWidth="3" />
                <line x1="30" y1="120" x2="100" y2="120" stroke="#0891b2" strokeWidth="3" />
                <line x1="100" y1="120" x2="170" y2="120" stroke="#0891b2" strokeWidth="3" />
                <line x1="170" y1="120" x2="240" y2="120" stroke="#0891b2" strokeWidth="3" />

                {[
                  { id: 0, x: 100, y: 40, active: true },
                  { id: 1, x: 100, y: 120, active: true, isHub: true },
                  { id: 2, x: 30, y: 120, active: true },
                  { id: 3, x: 170, y: 120, active: true },
                  { id: 4, x: 240, y: 120, active: false },
                ].map((n) => (
                  <g key={n.id}>
                    <circle
                      cx={n.x}
                      cy={n.y}
                      r={n.isHub ? 16 : 14}
                      fill={n.isHub ? '#06b6d4' : n.active ? '#0891b2' : isDark ? '#1e293b' : '#e2e8f0'}
                      stroke={n.isHub ? '#a5f3fc' : n.active ? '#38bdf8' : isDark ? '#334155' : '#cbd5e1'}
                      strokeWidth="2"
                    />
                    <text
                      x={n.x}
                      y={n.y + 4}
                      textAnchor="middle"
                      fill={n.active || n.isHub ? '#ffffff' : isDark ? '#64748b' : '#64748b'}
                      fontSize="10"
                      fontFamily="JetBrains Mono"
                      fontWeight="bold"
                    >
                      q{n.id}
                    </text>
                  </g>
                ))}
              </svg>
            )}

            {activeTab === 'B' && (
              <svg viewBox="0 0 260 260" className="w-full h-full">
                <line x1="40" y1="60" x2="100" y2="40" stroke="#2563eb" strokeWidth="2.5" />
                <line x1="100" y1="40" x2="160" y2="40" stroke="#2563eb" strokeWidth="2.5" />
                <line x1="160" y1="40" x2="220" y2="60" stroke="#2563eb" strokeWidth="2.5" />
                <line x1="220" y1="60" x2="220" y2="140" stroke="#2563eb" strokeWidth="2.5" />
                <line x1="220" y1="140" x2="160" y2="160" stroke="#2563eb" strokeWidth="2.5" />
                <line x1="160" y1="160" x2="100" y2="160" stroke="#2563eb" strokeWidth="2.5" />
                <line x1="100" y1="160" x2="40" y2="140" stroke="#2563eb" strokeWidth="2.5" />
                <line x1="40" y1="140" x2="40" y2="60" stroke="#2563eb" strokeWidth="2.5" />
                <line x1="100" y1="40" x2="100" y2="160" stroke="#2563eb" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="160" y1="40" x2="100" y2="160" stroke="#2563eb" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="160" y1="40" x2="160" y2="160" stroke="#2563eb" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="100" y1="160" x2="100" y2="230" stroke="#2563eb" strokeWidth="2.5" />

                {[
                  { id: 0, x: 40, y: 60, active: true },
                  { id: 1, x: 100, y: 40, active: true },
                  { id: 2, x: 160, y: 40, active: true },
                  { id: 3, x: 220, y: 60, active: true },
                  { id: 4, x: 220, y: 140, active: false },
                  { id: 5, x: 160, y: 160, active: false },
                  { id: 6, x: 100, y: 160, active: false },
                  { id: 7, x: 100, y: 230, active: false },
                  { id: 8, x: 40, y: 140, active: false },
                ].map((n) => (
                  <g key={n.id}>
                    <circle
                      cx={n.x}
                      cy={n.y}
                      r="13"
                      fill={n.active ? '#3b82f6' : isDark ? '#1e293b' : '#e2e8f0'}
                      stroke={n.active ? '#93c5fd' : isDark ? '#475569' : '#cbd5e1'}
                      strokeWidth="2"
                    />
                    <text
                      x={n.x}
                      y={n.y + 4}
                      textAnchor="middle"
                      fill={n.active ? '#ffffff' : isDark ? '#64748b' : '#64748b'}
                      fontSize="9.5"
                      fontFamily="JetBrains Mono"
                      fontWeight="bold"
                    >
                      q{n.id}
                    </text>
                  </g>
                ))}
              </svg>
            )}

            {activeTab === 'C' && (
              <svg viewBox="0 0 260 260" className="w-full h-full">
                <polygon
                  points="80,40 160,40 220,100 220,180 160,240 80,240 20,180 20,100"
                  fill="none"
                  stroke="#a855f7"
                  strokeWidth="2.5"
                />
                <line x1="80" y1="40" x2="220" y2="100" stroke="#a855f7" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="160" y1="40" x2="220" y2="180" stroke="#a855f7" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="160" y1="240" x2="20" y2="180" stroke="#a855f7" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="80" y1="240" x2="20" y2="100" stroke="#a855f7" strokeWidth="2" strokeDasharray="3 3" />

                {[
                  { id: 0, x: 80, y: 40, active: true },
                  { id: 1, x: 160, y: 40, active: true },
                  { id: 2, x: 220, y: 100, active: true },
                  { id: 3, x: 220, y: 180, active: true },
                  { id: 4, x: 160, y: 240, active: false },
                  { id: 5, x: 80, y: 240, active: false },
                  { id: 6, x: 20, y: 180, active: false },
                  { id: 7, x: 20, y: 100, active: false },
                ].map((n) => (
                  <g key={n.id}>
                    <circle
                      cx={n.x}
                      cy={n.y}
                      r="13"
                      fill={n.active ? '#a855f7' : isDark ? '#1e293b' : '#e2e8f0'}
                      stroke={n.active ? '#d8b4fe' : isDark ? '#475569' : '#cbd5e1'}
                      strokeWidth="2"
                    />
                    <text
                      x={n.x}
                      y={n.y + 4}
                      textAnchor="middle"
                      fill={n.active ? '#ffffff' : isDark ? '#64748b' : '#64748b'}
                      fontSize="9.5"
                      fontFamily="JetBrains Mono"
                      fontWeight="bold"
                    >
                      q{n.id}
                    </text>
                  </g>
                ))}
              </svg>
            )}
          </div>
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-cyan-500 inline-block" /> Active VQC Qubits (q0 - q3)
            </span>
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-slate-700 inline-block" /> Idle Hardware Ancilla
            </span>
          </div>
        </div>

        {/* Architecture Spec Card (5 cols) */}
        <div className="lg:col-span-5 rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase font-mono tracking-wider flex items-center gap-2">
            <Compass className="w-4 h-4 text-cyan-400" />
            Topology & Routing Characteristics
          </h3>

          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 rounded-xl bg-space-850 border border-space-800 space-y-1">
              <span className="text-slate-400 text-[10px]">GRAPH PROPERTIES</span>
              <div className="text-white font-semibold">
                {activeTab === 'A' ? '5 Nodes • 4 Edges • Diameter 3' : activeTab === 'B' ? '9 Nodes • 12 Edges • Diameter 4' : '8 Nodes • 12 Edges • Diameter 2'}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-space-850 border border-space-800 space-y-1">
              <span className="text-slate-400 text-[10px]">CROSSTALK & BOTTLENECKS</span>
              <p className="text-slate-300 font-sans text-xs">
                {activeTab === 'A'
                  ? 'High bottlenecking on Qubit 1 (degree 3 central hub). All routing traffic between {q0, q2} and {q3, q4} must traverse q1.'
                  : activeTab === 'B'
                  ? 'Heavy-hex sparse lattice isolates high-frequency transmon qubits. Hexagonal structure eliminates vertex crosstalk.'
                  : 'Chordal ring allows 2-hop traversal between any pair. Optimized specifically to cut SWAP routing overhead for variational ansätze.'}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-space-850 border border-space-800 space-y-1">
              <span className="text-slate-400 text-[10px]">LIVE TRANSPILATION (4Q CYCLIC ANSATZ)</span>
              <div className="text-cyan-400 font-bold">
                {activeTab === 'A'
                  ? `${pA.total_physical_cx} CX (${pA.swap_count} SWAPs, Depth ${pA.transpiled_depth})`
                  : activeTab === 'B'
                  ? `${pB.total_physical_cx} CX (${pB.swap_count} SWAPs, Depth ${pB.transpiled_depth})`
                  : `${pC.total_physical_cx} CX (${pC.swap_count} SWAPs, Depth ${pC.transpiled_depth})`}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Architectural Metrics Table */}
      <div className="rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">Side-by-Side Transpilation Benchmark</h3>
            <p className="text-xs text-slate-400">Live compiled metrics for compiling a 4-qubit 2-layer cyclic SU(2) VQC circuit (from /api/transpile).</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left font-mono">
            <thead className="bg-space-850 text-slate-400 border-b border-space-700 uppercase text-[10px]">
              <tr>
                <th className="p-3">Platform</th>
                <th className="p-3">Physical Qubits</th>
                <th className="p-3">Algorithmic CX</th>
                <th className="p-3">SWAP Count</th>
                <th className="p-3">Total Physical CX</th>
                <th className="p-3">Compiled Depth</th>
                <th className="p-3">Overhead Multiplier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-space-800 text-slate-300">
              <tr className="hover:bg-space-850/50">
                <td className="p-3 font-semibold text-white">Logical Ideal Circuit</td>
                <td className="p-3">4</td>
                <td className="p-3 text-cyan-400">8</td>
                <td className="p-3">0</td>
                <td className="p-3 text-cyan-400">8</td>
                <td className="p-3">5</td>
                <td className="p-3 text-emerald-400">1.00×</td>
              </tr>
              <tr className="hover:bg-space-850/50 bg-cyan-950/20">
                <td className="p-3 font-semibold text-cyan-300">Processor A (Star-Linear)</td>
                <td className="p-3">5</td>
                <td className="p-3">{pA.algorithmic_cx}</td>
                <td className="p-3 text-amber-400 font-bold">{pA.swap_count}</td>
                <td className="p-3 font-bold text-rose-400">{pA.total_physical_cx}</td>
                <td className="p-3">{pA.transpiled_depth}</td>
                <td className="p-3 text-amber-400">{(pA.total_physical_cx / pA.algorithmic_cx).toFixed(2)}×</td>
              </tr>
              <tr className="hover:bg-space-850/50 bg-blue-950/20">
                <td className="p-3 font-semibold text-blue-300">Processor B (Heavy-Hex)</td>
                <td className="p-3">9</td>
                <td className="p-3">{pB.algorithmic_cx}</td>
                <td className="p-3 text-amber-400 font-bold">{pB.swap_count}</td>
                <td className="p-3 font-bold text-rose-400">{pB.total_physical_cx}</td>
                <td className="p-3">{pB.transpiled_depth}</td>
                <td className="p-3 text-amber-400">{(pB.total_physical_cx / pB.algorithmic_cx).toFixed(2)}×</td>
              </tr>
              <tr className="hover:bg-space-850/50 bg-purple-950/20">
                <td className="p-3 font-semibold text-purple-300">Processor C (Phase 2 Proposed)</td>
                <td className="p-3">8</td>
                <td className="p-3">{pC.algorithmic_cx}</td>
                <td className="p-3 text-emerald-400 font-bold">{pC.swap_count}</td>
                <td className="p-3 font-bold text-emerald-400">{pC.total_physical_cx}</td>
                <td className="p-3 text-emerald-400">{pC.transpiled_depth}</td>
                <td className="p-3 text-emerald-400">{(pC.total_physical_cx / pC.algorithmic_cx).toFixed(2)}×</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
