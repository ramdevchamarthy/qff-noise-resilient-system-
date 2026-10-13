import React, { useState } from 'react';
import {
  Play,
  Settings2,
  Activity,
  Zap,
  Cpu,
  Sliders,
  CheckCircle2,
  Upload,
  FileText,
  AlertCircle,
  TrendingDown,
  Sparkles,
  Layers,
  Database,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { API_BASE } from '../config';
import { useTheme } from '../context/ThemeContext';

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
  onRunExperiment: (payload: any, isBatch?: boolean) => Promise<void>;
  isLoading: boolean;
}

const SAMPLE_CLINICAL_CSV = `rr_interval_ms,qrs_duration_ms,r_peak_mv,st_segment_mv,arrhythmia_label
812.4,84.2,1.25,0.01,0
825.1,86.0,1.18,0.02,0
805.3,83.9,1.22,-0.01,0
830.0,85.5,1.20,0.01,0
815.8,87.1,1.15,0.02,0
820.5,84.8,1.24,0.00,0
540.2,132.5,1.62,-0.18,1
525.0,128.0,1.55,-0.20,1
550.8,135.2,1.70,-0.15,1
515.3,130.4,1.58,-0.22,1
535.1,133.0,1.65,-0.19,1
545.9,129.5,1.60,-0.17,1
`;

export const ExperimentWorkspace: React.FC<ExperimentWorkspaceProps> = ({
  samples,
  onRunExperiment,
  isLoading,
}) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Data source mode: official vs custom
  const [dataMode, setDataMode] = useState<'official' | 'custom'>('official');

  // Official mode state
  const [selectedSampleId, setSelectedSampleId] = useState<string>(samples[0]?.id || 'PAT-1000');

  // Custom upload state
  const [rawCsvText, setRawCsvText] = useState<string>('');
  const [datasetMeta, setDatasetMeta] = useState<any>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Column mapping & validation state
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string>('');
  const [imputationStrategy, setImputationStrategy] = useState<'mean' | 'median' | 'drop'>('mean');
  const [validationResult, setValidationResult] = useState<any>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);

  // Model training state
  const [trainedModel, setTrainedModel] = useState<any>(null);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [trainEpochs, setTrainEpochs] = useState<number>(25);
  const [trainLr, setTrainLr] = useState<number>(0.20);

  // Hardware & execution configuration
  const [processor, setProcessor] = useState<'A' | 'B'>('A');
  const [noiseEnabled, setNoiseEnabled] = useState<boolean>(true);
  const [noisePreset, setNoisePreset] = useState<'calibrated' | 'custom'>('calibrated');
  const [customP2q, setCustomP2q] = useState<number>(0.005);
  const [customPro, setCustomPro] = useState<number>(0.015);
  const [mitigationMethod, setMitigationMethod] = useState<'none' | 'readout' | 'zne' | 'dual'>('dual');
  const [shots, setShots] = useState<number>(1024);
  const [seed, setSeed] = useState<number>(42);

  const currentSample = samples.find((s) => s.id === selectedSampleId) || samples[0];

  // Upload handler
  const handleUploadCsv = async (csvContent: string, filename: string = 'custom_dataset.csv') => {
    setIsUploading(true);
    setUploadError(null);
    setValidationResult(null);
    setTrainedModel(null);

    try {
      const res = await fetch(`${API_BASE}/api/datasets/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_csv: csvContent, filename }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'CSV upload failed');
      }
      const data = await res.json();
      setDatasetMeta(data);
      setRawCsvText(csvContent);

      // Auto-suggest first 4 numeric features and last column as target
      const numericCols = data.columns
        .filter((c: any) => c.inferred_type === 'numeric')
        .map((c: any) => c.name);

      const targetCol = data.headers[data.headers.length - 1];
      setSelectedTarget(targetCol);

      const potentialFeatures = numericCols.filter((c: string) => c !== targetCol).slice(0, 4);
      setSelectedFeatures(potentialFeatures);
    } catch (err: any) {
      setUploadError(err.message || 'Error parsing CSV');
    } finally {
      setIsUploading(false);
    }
  };

  const handleValidateDataset = async () => {
    if (!datasetMeta) return;
    setIsValidating(true);
    setUploadError(null);

    try {
      const res = await fetch(`${API_BASE}/api/datasets/${datasetMeta.dataset_id}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feature_columns: selectedFeatures,
          target_column: selectedTarget,
          imputation_strategy: imputationStrategy,
          seed,
        }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Validation failed');
      }
      const data = await res.json();
      setValidationResult(data);
    } catch (err: any) {
      setUploadError(err.message || 'Dataset validation failed');
    } finally {
      setIsValidating(false);
    }
  };

  const handleTrainVQC = async () => {
    setIsTraining(true);
    setUploadError(null);

    try {
      const payload: any = {
        epochs: trainEpochs,
        batch_size: 20,
        lr: trainLr,
        seed,
        model_name: dataMode === 'custom' ? `Custom VQC (${datasetMeta?.filename || 'CSV'})` : 'Benchmark VQC',
      };

      if (dataMode === 'custom' && datasetMeta) {
        payload.dataset_id = datasetMeta.dataset_id;
        payload.feature_columns = selectedFeatures;
        payload.target_column = selectedTarget;
        payload.imputation_strategy = imputationStrategy;
      }

      const res = await fetch(`${API_BASE}/api/models/train`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Training failed');
      }

      const data = await res.json();
      setTrainedModel(data);
    } catch (err: any) {
      setUploadError(err.message || 'VQC training failed');
    } finally {
      setIsTraining(false);
    }
  };

  const toggleFeature = (colName: string) => {
    if (selectedFeatures.includes(colName)) {
      setSelectedFeatures(selectedFeatures.filter((f) => f !== colName));
    } else {
      if (selectedFeatures.length < 4) {
        setSelectedFeatures([...selectedFeatures, colName]);
      } else {
        alert('Variational Quantum Classifier takes exactly 4 features (1 feature per qubit). Deselect a feature first.');
      }
    }
  };

  const handleExecuteSingleSample = () => {
    const payload = {
      sample_id: selectedSampleId,
      model_id: trainedModel?.model_id || undefined,
      processor,
      noise_enabled: noiseEnabled,
      noise_intensity_multiplier: 1.0,
      custom_p_2q: noisePreset === 'custom' ? customP2q : undefined,
      custom_p_ro: noisePreset === 'custom' ? customPro : undefined,
      mitigation_method: noiseEnabled ? mitigationMethod : 'none',
      shots,
      seed,
    };
    onRunExperiment(payload, false);
  };

  const handleExecuteBatchEvaluation = () => {
    const payload: any = {
      model_id: trainedModel?.model_id || undefined,
      processor,
      noise_enabled: noiseEnabled,
      noise_intensity_multiplier: 1.0,
      custom_p_2q: noisePreset === 'custom' ? customP2q : undefined,
      custom_p_ro: noisePreset === 'custom' ? customPro : undefined,
      mitigation_method: noiseEnabled ? mitigationMethod : 'none',
      shots,
      seed,
    };

    if (dataMode === 'custom' && datasetMeta) {
      payload.dataset_id = datasetMeta.dataset_id;
      payload.feature_columns = selectedFeatures;
      payload.target_column = selectedTarget;
      payload.imputation_strategy = imputationStrategy;
    }

    onRunExperiment(payload, true);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header & Main Execution CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-space-700/80 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Quantum Experiment Workspace</h2>
          <p className="text-xs text-slate-400">
            Configure datasets, leakage-free preprocessing, SPSA model training, and noise mitigation experiments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExecuteBatchEvaluation}
            disabled={isLoading || (dataMode === 'custom' && !validationResult)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs shadow-xl transition-all ${
              isLoading || (dataMode === 'custom' && !validationResult)
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white active:scale-95 shadow-purple-950/50'
            }`}
            title={dataMode === 'custom' && !validationResult ? 'Validate dataset first' : 'Evaluate full test set'}
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Evaluate Full Test Set (Batch)</span>
          </button>

          <button
            onClick={handleExecuteSingleSample}
            disabled={isLoading}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs shadow-xl transition-all ${
              isLoading
                ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 active:scale-95 shadow-cyan-950/50'
            }`}
          >
            {isLoading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                <span>Simulating Circuits...</span>
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5 fill-current" />
                <span>Run Single Sample</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Mode Selector Tabs */}
      <div className="flex items-center gap-3 border-b border-space-800 pb-2">
        <button
          onClick={() => setDataMode('official')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-semibold transition-all ${
            dataMode === 'official'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Official Benchmark Dataset (Synthetic MIT-BIH)</span>
        </button>

        <button
          onClick={() => setDataMode('custom')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-semibold transition-all ${
            dataMode === 'custom'
              ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Custom CSV Dataset Upload & VQC Training</span>
        </button>
      </div>

      {uploadError && (
        <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center gap-2 font-mono">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Dataset & Features (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {dataMode === 'official' ? (
            <>
              {/* Official ECG Record Selector */}
              <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-4">
                <div className="flex items-center justify-between text-slate-300">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Activity className="w-4 h-4 text-cyan-400" />
                    Select Patient ECG Record
                  </span>
                  <span className="text-[11px] font-mono text-cyan-400">Synthetic MIT-BIH Benchmark</span>
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

              {/* ECG Waveform Visualization */}
              {currentSample && (
                <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300">ECG Lead II Waveform Profile</span>
                    <span className="text-xs font-mono text-slate-400">{currentSample.waveform_type}</span>
                  </div>

                  <div className="h-32 w-full pt-1">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={currentSample.waveform}>
                        <YAxis domain={[-0.4, 1.8]} hide />
                        <XAxis dataKey="step" hide />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: isDark ? '#0f172a' : '#ffffff',
                            borderColor: isDark ? '#334155' : '#cbd5e1',
                            color: isDark ? '#f8fafc' : '#0f172a',
                            borderRadius: '0.5rem',
                            fontSize: '11px',
                            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                          }}
                          itemStyle={{ color: isDark ? '#f8fafc' : '#0f172a' }}
                          formatter={(val: any) => [`${val} mV`, 'Voltage']}
                          labelFormatter={(l) => `t = ${l}`}
                        />
                        <Line type="monotone" dataKey="voltage" stroke="#06b6d4" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="grid grid-cols-4 gap-2 pt-2 border-t border-space-800 font-mono text-center">
                    <div className="bg-space-850 p-2 rounded">
                      <div className="text-[10px] text-slate-400">RR (ms)</div>
                      <div className="text-xs font-bold text-white">{currentSample.features.rr_interval_ms}</div>
                    </div>
                    <div className="bg-space-850 p-2 rounded">
                      <div className="text-[10px] text-slate-400">QRS (ms)</div>
                      <div className="text-xs font-bold text-white">{currentSample.features.qrs_duration_ms}</div>
                    </div>
                    <div className="bg-space-850 p-2 rounded">
                      <div className="text-[10px] text-slate-400">R-Peak (mV)</div>
                      <div className="text-xs font-bold text-white">{currentSample.features.r_peak_mv}</div>
                    </div>
                    <div className="bg-space-850 p-2 rounded">
                      <div className="text-[10px] text-slate-400">ST Dev (mV)</div>
                      <div className="text-xs font-bold text-white">{currentSample.features.st_segment_mv}</div>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              {/* Custom CSV Upload & Preview Section */}
              <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Upload className="w-4 h-4 text-purple-400" />
                    CSV File Ingestion & Inspection
                  </span>
                  <button
                    onClick={() => handleUploadCsv(SAMPLE_CLINICAL_CSV, 'sample_mit_bih.csv')}
                    disabled={isUploading}
                    className="px-2.5 py-1 rounded bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 text-[11px] font-mono transition-all"
                  >
                    Load Sample Clinical CSV
                  </button>
                </div>

                <div className="border-2 border-dashed border-space-700 hover:border-purple-500/60 rounded-xl p-4 text-center transition-all">
                  <input
                    type="file"
                    accept=".csv"
                    id="csv-file-input"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        const reader = new FileReader();
                        reader.onload = (event) => {
                          const text = event.target?.result as string;
                          if (text) handleUploadCsv(text, file.name);
                        };
                        reader.readAsText(file);
                      }
                    }}
                  />
                  <label htmlFor="csv-file-input" className="cursor-pointer block space-y-1">
                    <FileText className="w-6 h-6 text-purple-400 mx-auto" />
                    <div className="text-xs font-semibold text-slate-200">
                      {isUploading ? 'Inspecting CSV Structure...' : 'Choose a CSV file or click Load Sample above'}
                    </div>
                    <div className="text-[11px] text-slate-500">Supports headers, numeric features, and binary target label</div>
                  </label>
                </div>

                {datasetMeta && (
                  <div className="space-y-4 pt-2">
                    {/* Metadata Badges */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-center text-xs">
                      <div className="p-2.5 rounded bg-space-850 border border-space-800">
                        <div className="text-[10px] text-slate-400">Total Rows</div>
                        <div className="font-bold text-white text-sm">{datasetMeta.row_count}</div>
                      </div>
                      <div className="p-2.5 rounded bg-space-850 border border-space-800">
                        <div className="text-[10px] text-slate-400">Columns</div>
                        <div className="font-bold text-white text-sm">{datasetMeta.column_count}</div>
                      </div>
                      <div className="p-2.5 rounded bg-space-850 border border-space-800">
                        <div className="text-[10px] text-slate-400">Missing Cells</div>
                        <div className="font-bold text-emerald-400 text-sm">{datasetMeta.total_missing_cells}</div>
                      </div>
                      <div className="p-2.5 rounded bg-space-850 border border-space-800">
                        <div className="text-[10px] text-slate-400">Fingerprint</div>
                        <div className="font-bold text-cyan-300 text-[11px]">{datasetMeta.fingerprint}</div>
                      </div>
                    </div>

                    {/* First 5 Preview Rows */}
                    <div className="space-y-2">
                      <div className="text-xs font-mono text-slate-400">Preview (First 5 Rows):</div>
                      <div className="overflow-x-auto rounded-lg border border-space-800">
                        <table className="w-full text-[11px] font-mono text-left">
                          <thead className="bg-space-850 text-slate-400">
                            <tr>
                              {datasetMeta.headers.map((h: string, idx: number) => (
                                <th key={idx} className="p-2 border-b border-space-800">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-space-800 text-slate-300">
                            {datasetMeta.preview_rows.map((row: any, rIdx: number) => (
                              <tr key={rIdx}>
                                {datasetMeta.headers.map((h: string, cIdx: number) => (
                                  <td key={cIdx} className="p-2">{row[h]}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Preprocessing & Feature Selection Controls */}
                    <div className="p-4 rounded-xl bg-space-850 border border-space-700/80 space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white font-mono uppercase">
                          Select 4 Features for 4-Qubit VQC
                        </span>
                        <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                          selectedFeatures.length === 4 ? 'bg-emerald-950 text-emerald-300' : 'bg-amber-950 text-amber-300'
                        }`}>
                          {selectedFeatures.length} / 4 Selected
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {datasetMeta.headers.map((h: string) => {
                          const isTarget = h === selectedTarget;
                          const isSelected = selectedFeatures.includes(h);
                          return (
                            <button
                              key={h}
                              disabled={isTarget}
                              onClick={() => toggleFeature(h)}
                              className={`p-2 rounded border text-left text-xs font-mono transition-all ${
                                isTarget
                                  ? 'bg-space-950 border-space-800 text-slate-600 cursor-not-allowed'
                                  : isSelected
                                  ? 'bg-purple-500/20 border-purple-500/60 text-purple-200 font-bold'
                                  : 'bg-space-900 border-space-700/60 text-slate-400 hover:text-white'
                              }`}
                            >
                              <div className="truncate">{h}</div>
                              <div className="text-[10px] text-slate-500">
                                {isTarget ? 'TARGET LABEL' : isSelected ? '✓ ACTIVE' : '+ SELECT'}
                              </div>
                            </button>
                          );
                        })}
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 font-mono text-xs">
                        <div>
                          <label className="text-slate-400 block mb-1">Target Binary Column:</label>
                          <select
                            value={selectedTarget}
                            onChange={(e) => {
                              setSelectedTarget(e.target.value);
                              if (selectedFeatures.includes(e.target.value)) {
                                setSelectedFeatures(selectedFeatures.filter((f) => f !== e.target.value));
                              }
                            }}
                            className="w-full bg-space-900 border border-space-700 text-white rounded p-2 text-xs"
                          >
                            {datasetMeta.headers.map((h: string) => (
                              <option key={h} value={h}>{h}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="text-slate-400 block mb-1">Imputation (Fitted on Train Set):</label>
                          <select
                            value={imputationStrategy}
                            onChange={(e: any) => setImputationStrategy(e.target.value)}
                            className="w-full bg-space-900 border border-space-700 text-white rounded p-2 text-xs"
                          >
                            <option value="mean">Mean Imputation (Train Set)</option>
                            <option value="median">Median Imputation (Train Set)</option>
                            <option value="drop">Drop Incomplete Rows</option>
                          </select>
                        </div>
                      </div>

                      <button
                        onClick={handleValidateDataset}
                        disabled={isValidating || selectedFeatures.length !== 4}
                        className={`w-full py-2 rounded-lg font-mono text-xs font-bold transition-all ${
                          selectedFeatures.length === 4
                            ? 'bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/50'
                            : 'bg-space-900 border-space-800 text-slate-600 cursor-not-allowed'
                        }`}
                      >
                        {isValidating ? 'Validating Preprocessing...' : 'Validate Dataset Preprocessing'}
                      </button>

                      {validationResult && (
                        <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800 text-emerald-300 text-xs font-mono space-y-1">
                          <div className="flex items-center gap-2 font-bold">
                            <CheckCircle2 className="w-4 h-4" />
                            <span>Dataset Preprocessing Validated (Leakage-Free)</span>
                          </div>
                          <div className="text-[11px] text-slate-300">
                            Train Samples: {validationResult.train_samples_count} • Test Samples: {validationResult.test_samples_count} • Target Classes: {JSON.stringify(validationResult.target_classes)}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Quantum Model Training Section */}
              <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    Trainable Variational Quantum Classifier (SPSA)
                  </span>
                  <span className="text-[11px] font-mono text-cyan-400">4 Qubits • 2 Layers (16 Weights)</span>
                </div>

                <div className="grid grid-cols-2 gap-4 font-mono text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1">Epochs ({trainEpochs}):</label>
                    <input
                      type="range"
                      min={10}
                      max={60}
                      step={5}
                      value={trainEpochs}
                      onChange={(e) => setTrainEpochs(parseInt(e.target.value))}
                      className="w-full accent-cyan-400"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Learning Rate ({trainLr}):</label>
                    <input
                      type="range"
                      min={0.05}
                      max={0.50}
                      step={0.05}
                      value={trainLr}
                      onChange={(e) => setTrainLr(parseFloat(e.target.value))}
                      className="w-full accent-cyan-400"
                    />
                  </div>
                </div>

                <button
                  onClick={handleTrainVQC}
                  disabled={isTraining || (dataMode === 'custom' && !validationResult)}
                  className={`w-full py-2.5 rounded-xl font-bold text-xs shadow-lg transition-all ${
                    isTraining || (dataMode === 'custom' && !validationResult)
                      ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                      : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold'
                  }`}
                >
                  {isTraining ? 'Training VQC via SPSA Optimizer...' : 'Train Quantum Classifier on Ideal Simulator'}
                </button>

                {trainedModel && (
                  <div className="p-4 rounded-xl bg-space-850 border border-space-700 space-y-3 font-mono text-xs">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-cyan-300">Model: {trainedModel.model_id}</span>
                      <span className="text-emerald-400 font-bold">Train Acc: {(trainedModel.train_accuracy * 100).toFixed(1)}%</span>
                    </div>

                    <div className="h-20 w-full pt-1">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trainedModel.loss_history.map((l: number, idx: number) => ({ epoch: idx + 1, loss: l }))}>
                          <YAxis hide domain={['dataMin', 'dataMax']} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: isDark ? '#0f172a' : '#ffffff',
                              borderColor: isDark ? '#334155' : '#cbd5e1',
                              color: isDark ? '#f8fafc' : '#0f172a',
                              borderRadius: '0.5rem',
                              fontSize: '11px',
                              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                            }}
                            itemStyle={{ color: isDark ? '#f8fafc' : '#0f172a' }}
                            formatter={(val: any) => [val, 'SPSA Cross-Entropy Loss']}
                          />
                          <Line type="monotone" dataKey="loss" stroke="#38bdf8" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Right Column: Hardware & Noise Configuration (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="rounded-xl bg-space-900 border border-space-700/80 p-5 space-y-5">
            <div className="flex items-center justify-between text-slate-300">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-cyan-400" />
                Target Quantum Hardware
              </span>
              <span className="text-[11px] font-mono text-cyan-400">Organizer Topologies</span>
            </div>

            {/* Processor Selection */}
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setProcessor('A')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  processor === 'A'
                    ? 'bg-cyan-500/10 border-cyan-500/40 text-white shadow-sm'
                    : 'bg-space-850 border-space-700/60 text-slate-400 hover:border-space-600'
                }`}
              >
                <div className="text-xs font-mono font-bold">Processor A</div>
                <div className="text-[11px] text-slate-400">5-Qubit Star-Linear</div>
                <div className="text-[10px] text-cyan-400 mt-1 font-mono">16 Physical CX • 2 SWAPs</div>
              </button>

              <button
                onClick={() => setProcessor('B')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  processor === 'B'
                    ? 'bg-blue-500/10 border-blue-500/40 text-white shadow-sm'
                    : 'bg-space-850 border-space-700/60 text-slate-400 hover:border-space-600'
                }`}
              >
                <div className="text-xs font-mono font-bold">Processor B</div>
                <div className="text-[11px] text-slate-400">9-Qubit Heavy-Hex</div>
                <div className="text-[10px] text-blue-400 mt-1 font-mono">24 Physical CX • 4 SWAPs</div>
              </button>
            </div>

            {/* Noise Modeling Controls */}
            <div className="space-y-3 pt-2 border-t border-space-800">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-300">Realistic Hardware Noise</span>
                <button
                  onClick={() => setNoiseEnabled(!noiseEnabled)}
                  className={`px-3 py-1 rounded-full text-[11px] font-mono font-semibold transition-all ${
                    noiseEnabled
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : 'bg-space-850 text-slate-500 border border-space-700'
                  }`}
                >
                  {noiseEnabled ? 'NOISE ACTIVE' : 'NOISE FREE'}
                </button>
              </div>

              {noiseEnabled && (
                <div className="p-3.5 rounded-xl bg-space-850 border border-space-800 space-y-3 text-xs font-mono">
                  <div className="flex gap-2">
                    <button
                      onClick={() => setNoisePreset('calibrated')}
                      className={`flex-1 py-1 rounded text-center transition-all ${
                        noisePreset === 'calibrated' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400'
                      }`}
                    >
                      Calibrated Device
                    </button>
                    <button
                      onClick={() => setNoisePreset('custom')}
                      className={`flex-1 py-1 rounded text-center transition-all ${
                        noisePreset === 'custom' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400'
                      }`}
                    >
                      Custom Noise
                    </button>
                  </div>

                  {noisePreset === 'custom' && (
                    <div className="space-y-2 pt-1">
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400">
                          <span>CX Gate Error (p_2q)</span>
                          <span className="text-white">{(customP2q * 100).toFixed(1)}%</span>
                        </div>
                        <input
                          type="range"
                          min={0.001}
                          max={0.05}
                          step={0.001}
                          value={customP2q}
                          onChange={(e) => setCustomP2q(parseFloat(e.target.value))}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400">
                          <span>Readout Error (p_ro)</span>
                          <span className="text-white">{(customPro * 100).toFixed(1)}%</span>
                        </div>
                        <input
                          type="range"
                          min={0.005}
                          max={0.08}
                          step={0.005}
                          value={customPro}
                          onChange={(e) => setCustomPro(parseFloat(e.target.value))}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Error Mitigation Method */}
            <div className="space-y-2 pt-2 border-t border-space-800">
              <span className="text-xs font-semibold text-slate-300 block">Quantum Error Mitigation</span>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                {[
                  { id: 'none', label: 'Unmitigated', desc: 'Noisy physical baseline' },
                  { id: 'readout', label: 'Readout (REM)', desc: 'Simplex calibration inversion' },
                  { id: 'zne', label: 'ZNE Only', desc: 'Digital folding (r=1,3,5)' },
                  { id: 'dual', label: 'Dual-Layer', desc: 'ZNE + Readout (Optimal)' },
                ].map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setMitigationMethod(m.id as any)}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      mitigationMethod === m.id
                        ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-200'
                        : 'bg-space-850 border-space-700/60 text-slate-400 hover:border-space-600'
                    }`}
                  >
                    <div className="font-bold text-white text-[11px]">{m.label}</div>
                    <div className="text-[10px] text-slate-400 truncate">{m.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Sampling Parameters */}
            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-space-800 font-mono text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Shots ({shots}):</label>
                <select
                  value={shots}
                  onChange={(e) => setShots(parseInt(e.target.value))}
                  className="w-full bg-space-850 border border-space-700 text-white rounded p-1.5 text-xs"
                >
                  <option value={512}>512 shots</option>
                  <option value={1024}>1,024 shots</option>
                  <option value={2048}>2,048 shots</option>
                  <option value={4096}>4,096 shots</option>
                </select>
              </div>
              <div>
                <label className="text-slate-400 block mb-1">RNG Seed:</label>
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(parseInt(e.target.value) || 0)}
                  className="w-full bg-space-850 border border-space-700 text-white rounded p-1.5 text-xs"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
