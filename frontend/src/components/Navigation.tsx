import React from 'react';
import { BookOpen, Palette, CheckCircle2, Eye, LayoutDashboard, FileText, Cpu, ShieldCheck } from 'lucide-react';
import { useAppStore, AppView } from '../store/useAppStore';

export const Navigation: React.FC = () => {
  const { currentView, setCurrentView, activeProject } = useAppStore();

  const navItems: { id: AppView; label: string; icon: React.ElementType; disabled?: boolean }[] = [
    { id: 'dashboard', label: 'Projects', icon: LayoutDashboard },
    { id: 'project', label: 'Manuscript', icon: FileText, disabled: !activeProject },
    { id: 'review', label: 'Review Queue', icon: CheckCircle2, disabled: !activeProject },
    { id: 'preview', label: 'Book Preview', icon: Eye, disabled: !activeProject },
  ];

  return (
    <header className="h-14 glass-panel border-b border-slate-800/80 px-4 flex items-center justify-between z-30 select-none">
      {/* Brand & Active Project */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <BookOpen className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              DocuCraft <span className="text-sky-400 font-semibold text-xs px-1 py-0.5 rounded bg-sky-500/10 border border-sky-500/20">PRO</span>
            </h1>
          </div>
        </div>

        {activeProject && (
          <div className="hidden md:flex items-center space-x-2 pl-4 border-l border-slate-800 text-xs">
            <span className="text-slate-400">Current:</span>
            <span className="font-medium text-slate-200 max-w-[180px] truncate">{activeProject.name}</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
              {activeProject.page_count} pgs
            </span>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center space-x-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800/60">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              disabled={item.disabled}
              onClick={() => setCurrentView(item.id)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm'
                  : item.disabled
                  ? 'text-slate-600 cursor-not-allowed'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Offline Status Badge */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">100% Offline & Private</span>
        </div>
      </div>
    </header>
  );
};
