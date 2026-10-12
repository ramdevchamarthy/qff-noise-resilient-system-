import React from 'react';
import { Activity, Cpu, ShieldCheck, BarChart3, BookOpen, Layers } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'workspace', label: 'Experiment Workspace', icon: Cpu },
    { id: 'results', label: 'Results & Metrics', icon: ShieldCheck },
    { id: 'robustness', label: 'Robustness Lab', icon: BarChart3 },
    { id: 'architecture', label: 'Hardware Architectures', icon: Layers },
    { id: 'methodology', label: 'Methodology & Docs', icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-50 bg-space-900/90 backdrop-blur-md border-b border-space-700/80 px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-base tracking-tight text-white">NOISE-RESILIENT QUANTUM SYSTEM</span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60 font-semibold">
              PS-Q3
            </span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-space-800 text-slate-400 border border-space-700">
              QFF 2026
            </span>
          </div>
          <p className="text-xs text-slate-400">Variational QML & Error Mitigation • Algorithm ↔ Architecture Co-Design</p>
        </div>
      </div>

      <nav className="flex items-center gap-1.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-950'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-space-800/80 border border-transparent'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </header>
  );
};
