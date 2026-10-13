import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { ExperimentWorkspace } from './components/ExperimentWorkspace';
import { ResultsDashboard } from './components/ResultsDashboard';
import { RobustnessLab } from './components/RobustnessLab';
import { ArchitectureComparator } from './components/ArchitectureComparator';
import { Methodology } from './components/Methodology';

import { API_BASE } from './config';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [samples, setSamples] = useState<any[]>([]);
  const [lastResult, setLastResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Fetch initial samples from API on mount with bounded timeout
  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    fetch(`${API_BASE}/api/samples`, { signal: controller.signal })
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error('Failed to fetch samples');
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) setSamples(data);
      })
      .catch((err) => {
        console.warn('Using built-in patient samples:', err.message || err);
        setSamples([
          {
            id: 'PAT-1000',
            waveform_type: 'Normal Sinus Rhythm (N)',
            label: 0,
            features: { rr_interval_ms: 812.4, qrs_duration_ms: 84.2, r_peak_mv: 1.25, st_segment_mv: 0.01 },
            waveform: Array.from({ length: 60 }, (_, i) => ({ step: i, voltage: Math.sin(i / 10) * 0.2 })),
          },
          {
            id: 'PAT-1001',
            waveform_type: 'Premature Ventricular Contraction (PVC)',
            label: 1,
            features: { rr_interval_ms: 540.2, qrs_duration_ms: 132.5, r_peak_mv: 1.62, st_segment_mv: -0.18 },
            waveform: Array.from({ length: 60 }, (_, i) => ({ step: i, voltage: Math.sin(i / 8) * 0.4 })),
          },
        ]);
      })
      .finally(() => clearTimeout(timeoutId));

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  const handleRunExperiment = async (payload: any, isBatch: boolean = false) => {
    setIsLoading(true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    try {
      const endpoint = isBatch ? `${API_BASE}/api/experiments/evaluate_batch` : `${API_BASE}/api/experiments/run`;
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      if (res.ok) {
        const data = await res.json();
        setLastResult(data);
        setActiveTab('results');
      } else {
        const errJson = await res.json().catch(() => ({}));
        alert(`Experiment execution failed: ${errJson.detail || 'Server error'}`);
      }
    } catch (err: any) {
      console.error('Experiment request error:', err);
      if (err.name === 'AbortError') {
        alert('Quantum experiment execution timed out (45s limit reached). Please try again with fewer shots or samples.');
      } else {
        alert('Unable to reach backend API. Please ensure the backend server is reachable.');
      }
    } finally {
      clearTimeout(timeoutId);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-space-950 text-slate-100 flex flex-col font-sans overflow-x-hidden">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 p-3.5 sm:p-6 md:p-8 max-w-7xl w-full mx-auto overflow-x-hidden">
        {activeTab === 'dashboard' && (
          <Dashboard
            onStartExperiment={() => setActiveTab('workspace')}
            onExploreArchitecture={() => setActiveTab('architecture')}
          />
        )}

        {activeTab === 'workspace' && (
          <ExperimentWorkspace
            samples={samples}
            onRunExperiment={handleRunExperiment}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'results' && (
          <ResultsDashboard
            result={lastResult}
            onNavigateToRobustness={() => setActiveTab('robustness')}
            onNavigateToWorkspace={() => setActiveTab('workspace')}
          />
        )}

        {activeTab === 'robustness' && <RobustnessLab />}

        {activeTab === 'architecture' && <ArchitectureComparator />}

        {activeTab === 'methodology' && <Methodology />}
      </main>

      <footer className="border-t border-space-800 bg-space-900/60 px-6 py-4 text-center text-xs text-slate-500 font-mono">
        Qiskit Fall Fest 2026 • Track: Variational QML • Problem Statement: PS-Q3 Noise-Resilient Classifier • Built with Qiskit, FastAPI & React
      </footer>
    </div>
  );
}

export default App;
