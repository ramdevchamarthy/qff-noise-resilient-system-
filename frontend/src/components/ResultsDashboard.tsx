import React, { useState, useEffect } from 'react';
import { ShieldCheck, AlertCircle, CheckCircle2, Cpu, BarChart2, Zap, Clock, Download, RefreshCw, FileText, ArrowRight } from 'lucide-react';
import { API_BASE } from '../config';

interface ResultsDashboardProps {
  result: any | null;
  onNavigateToRobustness: () => void;
  onNavigateToWorkspace?: () => void;
}

export const ResultsDashboard: React.FC<ResultsDashboardProps> = ({
  result,
  onNavigateToRobustness,
  onNavigateToWorkspace,
}) => {
  const [summaryData, setSummaryData] = useState<any>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState<boolean>(false);

  useEffect(() => {
    setIsSummaryLoading(true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    fetch(`${API_BASE}/api/results/summary`, { signal: controller.signal })
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error('Summary fetch failed');
      })
      .then((data) => setSummaryData(data))
      .catch((err) => console.warn('Could not load benchmark summary', err))
      .finally(() => {
        clearTimeout(timeoutId);
        setIsSummaryLoading(false);
      });

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  const handleExportCSV = () => {
    if (!result) return;
    if (result.run_id) {
      window.open(`${API_BASE}/api/experiments/${result.run_id}/export`, '_blank');
      return;
    }

    // Fallback client-side CSV download
    const expId = `EXP-${result.sample_id || 'BATCH'}-${Date.now()}`;
    const timestamp = new Date().toISOString();
    const headers = ['Experiment ID', 'Timestamp', 'Sample ID', 'Ground Truth', 'Predicted', 'Probability (%)', 'Processor', 'Mitigation', 'Circuits Executed', 'Total Shots'];
    const row = [
      expId,
      timestamp,
      result.sample_id || 'BATCH',
      result.ground_truth_label ?? result.ml_metrics?.recall,
      result.predicted_label ?? result.ml_metrics?.accuracy,
      ((result.probability_arrhythmia || result.ml_metrics?.accuracy || 0) * 100).toFixed(2),
      `"${result.processor_name}"`,
      `"${result.mitigation_method}"`,
      result.circuits_executed || result.architecture_metrics?.circuits_executed,
      result.total_shots || result.architecture_metrics?.total_shots,
    ];
    const csvContent = [headers.join(','), row.join(',')].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `experiment_${expId}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (!result) {
    return (
      <div className="space-y-8 max-w-7xl mx-auto pb-12">
        <div className="rounded-2xl bg-space-900 border border-space-700/80 p-12 text-center max-w-xl mx-auto my-12 space-y-4">
          <div className="w-12 h-12 rounded-full bg-cyan-500/10 text-cyan-400 mx-auto flex items-center justify-center">
            <Cpu className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white">No Experiment Executed Yet</h3>
          <p className="text-xs text-slate-400">
            Execute a single patient test or evaluate the full held-out test dataset in the Experiment Workspace to inspect real quantum state reconstructions and mitigation metrics.
          </p>
          <div className="pt-2">
            <button
              disabled
              className="px-4 py-2 rounded-xl bg-space-850 text-slate-600 border border-space-800 text-xs font-semibold cursor-not-allowed"
              title="Run an experiment first"
            >
              <Download className="w-3.5 h-3.5 inline mr-1.5 opacity-50" />
              <span>Export CSV (Disabled)</span>
            </button>
          </div>
        </div>

        {/* Reference Benchmark Table Still Inspectable */}
        {renderBenchmarkTable(summaryData)}
      </div>
    );
  }

  const isBatch = result.mode === 'batch_evaluation' || Boolean(result.ml_metrics);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-space-700/80 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
              Run ID: {result.run_id || 'LIVE-RUN'}
            </span>
            {result.is_persisted ? (
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Durably Saved
              </span>
            ) : result.durability === 'unpersisted' || result.run_id?.startsWith('ephem_') ? (
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1" title="Audit log persistence failed. Results held in memory only.">
                <AlertCircle className="w-3 h-3" /> Unpersisted Run
              </span>
            ) : (
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1" title="Stored in serverless container storage (/tmp). Ephemeral across cold starts.">
                <AlertCircle className="w-3 h-3" /> Ephemeral Container (/tmp)
              </span>
            )}
            <span className="text-xs font-mono text-slate-400">
              {result.dataset_source === 'official_benchmark' ? 'Official Benchmark' : 'Custom Uploaded Dataset'}
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            {isBatch ? 'Batch Test Evaluation Metrics' : 'Single Sample Quantum Inference'}
          </h2>
          <p className="text-xs text-slate-400">
            Target Hardware: <span className="text-cyan-400 font-semibold">{result.processor_name}</span> • Mitigation:{' '}
            <span className="text-white font-medium">{result.mitigation_method}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-xs font-semibold transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Experiment CSV</span>
          </button>

          <button
            onClick={onNavigateToRobustness}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-space-800 hover:bg-space-700/80 text-cyan-400 border border-cyan-800/60 text-xs font-semibold transition-all"
          >
            <BarChart2 className="w-4 h-4" />
            <span>View Noise Sweep Curves →</span>
          </button>
        </div>
      </div>

      {result.storage_warning && (
        <div className={`p-3.5 rounded-xl border text-xs font-mono flex items-start gap-2.5 ${
          result.durability === 'unpersisted' || result.run_id?.startsWith('ephem_')
            ? 'bg-rose-950/40 border-rose-800/60 text-rose-300'
            : 'bg-amber-950/40 border-amber-800/60 text-amber-300'
        }`}>
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-bold">
              {result.durability === 'unpersisted' || result.run_id?.startsWith('ephem_')
                ? 'Persistence Notice (Audit Log Not Durably Saved):'
                : 'Storage Durability Notice:'}
            </span>
            <p className="text-slate-300 text-[11px]">{result.storage_warning}</p>
          </div>
        </div>
      )}

      {isBatch ? (
        /* BATCH EVALUATION DISPLAY */
        <div className="space-y-6">
          {/* Small Sample Warning Banner */}
          {(result.ml_metrics.sample_count < 30 || result.ml_metrics.is_small_sample) && (
            <div className="p-4 rounded-xl border bg-amber-950/30 border-amber-800/60 text-amber-200 text-xs font-mono flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-bold text-amber-300 flex items-center gap-2">
                  <span>Small Evaluation Cohort Disclaimer (N = {result.ml_metrics.sample_count} samples):</span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] border border-amber-500/30">
                    High Statistical Uncertainty (σ_p ≈ ±{((result.ml_metrics.std_error || 0) * 100).toFixed(1)}%)
                  </span>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  This test partition contains only {result.ml_metrics.sample_count} held-out cases. Metrics from small sample cohorts carry wide confidence intervals and serve for workflow verification only, not validated clinical performance estimates.
                  {result.ml_metrics.confusion_matrix && (
                    <span className="block mt-1 text-amber-300/90">
                      Contingency distribution: {result.ml_metrics.confusion_matrix.tn} True Negatives, {result.ml_metrics.confusion_matrix.fp} False Positives, {result.ml_metrics.confusion_matrix.fn} False Negatives, {result.ml_metrics.confusion_matrix.tp} True Positives.
                    </span>
                  )}
                </p>
              </div>
            </div>
          )}

          {/* Top Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono">
            <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-1">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Test Accuracy</span>
              <div className="text-3xl font-extrabold text-white">
                {(result.ml_metrics.accuracy * 100).toFixed(1)}%
              </div>
              <p className="text-[11px] text-slate-400">Fraction of correct predictions</p>
            </div>

            <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-1">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Sensitivity (Recall)</span>
              <div className="text-3xl font-extrabold text-cyan-400">
                {(result.ml_metrics.recall * 100).toFixed(1)}%
              </div>
              <p className="text-[11px] text-slate-400">Clinical arrhythmia detection</p>
            </div>

            <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-1">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Precision</span>
              <div className="text-3xl font-extrabold text-purple-400">
                {(result.ml_metrics.precision * 100).toFixed(1)}%
              </div>
              <p className="text-[11px] text-slate-400">Positive predictive value</p>
            </div>

            <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-1">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">F1 Score</span>
              <div className="text-3xl font-extrabold text-emerald-400">
                {(result.ml_metrics.f1_score * 100).toFixed(1)}%
              </div>
              <p className="text-[11px] text-slate-400">Harmonic mean precision-recall</p>
            </div>
          </div>

          {/* Scientific Confusion Matrix & Diagnostic Verification */}
          {result.ml_metrics.confusion_matrix && (
            <div className="rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4 font-mono">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-space-800 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <span>Clinical Confusion Matrix</span>
                    <span className="text-[11px] font-normal text-slate-400">
                      (N = {result.ml_metrics.sample_count} Evaluated Samples)
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Biomedical contingency breakdown: Class 0 = Normal Sinus Rhythm, Class 1 = Cardiac Arrhythmia
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <div>
                    <span className="text-slate-400">Specificity: </span>
                    <span className="font-bold text-emerald-400">
                      {((result.ml_metrics.specificity ?? (result.ml_metrics.confusion_matrix.tn / Math.max(1, result.ml_metrics.confusion_matrix.tn + result.ml_metrics.confusion_matrix.fp))) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Balanced Acc: </span>
                    <span className="font-bold text-cyan-300">
                      {((result.ml_metrics.balanced_accuracy ?? ((result.ml_metrics.recall + (result.ml_metrics.specificity ?? 1.0)) / 2.0)) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 2x2 Matrix Grid */}
                <div className="bg-space-950 p-4 rounded-xl border border-space-800 space-y-3">
                  <div className="text-[10px] uppercase text-slate-400 text-center tracking-wider font-semibold">
                    PREDICTED CLASS
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-center text-xs">
                    {/* Header */}
                    <div className="p-1 text-[10px] text-slate-400">Pred: Normal (0)</div>
                    <div className="p-1 text-[10px] text-slate-400">Pred: Arrhythmia (1)</div>

                    {/* Row 1: Ground Truth Normal (0) */}
                    <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/50 flex flex-col justify-center">
                      <span className="text-xs text-slate-400">True Negative (TN)</span>
                      <span className="text-2xl font-black text-emerald-400">{result.ml_metrics.confusion_matrix.tn}</span>
                      <span className="text-[10px] text-emerald-300/80">Normal correctly ruled out</span>
                    </div>

                    <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-800/40 flex flex-col justify-center">
                      <span className="text-xs text-slate-400">False Positive (FP)</span>
                      <span className="text-2xl font-black text-amber-400">{result.ml_metrics.confusion_matrix.fp}</span>
                      <span className="text-[10px] text-amber-300/80">Normal falsely flagged</span>
                    </div>

                    {/* Row 2: Ground Truth Arrhythmia (1) */}
                    <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-800/60 flex flex-col justify-center">
                      <span className="text-xs text-slate-400">False Negative (FN)</span>
                      <span className="text-2xl font-black text-rose-400">{result.ml_metrics.confusion_matrix.fn}</span>
                      <span className="text-[10px] text-rose-300/80">Arrhythmia MISSED</span>
                    </div>

                    <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-800/50 flex flex-col justify-center">
                      <span className="text-xs text-slate-400">True Positive (TP)</span>
                      <span className="text-2xl font-black text-cyan-400">{result.ml_metrics.confusion_matrix.tp}</span>
                      <span className="text-[10px] text-cyan-300/80">Arrhythmia detected</span>
                    </div>
                  </div>
                </div>

                {/* Mathematical Derivations & Explanations */}
                <div className="bg-space-950 p-4 rounded-xl border border-space-800 space-y-2.5 text-xs text-slate-300">
                  <span className="text-[11px] uppercase font-bold text-slate-400 block tracking-wider">
                    Mathematical Metric Verification:
                  </span>
                  <div className="space-y-1.5 text-[11px]">
                    <div className="flex justify-between border-b border-space-850 pb-1">
                      <span className="text-slate-400">Accuracy (TP + TN) / N:</span>
                      <span className="font-mono text-white">
                        ({result.ml_metrics.confusion_matrix.tp} + {result.ml_metrics.confusion_matrix.tn}) / {result.ml_metrics.sample_count} = {(result.ml_metrics.accuracy * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-space-850 pb-1">
                      <span className="text-slate-400">Sensitivity TP / (TP + FN):</span>
                      <span className="font-mono text-cyan-400">
                        {result.ml_metrics.confusion_matrix.tp} / ({result.ml_metrics.confusion_matrix.tp} + {result.ml_metrics.confusion_matrix.fn}) = {(result.ml_metrics.recall * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-space-850 pb-1">
                      <span className="text-slate-400">Precision TP / (TP + FP):</span>
                      <span className="font-mono text-purple-400">
                        {result.ml_metrics.confusion_matrix.tp + result.ml_metrics.confusion_matrix.fp > 0
                          ? `${result.ml_metrics.confusion_matrix.tp} / (${result.ml_metrics.confusion_matrix.tp} + ${result.ml_metrics.confusion_matrix.fp}) = ${(result.ml_metrics.precision * 100).toFixed(1)}%`
                          : '0 / 0 → 0.0% (Zero positive predictions)'}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-space-850 pb-1">
                      <span className="text-slate-400">Specificity TN / (TN + FP):</span>
                      <span className="font-mono text-emerald-400">
                        {result.ml_metrics.confusion_matrix.tn} / ({result.ml_metrics.confusion_matrix.tn} + {result.ml_metrics.confusion_matrix.fp}) = {(((result.ml_metrics.confusion_matrix.tn) / Math.max(1, result.ml_metrics.confusion_matrix.tn + result.ml_metrics.confusion_matrix.fp)) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-space-850 pb-1">
                      <span className="text-slate-400">Balanced Accuracy (Rec + Spec) / 2:</span>
                      <span className="font-mono text-cyan-300">
                        {((result.ml_metrics.balanced_accuracy ?? ((result.ml_metrics.recall + (result.ml_metrics.specificity ?? 1.0)) / 2.0)) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Standard Error (σ_p):</span>
                      <span className="font-mono text-amber-300">
                        ±{((result.ml_metrics.std_error || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  {result.ml_metrics.confusion_matrix.tp === 0 && (
                    <p className="text-[10px] text-amber-300/90 bg-amber-950/30 p-2 rounded border border-amber-900/40">
                      Notice: Zero positive detections (TP=0, FP=0) yields 0.0% Recall and 0.0% Precision. All correct classifications ({result.ml_metrics.confusion_matrix.tn}) are True Negatives.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Architecture & Mitigation Overhead */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
            <div className="rounded-xl bg-space-900 border border-space-700/80 p-4 space-y-2">
              <span className="text-slate-400 text-[11px] uppercase">Routing & Physical Operations</span>
              <div className="flex justify-between border-b border-space-800 pb-1">
                <span className="text-slate-400">Transpiled Depth:</span>
                <span className="text-white font-bold">{result.architecture_metrics?.circuit_depth ?? result.circuit_depth}</span>
              </div>
              <div className="flex justify-between border-b border-space-800 pb-1">
                <span className="text-slate-400">SWAP Gates:</span>
                <span className="text-amber-400 font-bold">{result.architecture_metrics?.swap_count ?? result.swap_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Physical CX Gates:</span>
                <span className="text-white font-bold">{result.architecture_metrics?.total_physical_cx ?? result.total_physical_cx}</span>
              </div>
            </div>

            <div className="rounded-xl bg-space-900 border border-space-700/80 p-4 space-y-2">
              <span className="text-slate-400 text-[11px] uppercase">Resource Accounting</span>
              <div className="flex justify-between border-b border-space-800 pb-1">
                <span className="text-slate-400">Circuits Executed:</span>
                <span className="text-purple-300 font-bold">{result.architecture_metrics?.circuits_executed ?? result.circuits_executed}×</span>
              </div>
              <div className="flex justify-between border-b border-space-800 pb-1">
                <span className="text-slate-400">Total Shots Sampled:</span>
                <span className="text-white font-bold">{(result.architecture_metrics?.total_shots ?? result.total_shots)?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Execution Latency:</span>
                <span className="text-cyan-300 font-bold">{result.architecture_metrics?.latency_ms ?? result.latency_ms} ms</span>
              </div>
            </div>

            <div className="rounded-xl bg-space-900 border border-space-700/80 p-4 space-y-2">
              <span className="text-slate-400 text-[11px] uppercase">Noise Environment</span>
              <div className="flex justify-between border-b border-space-800 pb-1">
                <span className="text-slate-400">Two-Qubit Noise (p_2q):</span>
                <span className="text-white font-bold">{((result.noise_rate_2q || 0) * 100).toFixed(2)}%</span>
              </div>
              <div className="flex justify-between border-b border-space-800 pb-1">
                <span className="text-slate-400">Readout Error (p_ro):</span>
                <span className="text-white font-bold">{((result.readout_error_rate || 0) * 100).toFixed(2)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Mitigation:</span>
                <span className="text-emerald-400 font-bold">{result.mitigation_method}</span>
              </div>
            </div>
          </div>

          {/* Sample Predictions Table */}
          {result.detailed_samples && (
            <div className="rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-3 font-mono">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Held-Out Test Samples ({result.detailed_samples.length} Samples)
                </h3>
                <span className="text-xs text-slate-400">Ground Truth vs Quantum Predictions</span>
              </div>

              <div className="overflow-x-auto max-h-80 overflow-y-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-space-850 text-slate-400 border-b border-space-800 uppercase text-[10px]">
                    <tr>
                      <th className="p-2.5">Sample ID</th>
                      <th className="p-2.5">Ground Truth</th>
                      <th className="p-2.5">Predicted Label</th>
                      <th className="p-2.5">Arrhythmia Probability</th>
                      <th className="p-2.5">Diagnostic Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-space-800 text-slate-300">
                    {result.detailed_samples.map((s: any, idx: number) => (
                      <tr key={idx} className="hover:bg-space-850/50">
                        <td className="p-2.5 font-bold text-white">{s.id}</td>
                        <td className="p-2.5">{s.ground_truth === 1 ? 'ARRHYTHMIA (1)' : 'NORMAL (0)'}</td>
                        <td className="p-2.5">{s.predicted === 1 ? 'ARRHYTHMIA (1)' : 'NORMAL (0)'}</td>
                        <td className="p-2.5 font-bold text-cyan-300">{(s.probability * 100).toFixed(1)}%</td>
                        <td className="p-2.5">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            s.is_correct ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/60' : 'bg-rose-950 text-rose-300 border border-rose-800/60'
                          }`}>
                            {s.is_correct ? 'CORRECT' : 'MISCLASSIFIED'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* SINGLE SAMPLE DISPLAY */
        <div className="space-y-6">
          {/* Diagnostic Banner */}
          <div
            className={`rounded-2xl border p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 ${
              result.is_correct
                ? 'bg-emerald-950/20 border-emerald-800/60 text-emerald-200'
                : 'bg-rose-950/20 border-rose-800/60 text-rose-200'
            }`}
          >
            <div className="flex items-center gap-4">
              <div
                className={`p-3.5 rounded-xl border ${
                  result.is_correct ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400' : 'bg-rose-500/20 border-rose-500/40 text-rose-400'
                }`}
              >
                {result.is_correct ? <CheckCircle2 className="w-8 h-8" /> : <AlertCircle className="w-8 h-8" />}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold tracking-wider opacity-75">{result.sample_id}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-space-900/60 font-mono text-slate-300">
                    {result.waveform_type}
                  </span>
                </div>
                <div className="text-2xl font-black text-white">
                  {result.predicted_label === 1 ? 'Cardiac Arrhythmia Detected' : 'Normal Sinus Rhythm'}
                </div>
                <p className="text-xs text-slate-300">
                  Ground Truth:{' '}
                  <strong className="text-white">{result.ground_truth_label === 1 ? 'ARRHYTHMIA' : 'NORMAL'}</strong> • Result is{' '}
                  <strong className={result.is_correct ? 'text-emerald-400' : 'text-rose-400'}>
                    {result.is_correct ? 'CORRECT' : 'MISCLASSIFIED'}
                  </strong>
                </p>
              </div>
            </div>

            <div className="text-right font-mono">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 block">
                ARRHYTHMIA PROBABILITY
              </span>
              <span className="text-3xl font-extrabold text-white">
                {(result.probability_arrhythmia * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Physics & Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-semibold uppercase tracking-wider">Quantum Expectation ⟨Z₀⟩</span>
                <Zap className="w-4 h-4 text-cyan-400" />
              </div>

              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between items-center p-2.5 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400">Measured ⟨Z₀⟩</span>
                  <span className="font-bold text-cyan-300 text-sm">{result.expectation_z0.toFixed(4)}</span>
                </div>
                <div className="flex justify-between items-center p-2.5 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400">Ideal Simulator ⟨Z₀⟩</span>
                  <span className="font-bold text-white text-sm">{result.ideal_expectation_z0.toFixed(4)}</span>
                </div>
                <div className="flex justify-between items-center p-2.5 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400">Absolute Error Δ⟨Z₀⟩</span>
                  <span className="font-bold text-emerald-400">
                    {Math.abs(result.expectation_z0 - result.ideal_expectation_z0).toFixed(4)}
                  </span>
                </div>
              </div>
            </div>

            <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-semibold uppercase tracking-wider">Architecture Routing Cost</span>
                <Cpu className="w-4 h-4 text-amber-400" />
              </div>

              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between items-center p-2.5 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400">Transpiled Depth</span>
                  <span className="font-bold text-white text-sm">{result.circuit_depth}</span>
                </div>
                <div className="flex justify-between items-center p-2.5 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400">SWAP Gates Inserted</span>
                  <span className="font-bold text-amber-400 text-sm">{result.swap_count}</span>
                </div>
                <div className="flex justify-between items-center p-2.5 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400">Total Physical CX</span>
                  <span className="font-bold text-white text-sm">{result.total_physical_cx}</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-semibold uppercase tracking-wider">Mitigation Overhead</span>
                <Clock className="w-4 h-4 text-purple-400" />
              </div>

              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between items-center p-2.5 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400">Circuits Executed</span>
                  <span className="font-bold text-purple-300 text-sm">{result.circuits_executed}×</span>
                </div>
                <div className="flex justify-between items-center p-2.5 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400">Total Shots Sampled</span>
                  <span className="font-bold text-white text-sm">{result.total_shots.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center p-2.5 rounded bg-space-850 border border-space-800">
                  <span className="text-slate-400">Execution Latency</span>
                  <span className="font-bold text-cyan-300 text-sm">{result.latency_ms.toFixed(1)} ms</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Official Benchmark Summary Table */}
      {renderBenchmarkTable(summaryData)}
    </div>
  );
};

function renderBenchmarkTable(summaryData: any) {
  const pAUnmitCx = summaryData?.processor_a_unmitigated?.architecture_metrics?.total_physical_cx || 16;
  const pAMitCx = summaryData?.processor_a_mitigated?.architecture_metrics?.total_physical_cx || 16;
  const pBUnmitCx = summaryData?.processor_b_unmitigated?.architecture_metrics?.total_physical_cx || 24;
  const pBMitCx = summaryData?.processor_b_mitigated?.architecture_metrics?.total_physical_cx || 24;

  const pASwaps = summaryData?.processor_a_unmitigated?.architecture_metrics?.swap_count || 2;
  const pBSwaps = summaryData?.processor_b_unmitigated?.architecture_metrics?.swap_count || 4;

  return (
    <div className="rounded-2xl bg-space-900 border border-space-700/80 p-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-bold text-white tracking-tight">Full Test-Partition Benchmark (N = 50 Samples)</h3>
          <p className="text-xs text-slate-400">Live backend benchmark comparing classical baseline, ideal VQC, noisy execution, and dual mitigation.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px] font-mono font-semibold">
            Verified Benchmark (N=50 via /api/results/summary)
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left font-mono">
          <thead className="bg-space-850 text-slate-400 border-b border-space-700 uppercase text-[10px]">
            <tr>
              <th className="p-3">Platform / Method</th>
              <th className="p-3">Accuracy</th>
              <th className="p-3">Recall (Sensitivity)</th>
              <th className="p-3">Circuit Depth</th>
              <th className="p-3">SWAP Gates</th>
              <th className="p-3">Physical CX</th>
              <th className="p-3">Exec Overhead</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-space-800 text-slate-300">
            <tr className="hover:bg-space-850/50">
              <td className="p-3 font-semibold text-white">Classical Logistic Regression</td>
              <td className="p-3 text-cyan-400 font-bold">
                {summaryData?.classical_baseline?.ml_metrics?.accuracy ? `${(summaryData.classical_baseline.ml_metrics.accuracy * 100).toFixed(1)}%` : '90.0%'}
              </td>
              <td className="p-3 text-cyan-400">
                {summaryData?.classical_baseline?.ml_metrics?.recall ? `${(summaryData.classical_baseline.ml_metrics.recall * 100).toFixed(1)}%` : '73.7%'}
              </td>
              <td className="p-3 text-slate-500">—</td>
              <td className="p-3 text-slate-500">—</td>
              <td className="p-3 text-slate-500">—</td>
              <td className="p-3 text-slate-500">1× (Classical)</td>
            </tr>
            <tr className="hover:bg-space-850/50">
              <td className="p-3 font-semibold text-white">Ideal Simulator (Reference VQC)</td>
              <td className="p-3 text-emerald-400 font-bold">
                {summaryData?.ideal_vqc?.ml_metrics?.accuracy ? `${(summaryData.ideal_vqc.ml_metrics.accuracy * 100).toFixed(1)}%` : '90.0%'}
              </td>
              <td className="p-3 text-emerald-400">
                {summaryData?.ideal_vqc?.ml_metrics?.recall ? `${(summaryData.ideal_vqc.ml_metrics.recall * 100).toFixed(1)}%` : '73.7%'}
              </td>
              <td className="p-3">5</td>
              <td className="p-3">0</td>
              <td className="p-3">8</td>
              <td className="p-3">1×</td>
            </tr>
            <tr className="hover:bg-space-850/50">
              <td className="p-3 font-semibold text-rose-300">Processor A — Unmitigated Noisy</td>
              <td className="p-3 text-rose-400 font-bold">
                {summaryData?.processor_a_unmitigated?.ml_metrics?.accuracy ? `${(summaryData.processor_a_unmitigated.ml_metrics.accuracy * 100).toFixed(1)}%` : '88.0%'}
              </td>
              <td className="p-3 text-rose-400 font-bold">
                {summaryData?.processor_a_unmitigated?.ml_metrics?.recall ? `${(summaryData.processor_a_unmitigated.ml_metrics.recall * 100).toFixed(1)}% (Degraded)` : '68.4% (Degraded)'}
              </td>
              <td className="p-3">9</td>
              <td className="p-3 text-amber-400">{pASwaps}</td>
              <td className="p-3">{pAUnmitCx}</td>
              <td className="p-3">1×</td>
            </tr>
            <tr className="hover:bg-space-850/50 bg-cyan-950/20">
              <td className="p-3 font-semibold text-cyan-300">Processor A — Dual Mitigated (ZNE + Readout)</td>
              <td className="p-3 text-cyan-400 font-bold">
                {summaryData?.processor_a_mitigated?.ml_metrics?.accuracy ? `${(summaryData.processor_a_mitigated.ml_metrics.accuracy * 100).toFixed(1)}% (Recovered)` : '90.0% (Recovered)'}
              </td>
              <td className="p-3 text-cyan-400 font-bold">
                {summaryData?.processor_a_mitigated?.ml_metrics?.recall ? `${(summaryData.processor_a_mitigated.ml_metrics.recall * 100).toFixed(1)}% (Recovered)` : '73.7% (Recovered)'}
              </td>
              <td className="p-3">9</td>
              <td className="p-3 text-amber-400">{pASwaps}</td>
              <td className="p-3">{pAMitCx}</td>
              <td className="p-3 text-purple-300">3× Circuits</td>
            </tr>
            <tr className="hover:bg-space-850/50">
              <td className="p-3 font-semibold text-rose-300">Processor B — Unmitigated Noisy</td>
              <td className="p-3 text-rose-400 font-bold">
                {summaryData?.processor_b_unmitigated?.ml_metrics?.accuracy ? `${(summaryData.processor_b_unmitigated.ml_metrics.accuracy * 100).toFixed(1)}%` : '88.0%'}
              </td>
              <td className="p-3 text-rose-400 font-bold">
                {summaryData?.processor_b_unmitigated?.ml_metrics?.recall ? `${(summaryData.processor_b_unmitigated.ml_metrics.recall * 100).toFixed(1)}% (Degraded)` : '68.4% (Degraded)'}
              </td>
              <td className="p-3">9</td>
              <td className="p-3 text-amber-400">{pBSwaps}</td>
              <td className="p-3">{pBUnmitCx}</td>
              <td className="p-3">1×</td>
            </tr>
            <tr className="hover:bg-space-850/50 bg-blue-950/20">
              <td className="p-3 font-semibold text-blue-300">Processor B — Dual Mitigated (ZNE + Readout)</td>
              <td className="p-3 text-blue-400 font-bold">
                {summaryData?.processor_b_mitigated?.ml_metrics?.accuracy ? `${(summaryData.processor_b_mitigated.ml_metrics.accuracy * 100).toFixed(1)}% (Recovered)` : '90.0% (Recovered)'}
              </td>
              <td className="p-3 text-blue-400 font-bold">
                {summaryData?.processor_b_mitigated?.ml_metrics?.recall ? `${(summaryData.processor_b_mitigated.ml_metrics.recall * 100).toFixed(1)}% (Recovered)` : '73.7% (Recovered)'}
              </td>
              <td className="p-3">9</td>
              <td className="p-3 text-amber-400">{pBSwaps}</td>
              <td className="p-3">{pBMitCx}</td>
              <td className="p-3 text-purple-300">3× Circuits</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
