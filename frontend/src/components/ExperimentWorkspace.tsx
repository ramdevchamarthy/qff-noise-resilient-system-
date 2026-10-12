import React, { useState } from 'react';
import { Play, Settings2, Activity, Zap, Cpu, Sliders, CheckCircle2 } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

interface Sample {
  id: string;
  waveform_type: string;
  label: number;
  features: {
    rr_interval_ms: number;
    qrs_duration_ms: number;
    r_peak_mv: number;
    st_segment_mv: number;
  };
  waveform: Array<{ step: number; voltage: number }>;
}

interface ExperimentWorkspaceProps {
  samples: Sample[];
  onRunExperiment: (payload: any) => Promise<void>;
  isLoading: boolean;
}

export const ExperimentWorkspace: React.FC<ExperimentWorkspaceProps> = ({
  samples,
  onRunExperiment,
  isLoading,
}) => {
  const [selectedSampleId, setSelectedSampleId] = useState<string>(samples[0]?.id || 'PAT-1000');
  const [processor, setProcessor] = useState<'A' | 'B'>('A');
  const [noiseEnabled, setNoiseEnabled] = useState<boolean>(true);
  const [noisePreset, setNoisePreset] = useState<'calibrated' | 'custom'>('calibrated');
  const [customP2q, setCustomP2q] = useState<number>(0.005);
  const [customPro, setCustomPro] = useState<number>(0.015);
  const [mitigationMethod, setMitigationMethod] = useState<'none' | 'readout' | 'zne' | 'dual'>('dual');
  const [shots, setShots] = useState<number>(1024);
  const [seed, setSeed] = useState<number>(42);

  const currentSample = samples.find((s) => s.id === selectedSampleId) || samples[0];

  const handleExecute = () => {
    const payload = {
      sample_id: selectedSampleId,
      processor,
      noise_enabled: noiseEnabled,
      noise_intensity_multiplier: 1.0,
      custom_p_2q: noisePreset === 'custom' ? customP2q : undefined,
      custom_p_ro: noisePreset === 'custom' ? customPro : undefined,
      mitigation_method: noiseEnabled ? mitigationMethod : 'none',
      shots,
      seed,
    };
    onRunExperiment(payload);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-space-700/80 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Quantum Experiment Workspace</h2>
          <p className="text-xs text-slate-400">
            Configure clinical ECG signals, physical target hardware, calibrated device noise, and error mitigation.
          </p>
        </div>

        <button
          onClick={handleExecute}
          disabled={isLoading}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm shadow-xl transition-all ${
            isLoading
              ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 active:scale-95 shadow-cyan-950/50'
          }`}
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
              <span>Simulating Quantum Circuits...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Run Experiment</span>
            </>
          )}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Sample & Signal Preview (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Sample Selector */}
          <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-4">
            <div className="flex items-center justify-between text-slate-300">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-cyan-400" />
                Select Patient ECG Record
              </span>
              <span className="text-[11px] font-mono text-cyan-400">MIT-BIH Database</span>
            </div>

            <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto pr-1">
              {samples.slice(0, 8).map((s) => {
                const isSelected = s.id === selectedSampleId;
                const isArrhythmia = s.label === 1;
                return (
                  <button
                    key={s.id}
                    onClick={() => setSelectedSampleId(s.id)}
                    className={`flex items-center justify-between p-3 rounded-lg border text-left transition-all ${
                      isSelected
                        ? 'bg-cyan-500/10 border-cyan-500/40 text-white shadow-sm'
                        : 'bg-space-850 border-space-700/60 text-slate-400 hover:border-space-600 hover:text-slate-200'
                    }`}
                  >
                    <div>
                      <div className="text-xs font-mono font-bold text-slate-200">{s.id}</div>
                      <div className="text-[11px] text-slate-400">{s.waveform_type}</div>
                    </div>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                        isArrhythmia
                          ? 'bg-rose-950 text-rose-300 border border-rose-800/60'
                          : 'bg-emerald-950 text-emerald-300 border border-emerald-800/60'
                      }`}
                    >
                      {isArrhythmia ? 'ARRHYTHMIA' : 'NORMAL'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ECG Signal Preview Chart */}
          {currentSample && (
            <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">ECG Lead II Waveform Profile</span>
                <span className="text-xs font-mono text-slate-400">{currentSample.waveform_type}</span>
              </div>

              <div className="h-40 w-full bg-space-950 rounded-lg p-2 border border-space-800">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={currentSample.waveform}>
                    <XAxis dataKey="step" hide />
                    <YAxis domain={[-0.6, 2.2]} hide />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }}
                      formatter={(val: any) => [`${val} mV`, 'Amplitude']}
                    />
                    <Line
                      type="monotone"
                      dataKey="voltage"
                      stroke="#06b6d4"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Biomarker Values Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400 block text-[10px]">R-R INTERVAL</span>
                  <span className="text-cyan-300 font-semibold">{currentSample.features.rr_interval_ms} ms</span>
                </div>
                <div className="p-2 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400 block text-[10px]">QRS DURATION</span>
                  <span className="text-cyan-300 font-semibold">{currentSample.features.qrs_duration_ms} ms</span>
                </div>
                <div className="p-2 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400 block text-[10px]">R-PEAK AMPLITUDE</span>
                  <span className="text-cyan-300 font-semibold">{currentSample.features.r_peak_mv} mV</span>
                </div>
                <div className="p-2 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400 block text-[10px]">ST DEVIATION</span>
                  <span className="text-cyan-300 font-semibold">{currentSample.features.st_segment_mv} mV</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Hardware & Noise Controls (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Target Architecture Selector */}
          <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-cyan-400" />
              Target Hardware Architecture
            </span>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setProcessor('A')}
                className={`p-4 rounded-xl border text-left transition-all ${
                  processor === 'A'
                    ? 'bg-cyan-500/10 border-cyan-500/50 shadow-md shadow-cyan-950'
                    : 'bg-space-850 border-space-700/70 hover:border-space-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-white">Processor A</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-space-800 text-slate-300 border border-space-700">5 Qubits</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">Fixed online benchmark with star-linear coupling centered at qubit 1.</p>
                <div className="text-[11px] font-mono text-cyan-400 mt-2">Edges: (0,1), (1,2), (1,3), (3,4)</div>
              </button>

              <button
                onClick={() => setProcessor('B')}
                className={`p-4 rounded-xl border text-left transition-all ${
                  processor === 'B'
                    ? 'bg-blue-500/10 border-blue-500/50 shadow-md shadow-blue-950'
                    : 'bg-space-850 border-space-700/70 hover:border-space-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-white">Processor B</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-space-800 text-slate-300 border border-space-700">9 Qubits</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">IBM heavy-hex inspired lattice designed to suppress inter-qubit crosstalk.</p>
                <div className="text-[11px] font-mono text-blue-400 mt-2">12 coupling edges (unit cell)</div>
              </button>
            </div>
          </div>

          {/* Noise Model & Calibration Setup */}
          <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-amber-400" />
                Physical Noise Environment
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Enable Noise</span>
                <input
                  type="checkbox"
                  checked={noiseEnabled}
                  onChange={(e) => setNoiseEnabled(e.target.checked)}
                  className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
                />
              </div>
            </div>

            {noiseEnabled && (
              <div className="space-y-4 pt-1">
                <div className="flex items-center gap-2 text-xs">
                  <button
                    onClick={() => setNoisePreset('calibrated')}
                    className={`px-3 py-1.5 rounded-lg border font-medium ${
                      noisePreset === 'calibrated'
                        ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300'
                        : 'bg-space-850 border-space-700 text-slate-400'
                    }`}
                  >
                    Authoritative QFF Calibration
                  </button>
                  <button
                    onClick={() => setNoisePreset('custom')}
                    className={`px-3 py-1.5 rounded-lg border font-medium ${
                      noisePreset === 'custom'
                        ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300'
                        : 'bg-space-850 border-space-700 text-slate-400'
                    }`}
                  >
                    Custom Intensity Sliders
                  </button>
                </div>

                {noisePreset === 'calibrated' ? (
                  <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-space-850 border border-space-800 text-xs font-mono">
                    <div>
                      <span className="text-slate-400 block text-[10px]">2-QUBIT DEPOLARIZING (CX)</span>
                      <span className="text-amber-400 font-semibold">0.50% (0.005)</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">READOUT ERROR RATE</span>
                      <span className="text-amber-400 font-semibold">1.50% (0.015)</span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3 p-3 rounded-lg bg-space-850 border border-space-800">
                    <div>
                      <div className="flex justify-between text-xs font-mono mb-1">
                        <span className="text-slate-300">Two-Qubit Error (p_2q)</span>
                        <span className="text-amber-400">{(customP2q * 100).toFixed(2)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="0.05"
                        step="0.002"
                        value={customP2q}
                        onChange={(e) => setCustomP2q(parseFloat(e.target.value))}
                        className="w-full accent-amber-500 cursor-pointer"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs font-mono mb-1">
                        <span className="text-slate-300">Readout Error (p_ro)</span>
                        <span className="text-amber-400">{(customPro * 100).toFixed(2)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="0.05"
                        step="0.002"
                        value={customPro}
                        onChange={(e) => setCustomPro(parseFloat(e.target.value))}
                        className="w-full accent-amber-500 cursor-pointer"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Mitigation Strategy Selector */}
          <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Sliders className="w-4 h-4 text-cyan-400" />
              Quantum Error Mitigation Strategy
            </span>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { id: 'none', label: 'Unmitigated', desc: 'Raw noisy execution (Baseline)' },
                { id: 'readout', label: 'Readout Only', desc: 'M^-1 simplex inversion' },
                { id: 'zne', label: 'ZNE Only', desc: 'Gate folding r=1,3,5' },
                { id: 'dual', label: 'Dual-Layer', desc: 'ZNE + Readout (Recommended)' },
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMitigationMethod(m.id as any)}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    mitigationMethod === m.id
                      ? 'bg-cyan-500/15 border-cyan-500/50 text-white shadow-sm'
                      : 'bg-space-850 border-space-700 text-slate-400 hover:border-space-600'
                  }`}
                >
                  <div className="text-xs font-bold text-slate-200">{m.label}</div>
                  <div className="text-[10px] text-slate-400 mt-1">{m.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Execution Settings */}
          <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
            <div className="flex items-center gap-4">
              <div>
                <span className="text-slate-400 block text-[10px]">MEASUREMENT SHOTS</span>
                <select
                  value={shots}
                  onChange={(e) => setShots(parseInt(e.target.value))}
                  className="bg-space-850 border border-space-700 rounded px-2.5 py-1 text-slate-200"
                >
                  <option value={512}>512 shots</option>
                  <option value={1024}>1024 shots</option>
                  <option value={2048}>2048 shots</option>
                  <option value={4096}>4096 shots</option>
                </select>
              </div>

              <div>
                <span className="text-slate-400 block text-[10px]">RANDOM SEED</span>
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(parseInt(e.target.value) || 0)}
                  className="bg-space-850 border border-space-700 rounded px-2 py-1 w-20 text-slate-200"
                />
              </div>
            </div>

            <div className="text-right">
              <span className="text-slate-400 block text-[10px]">VQC TOPOLOGY</span>
              <span className="text-cyan-400">4 Qubits • 2 Layers • SU(2)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
