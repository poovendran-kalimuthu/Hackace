import React, { useEffect, useRef, useState } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle,
  AlertTriangle,
  Layers,
  BookOpen,
  Play,
  Eye,
  Image as ImageIcon,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Hash
} from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

export const ProjectView: React.FC = () => {
  const { activeProject, selectProject, templates, setCurrentView, setActiveJob, loadProjects } = useAppStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logoInputRef = useRef<HTMLInputElement>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(activeProject?.template_id || 'book');
  const [isStartingJob, setIsStartingJob] = useState(false);

  // Logo state
  const [logoAsset, setLogoAsset] = useState<any | null>(null);
  const [isUploadingLogo, setIsUploadingLogo] = useState(false);
  const [logoError, setLogoError] = useState<string | null>(null);

  useEffect(() => {
    if (activeProject) {
      fetchLogo();
    }
  }, [activeProject?.id]);

  const fetchLogo = async () => {
    if (!activeProject) return;
    try {
      const res = await api.getLogo(activeProject.id);
      if (res.has_logo) {
        setLogoAsset(res.logo);
      } else {
        setLogoAsset(null);
      }
    } catch (e) {
      console.error('Failed to fetch logo', e);
    }
  };

  if (!activeProject) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-center text-slate-400">
        <p>No active project selected. Return to Dashboard to select or create a project.</p>
      </div>
    );
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      await api.uploadManuscript(activeProject.id, file);
      const updated = await api.getProject(activeProject.id);
      selectProject(updated);
      await loadProjects();
    } catch (err: any) {
      alert(err?.message || 'Failed to upload and scan manuscript.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingLogo(true);
    setLogoError(null);
    try {
      const res = await api.uploadLogo(activeProject.id, file);
      setLogoAsset(res.logo);
    } catch (err: any) {
      setLogoError(err?.message || 'Invalid logo asset. Must be PNG/JPG, min 100x100px, max 5MB.');
    } finally {
      setIsUploadingLogo(false);
    }
  };

  const handleStartFormatting = async () => {
    if (!logoAsset || !logoAsset.is_valid) {
      alert('A valid publisher / book logo is required before formatting.');
      return;
    }

    setIsStartingJob(true);
    try {
      const res = await api.startJob(activeProject.id, selectedTemplate);
      const jobStatus = await api.getJobStatus(res.job_id);
      setActiveJob(jobStatus);
    } catch (err: any) {
      alert(err?.message || 'Failed to start formatting pipeline.');
    } finally {
      setIsStartingJob(false);
    }
  };

  const hasValidLogo = !!(logoAsset && logoAsset.is_valid);

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 max-w-6xl mx-auto w-full">
      {/* Project Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/20 text-sky-400 font-medium">
              Project Workspace
            </span>
            <span className="text-slate-500 text-xs">•</span>
            <span className="text-xs text-slate-400 font-mono">{activeProject.id}</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">{activeProject.name}</h1>
          <p className="text-xs text-slate-400 mt-1">{activeProject.description || 'No description provided.'}</p>
        </div>

        {activeProject.source_filename && (
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setCurrentView('preview')}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
            >
              <Eye className="w-4 h-4 text-slate-400" />
              <span>Preview</span>
            </button>
            <button
              onClick={handleStartFormatting}
              disabled={isStartingJob || !hasValidLogo}
              title={!hasValidLogo ? 'Upload a publisher logo to enable formatting' : ''}
              className={`flex items-center space-x-2 px-5 py-2 rounded-xl text-white text-xs font-semibold shadow-lg transition active:scale-95 ${
                hasValidLogo
                  ? 'bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 shadow-sky-500/25 cursor-pointer'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
              }`}
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{isStartingJob ? 'Initiating Pipeline...' : 'Format Book Now'}</span>
            </button>
          </div>
        )}
      </div>

      {/* Upload Dropzone */}
      {!activeProject.source_filename ? (
        <div
          onClick={() => fileInputRef.current?.click()}
          className="glass-card rounded-2xl p-12 text-center border-2 border-dashed border-slate-700/80 hover:border-sky-500/60 cursor-pointer transition group"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".docx"
            className="hidden"
          />
          <div className="w-16 h-16 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 mx-auto mb-4 group-hover:scale-105 transition">
            <UploadCloud className="w-8 h-8" />
          </div>
          <h3 className="text-base font-bold text-slate-100">
            {isUploading ? 'Scanning Manuscript...' : 'Drop Microsoft Word (.docx) Here'}
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">
            Supports documents from 100 to 10,000+ pages with zero cloud dependencies.
          </p>
          <button
            disabled={isUploading}
            className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-white text-xs font-medium inline-flex items-center space-x-2 shadow-md shadow-sky-500/20 transition"
          >
            <FileText className="w-4 h-4" />
            <span>Browse Manuscript File</span>
          </button>
        </div>
      ) : (
        /* Structural Analysis Summary Cards & Configuration */
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-200 flex items-center space-x-2">
              <Layers className="w-4 h-4 text-sky-400" />
              <span>Manuscript Structural Intelligence</span>
            </h2>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="text-xs text-slate-400 hover:text-sky-400 transition"
            >
              Replace Manuscript
            </button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".docx"
              className="hidden"
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="glass-card rounded-xl p-4 border border-slate-800">
              <span className="text-[11px] text-slate-400">Estimated Pages</span>
              <p className="text-2xl font-bold text-white font-mono mt-1">
                {activeProject.page_count.toLocaleString()}
              </p>
              <span className="text-[10px] text-slate-500 mt-0.5 block">@ ~280 words / page</span>
            </div>

            <div className="glass-card rounded-xl p-4 border border-slate-800">
              <span className="text-[11px] text-slate-400">Total Word Count</span>
              <p className="text-2xl font-bold text-slate-200 font-mono mt-1">
                {activeProject.word_count.toLocaleString()}
              </p>
              <span className="text-[10px] text-emerald-400 mt-0.5 block">100% Extracted</span>
            </div>

            <div className="glass-card rounded-xl p-4 border border-slate-800">
              <span className="text-[11px] text-slate-400">Detected Chapters</span>
              <p className="text-2xl font-bold text-sky-400 font-mono mt-1">
                {activeProject.chapter_count}
              </p>
              <span className="text-[10px] text-slate-500 mt-0.5 block">Structural boundaries</span>
            </div>

            <div className="glass-card rounded-xl p-4 border border-slate-800">
              <span className="text-[11px] text-slate-400">Source Document</span>
              <p className="text-xs font-semibold text-slate-300 truncate mt-1.5">
                {activeProject.source_filename}
              </p>
              <span className="text-[10px] text-sky-400 mt-1 block">Indexed in SQLite</span>
            </div>
          </div>

          {/* SECTION 5: Mandatory Publisher / Book Logo Upload */}
          <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${
                  hasValidLogo ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                }`}>
                  <ImageIcon className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-semibold text-slate-100">Publisher / Book Logo</h3>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/30 text-amber-300">
                      Required
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Strict publication specifications: PNG, JPG, or JPEG (min 100×100px, max 5MB). Placed on title page.
                  </p>
                </div>
              </div>

              <div>
                <input
                  type="file"
                  ref={logoInputRef}
                  onChange={handleLogoUpload}
                  accept="image/png, image/jpeg, image/jpg"
                  className="hidden"
                />
                <button
                  type="button"
                  disabled={isUploadingLogo}
                  onClick={() => logoInputRef.current?.click()}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-medium border transition ${
                    hasValidLogo
                      ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
                      : 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border-amber-500/40 font-semibold'
                  }`}
                >
                  <UploadCloud className="w-3.5 h-3.5" />
                  <span>{isUploadingLogo ? 'Validating Logo...' : hasValidLogo ? 'Replace Logo' : 'Upload Required Logo'}</span>
                </button>
              </div>
            </div>

            {/* Logo Validation Status Banner */}
            {hasValidLogo ? (
              <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                <div className="flex items-center space-x-2 text-emerald-400 font-medium">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>✓ Valid logo: {logoAsset.filename} ({logoAsset.width}×{logoAsset.height} px, {(logoAsset.file_size_bytes / 1024).toFixed(1)} KB)</span>
                </div>
                <div className="flex items-center space-x-1.5 text-slate-400 text-[11px] font-mono">
                  <Hash className="w-3 h-3 text-slate-500" />
                  <span>SHA256: {logoAsset.sha256?.substring(0, 12)}...</span>
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 flex items-center justify-between text-xs text-amber-300">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                  <span>
                    {logoError ? `✕ Invalid logo — ${logoError}` : '✕ Missing publisher logo — Publication formatting requires a verified publisher logo.'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Human-in-the-loop Review Queue Banner */}
          <div className="glass-card rounded-xl p-4 border border-slate-800 bg-slate-900/40 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-200">Human-in-the-Loop Review Queue Available</h4>
                <p className="text-[11px] text-slate-400">
                  Inspect elements where ML confidence was lower or deterministic disambiguation took place.
                </p>
              </div>
            </div>
            <button
              onClick={() => setCurrentView('review')}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition"
            >
              Open Review Queue
            </button>
          </div>

          {/* SECTIONS 4 & 8: Three JSON Publication Templates */}
          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-200 flex items-center space-x-2">
                  <BookOpen className="w-4 h-4 text-indigo-400" />
                  <span>Select Publication Template (JSON Presets)</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Pre-configured with Times New Roman 12pt, 1.5 Line Spacing, and 1.27 cm First-Line Indent.
                </p>
              </div>
              <span className="text-[11px] font-mono text-slate-500">3 Verified Presets</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {templates.map((tpl) => {
                const isSel = selectedTemplate === tpl.id;
                return (
                  <div
                    key={tpl.id}
                    onClick={() => setSelectedTemplate(tpl.id)}
                    className={`glass-card rounded-xl p-5 cursor-pointer transition border flex flex-col justify-between ${
                      isSel
                        ? 'border-sky-500/80 bg-sky-500/10 shadow-lg shadow-sky-500/15'
                        : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-sky-400">
                          {tpl.category}
                        </span>
                        {isSel && <CheckCircle className="w-4 h-4 text-sky-400" />}
                      </div>
                      <h3 className="font-semibold text-slate-100 text-sm">{tpl.name}</h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">{tpl.description}</p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
                      <span>{tpl.page.width}" × {tpl.page.height}"</span>
                      <span className="text-slate-300 font-serif font-medium">
                        Times New Roman 12pt
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
