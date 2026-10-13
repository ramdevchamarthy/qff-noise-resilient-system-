import React, { useState } from 'react';
import { Activity, Cpu, ShieldCheck, BarChart3, BookOpen, Layers, Menu, X, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'workspace', label: 'Experiment Workspace', icon: Cpu },
    { id: 'results', label: 'Results & Metrics', icon: ShieldCheck },
    { id: 'robustness', label: 'Robustness Lab', icon: BarChart3 },
    { id: 'architecture', label: 'Hardware Architectures', icon: Layers },
    { id: 'methodology', label: 'Methodology & Docs', icon: BookOpen },
  ];

  const handleSelect = (id: string) => {
    setActiveTab(id);
    setMobileOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 bg-space-900/95 backdrop-blur-md border-b border-space-700/80 px-4 sm:px-6 py-3">
      <div className="flex items-center justify-between gap-3 max-w-7xl mx-auto">
        <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
          <div className="h-8 w-8 sm:h-9 sm:w-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
            <ShieldCheck className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-bold text-xs sm:text-base tracking-tight text-white truncate">
                NOISE-RESILIENT QUANTUM SYSTEM
              </span>
              <span className="text-[10px] sm:text-[11px] font-mono px-1.5 sm:px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60 font-semibold shrink-0">
                PS-Q3
              </span>
              <span className="text-[10px] sm:text-[11px] font-mono px-1.5 sm:px-2 py-0.5 rounded bg-space-800 text-slate-400 border border-space-700 shrink-0 hidden sm:inline-block">
                QFF 2026
              </span>
            </div>
            <p className="text-[11px] sm:text-xs text-slate-400 truncate hidden md:block">
              Variational QML & Error Mitigation • Algorithm ↔ Architecture Co-Design
            </p>
          </div>
        </div>

        {/* Mobile Menu & Theme Toggle */}
        <div className="flex items-center gap-2 lg:hidden shrink-0">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg bg-space-800 border border-space-700 text-slate-300 hover:text-white hover:bg-space-700 transition-colors"
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-cyan-600" />}
          </button>
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="p-2 rounded-lg bg-space-800 border border-space-700 text-slate-300 hover:text-white hover:bg-space-700 transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Desktop Navigation & Theme Toggle */}
        <div className="hidden lg:flex items-center gap-2 shrink-0">
          <nav className="flex items-center gap-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleSelect(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-950 font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-space-800/80 border border-transparent'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
          <div className="h-5 w-px bg-space-700/80 mx-1" />
          <button
            onClick={toggleTheme}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-space-800/80 hover:bg-space-800 border border-space-700 transition-colors"
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? (
              <>
                <Sun className="w-4 h-4 text-amber-400" />
                <span className="hidden xl:inline text-slate-300 font-mono text-[11px]">Light</span>
              </>
            ) : (
              <>
                <Moon className="w-4 h-4 text-cyan-600" />
                <span className="hidden xl:inline text-slate-700 font-mono text-[11px]">Dark</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Mobile Dropdown Navigation */}
      {mobileOpen && (
        <div className="lg:hidden mt-3 pt-3 border-t border-space-800 space-y-1 pb-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleSelect(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-950 font-semibold'
                    : 'text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-space-800 border border-transparent'
                }`}
              >
                <Icon className="w-4 h-4 text-cyan-500 dark:text-cyan-400" />
                <span>{item.label}</span>
              </button>
            );
          })}
          <div className="pt-2 mt-2 border-t border-space-800">
            <button
              onClick={toggleTheme}
              className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-space-800 border border-space-700/60 transition-all"
            >
              <div className="flex items-center gap-3">
                {theme === 'dark' ? (
                  <Sun className="w-4 h-4 text-amber-400" />
                ) : (
                  <Moon className="w-4 h-4 text-cyan-600" />
                )}
                <span>Theme Mode</span>
              </div>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-space-800 text-cyan-400 border border-space-700 uppercase">
                {theme}
              </span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
