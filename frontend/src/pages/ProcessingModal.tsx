import React from 'react';
import { CheckCircle2, Circle, Loader2, Pause, Play, XCircle, AlertTriangle, Cpu, HardDrive, Zap } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

export const ProcessingModal: React.FC = () => {
  const { activeJob, setActiveJob, isProcessing, setCurrentView } = useAppStore();

  if (!activeJob || !isProcessing) return null;

  const stages = [
    { id: 'INDEXING', label: 'Reading document & building persistent SQLite index' },
    { id: 'CHUNKING', label: 'Logical chapter-aware chunking' },
    { id: 'ANALYZING', label: 'Feature extraction & parallel Random Forest ML' },
    { id: 'VALIDATING', label: 'Deterministic rule engine & heading hierarchy validation' },
    { id: 'FORMATTING', label: 'Applying template typography & smart layout pagination' },
    { id: 'EXPORTING', label: 'Pre-flight quality validation & publication DOCX generation' },
  ];

  const currentStageIndex = stages.findIndex((s) => s.id === activeJob.current_stage);

  const handlePause = async () => {
    await api.pauseJob(activeJob.job_id);
  };

  const handleResume = async () => {
    await api.resumeJob(activeJob.job_id);
  };

  const handleCancel = async () => {
    if (confirm('Cancel formatting pipeline?')) {
      await api.cancelJob(activeJob.job_id);
    }
  };

  const isPaused = activeJob.status === 'PAUSED';

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fade-in select-none">
      <div className="glass-panel w-full max-w-xl rounded-2xl p-6 border border-slate-800 shadow-2xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-sky-400">
              Pipeline Concurrency Engine
            </span>
            <h3 className="text-lg font-bold text-white flex items-center space-x-2 mt-0.5">
              <span>Processing Manuscript</span>
              {isPaused ? (
                <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-normal">
                  Paused
                </span>
              ) : (
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              )}
            </h3>
          </div>

          <div className="flex items-center space-x-2">
            {isPaused ? (
              <button
                onClick={handleResume}
                className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition"
                title="Resume"
              >
                <Play className="w-4 h-4 fill-current" />
              </button>
            ) : (
              <button
                onClick={handlePause}
                className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
                title="Pause"
              >
                <Pause className="w-4 h-4 fill-current" />
              </button>
            )}
            <button
              onClick={handleCancel}
              className="p-2 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition"
              title="Cancel Job"
            >
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Progress Bar & Chunks */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-300 font-medium">
              Overall Progress: <span className="font-mono text-sky-400">{Math.round(activeJob.progress)}%</span>
            </span>
            {activeJob.total_chunks > 0 && (
              <span className="text-slate-400 font-mono">
                Chunks: {activeJob.current_chunk} / {activeJob.total_chunks}
              </span>
            )}
          </div>

          <div className="w-full h-2.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-sky-500 to-indigo-500 transition-all duration-300 rounded-full"
              style={{ width: `${Math.max(5, activeJob.progress)}%` }}
            />
          </div>
        </div>

        {/* Stages Checklist */}
        <div className="space-y-2.5 py-1">
          {stages.map((stg, idx) => {
            const isDone = currentStageIndex > idx;
            const isCurrent = currentStageIndex === idx;

            return (
              <div
                key={stg.id}
                className={`flex items-center space-x-3 p-2 rounded-xl text-xs transition ${
                  isCurrent
                    ? 'bg-sky-500/10 border border-sky-500/20 text-sky-300 font-medium'
                    : isDone
                    ? 'text-slate-300'
                    : 'text-slate-600'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-sky-400 animate-spin flex-shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-slate-700 flex-shrink-0" />
                )}
                <span>{stg.label}</span>
              </div>
            );
          })}
        </div>

        {/* Live Diagnostics Telemetry Banner */}
        {activeJob.telemetry && (
          <div className="grid grid-cols-3 gap-2 p-3 rounded-xl bg-slate-900/90 border border-slate-800/80 text-[11px] text-slate-400">
            <div className="flex items-center space-x-1.5">
              <Cpu className="w-3.5 h-3.5 text-sky-400" />
              <span>CPU:</span>
              <span className="font-mono text-slate-200 font-semibold">
                {activeJob.telemetry.cpu_percent}%
              </span>
            </div>
            <div className="flex items-center space-x-1.5">
              <HardDrive className="w-3.5 h-3.5 text-indigo-400" />
              <span>RAM:</span>
              <span className="font-mono text-slate-200 font-semibold">
                {activeJob.telemetry.ram_used_gb} GB
              </span>
            </div>
            <div className="flex items-center space-x-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Workers:</span>
              <span className="font-mono text-slate-200 font-semibold">
                {activeJob.telemetry.cpu_workers} Proc
              </span>
            </div>
          </div>
        )}

        {/* Completion Action */}
        {activeJob.status === 'COMPLETED' && (
          <div className="pt-2 flex justify-end">
            <button
              onClick={() => {
                setActiveJob(null);
                setCurrentView('preview');
              }}
              className="px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold shadow-lg shadow-emerald-500/20 transition"
            >
              Open Book Preview
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
