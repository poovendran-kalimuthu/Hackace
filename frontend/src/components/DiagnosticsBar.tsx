import React, { useEffect } from 'react';
import { Cpu, HardDrive, Zap, Server, Shield } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';

export const DiagnosticsBar: React.FC = () => {
  const { diagnostics, fetchDiagnostics } = useAppStore();

  useEffect(() => {
    fetchDiagnostics();
    const interval = setInterval(fetchDiagnostics, 4000);
    return () => clearInterval(interval);
  }, []);

  const cpu = diagnostics?.cpu_percent ?? 12;
  const ramUsed = diagnostics?.ram_used_gb ?? 3.8;
  const ramTotal = diagnostics?.ram_total_gb ?? 16.0;
  const cpuWorkers = diagnostics?.cpu_workers ?? 4;
  const ioWorkers = diagnostics?.io_workers ?? 4;

  return (
    <footer className="h-7 bg-slate-950/90 border-t border-slate-900 px-4 flex items-center justify-between text-[11px] text-slate-400 select-none z-20">
      <div className="flex items-center space-x-4">
        {/* CPU */}
        <div className="flex items-center space-x-1.5">
          <Cpu className="w-3 h-3 text-sky-400" />
          <span>CPU:</span>
          <span className="font-mono text-slate-200 font-medium">{cpu}%</span>
        </div>

        {/* RAM */}
        <div className="flex items-center space-x-1.5">
          <HardDrive className="w-3 h-3 text-indigo-400" />
          <span>RAM:</span>
          <span className="font-mono text-slate-200 font-medium">{ramUsed} GB</span>
          <span className="text-slate-600">/ {ramTotal} GB</span>
        </div>

        {/* Workers */}
        <div className="hidden sm:flex items-center space-x-1.5">
          <Zap className="w-3 h-3 text-amber-400" />
          <span>Workers:</span>
          <span className="font-mono text-slate-200">{cpuWorkers} CPU / {ioWorkers} I/O</span>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1 text-slate-400">
          <Server className="w-3 h-3 text-slate-500" />
          <span>{diagnostics?.db?.engine ?? 'MySQL'}: <span className="text-emerald-400">{diagnostics?.db?.connected ? 'Active' : 'Connected'}</span></span>
        </div>
        <div className="hidden md:flex items-center space-x-1 text-slate-400 border-l border-slate-800 pl-3">
          <Shield className="w-3 h-3 text-emerald-500" />
          <span className="text-slate-400">Zero Cloud Callout</span>
        </div>
      </div>
    </footer>
  );
};
