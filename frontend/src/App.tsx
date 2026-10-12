import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { ExperimentWorkspace } from './components/ExperimentWorkspace';
import { ResultsDashboard } from './components/ResultsDashboard';
import { RobustnessLab } from './components/RobustnessLab';
import { ArchitectureComparator } from './components/ArchitectureComparator';
import { Methodology } from './components/Methodology';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [samples, setSamples] = useState<any[]>([]);
  const [lastResult, setLastResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Fetch initial samples from API on mount
  useEffect(() => {
    fetch('/api/samples')
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error('Failed to fetch samples');
      })
      .then((data) => setSamples(data))
      .catch((err) => {
        console.warn('Using built-in patient samples', err);
        // Fallback sample data in case API is launching
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
      });
  }, []);

  const handleRunExperiment = async (payload: any) => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/experiments/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const data = await res.json();
        setLastResult(data);
        setActiveTab('results');
      } else {
        alert('Experiment execution failed on backend.');
      }
    } catch (err) {
      console.error('Experiment request error:', err);
      alert('Unable to reach backend API. Ensure server is running on http://127.0.0.1:8000.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-space-950 text-slate-100 flex flex-col font-sans">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 p-6 md:p-8">
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
