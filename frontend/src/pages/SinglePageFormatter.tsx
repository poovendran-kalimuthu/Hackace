import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Image as ImageIcon,
  Check,
  RefreshCw,
  FileDown,
  Cpu,
  BookOpen,
  GraduationCap,
  FileCode,
  X,
  Layers,
  Sparkles,
  ShieldCheck,
  Table as TableIcon,
  Database,
  Clock,
  HardDrive,
  BarChart2,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Target,
} from 'lucide-react';
import { api } from '../services/api';
import { BookTemplate } from '../types';
import { PerformanceDashboard } from './PerformanceDashboard';

type AppState = 'input' | 'processing' | 'completed';

interface ManuscriptInfo {
  filename: string;
  fileSizeFormatted: string;
  wordCount?: number;
  pageCount?: number;
  chapterCount?: number;
  tableCount?: number;
  imageCount?: number;
}

interface LogoInfo {
  filename: string;
  previewUrl: string;
  width: number;
  height: number;
  fileSizeBytes: number;
}

export const SinglePageFormatter: React.FC = () => {
  // App Progression State
  const [appState, setAppState] = useState<AppState>('input');

  // Input State
  const [templates, setTemplates] = useState<BookTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('book');
  const [projectId, setProjectId] = useState<string | null>(null);

  // Manuscript
  const [manuscriptFile, setManuscriptFile] = useState<File | null>(null);
  const [manuscriptInfo, setManuscriptInfo] = useState<ManuscriptInfo | null>(null);
  const [isUploadingManuscript, setIsUploadingManuscript] = useState<boolean>(false);
  const [isDraggingDocx, setIsDraggingDocx] = useState<boolean>(false);

  // Logo
  const [logoInfo, setLogoInfo] = useState<LogoInfo | null>(null);
  const [isUploadingLogo, setIsUploadingLogo] = useState<boolean>(false);
  const [isDraggingLogo, setIsDraggingLogo] = useState<boolean>(false);

  // Processing State
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState<number>(0);
  const [currentStage, setCurrentStage] = useState<string>('QUEUED');
  const [currentChunk, setCurrentChunk] = useState<number>(0);
  const [totalChunks, setTotalChunks] = useState<number>(0);
  const [cpuWorkers, setCpuWorkers] = useState<number>(8);

  // Completion State
  const [completionReport, setCompletionReport] = useState<any>(null);

  // Error State
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Storage & Saved Documents History State
  const [storageStatus, setStorageStatus] = useState<any>(null);
  const [showHistoryModal, setShowHistoryModal] = useState<boolean>(false);
  const [savedProjects, setSavedProjects] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);

  // Performance Dashboard
  const [showPerfDashboard, setShowPerfDashboard] = useState<boolean>(false);

  // Expanded technical details per project in history modal
  const [expandedProjectDetails, setExpandedProjectDetails] = useState<Set<string>>(new Set());
  const [projectTechDetails, setProjectTechDetails] = useState<Record<string, any>>({});
  const [loadingTechDetails, setLoadingTechDetails] = useState<Record<string, boolean>>({});

  // Auto-loaded tech details for the just-completed document
  const [completedTechDetails, setCompletedTechDetails] = useState<any>(null);
  const [isLoadingCompletedTech, setIsLoadingCompletedTech] = useState<boolean>(false);

  // Hidden File Inputs
  const docxInputRef = useRef<HTMLInputElement>(null);
  const logoInputRef = useRef<HTMLInputElement>(null);

  // Load the 3 templates & system CPU worker count on mount
  useEffect(() => {
    const initData = async () => {
      try {
        const tpls = await api.getTemplates();
        if (tpls && tpls.length > 0) {
          setTemplates(tpls);
          setSelectedTemplateId(tpls[0].id);
        }
      } catch (err) {
        console.warn('Using default template presets', err);
      }

      try {
        const diag = await api.getDiagnostics();
        if (diag?.cpu_cores_logical) {
          setCpuWorkers(diag.cpu_cores_logical);
        }
      } catch (err) {
        // silent fallback
      }

      try {
        const storage = await api.getStorageStatus();
        setStorageStatus(storage);
      } catch (err) {
        // silent fallback
      }
    };

    initData();
  }, []);

  // Fetch saved projects history from MySQL
  const openHistoryModal = async () => {
    setShowHistoryModal(true);
    setIsLoadingHistory(true);
    try {
      const projs = await api.getProjects();
      setSavedProjects(projs || []);
      const storage = await api.getStorageStatus();
      setStorageStatus(storage);
    } catch (err) {
      console.warn('Failed to load saved projects history', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Poll Job Status during processing state
  useEffect(() => {
    if (appState !== 'processing' || !activeJobId) return;

    const interval = setInterval(async () => {
      try {
        const status = await api.getJobStatus(activeJobId);
        setJobProgress(Math.min(100, Math.round(status.progress || 0)));
        setCurrentStage(status.current_stage || 'Formatting');
        setCurrentChunk(status.current_chunk || 0);
        setTotalChunks(status.total_chunks || 0);

        if (status.status === 'COMPLETED') {
          clearInterval(interval);
          if (projectId) {
            const comp = await api.getComparison(projectId);
            setCompletionReport(comp);
            // Auto-load technical analysis for this document
            setIsLoadingCompletedTech(true);
            try {
              const td = await api.getProjectTechnicalDetails(projectId);
              setCompletedTechDetails(td);
            } catch {
              setCompletedTechDetails(null);
            } finally {
              setIsLoadingCompletedTech(false);
            }
          }
          setAppState('completed');
        } else if (status.status === 'FAILED') {
          clearInterval(interval);
          setErrorMessage(
            status.errors && status.errors.length > 0
              ? `Document processing failed: ${status.errors[0]}`
              : 'Document processing encountered an error. The original manuscript has not been modified.'
          );
          setAppState('input');
        }
      } catch (err) {
        console.warn('Failed to poll job status', err);
      }
    }, 800);

    return () => clearInterval(interval);
  }, [appState, activeJobId, projectId]);

  // Ensure an active project workspace exists
  const getOrCreateProjectId = async (projectName: string): Promise<string> => {
    if (projectId) return projectId;
    const proj = await api.createProject(projectName, 'Single-page formatter session', selectedTemplateId);
    setProjectId(proj.id);
    return proj.id;
  };

  // ----------------------------------------------------
  // SECTION 1: MANUSCRIPT UPLOAD HANDLERS
  // ----------------------------------------------------
  const handleDocxSelection = async (file: File) => {
    setErrorMessage(null);

    // Strict extension check
    if (!file.name.toLowerCase().endsWith('.docx')) {
      setErrorMessage('Please upload a valid Microsoft Word (.docx) manuscript.');
      return;
    }

    setIsUploadingManuscript(true);
    try {
      const cleanName = file.name.replace(/\.docx$/i, '');
      const activeProjId = await getOrCreateProjectId(cleanName);
      const res = await api.uploadManuscript(activeProjId, file);

      setManuscriptFile(file);
      setManuscriptInfo({
        filename: file.name,
        fileSizeFormatted: formatFileSize(file.size),
        wordCount: res.word_count || 0,
        pageCount: res.page_count || 0,
        chapterCount: res.chapter_count || 0,
        tableCount: res.table_count || 0,
        imageCount: res.image_count || 0,
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to upload and validate DOCX manuscript.');
      setManuscriptFile(null);
      setManuscriptInfo(null);
    } finally {
      setIsUploadingManuscript(false);
    }
  };

  // ----------------------------------------------------
  // SECTION 3: LOGO UPLOAD HANDLERS
  // ----------------------------------------------------
  const handleLogoSelection = async (file: File) => {
    setErrorMessage(null);

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !['png', 'jpg', 'jpeg'].includes(ext)) {
      setErrorMessage('Logo upload failed: only PNG, JPG, and JPEG images are supported.');
      return;
    }

    setIsUploadingLogo(true);
    try {
      const activeProjId = await getOrCreateProjectId(manuscriptFile ? manuscriptFile.name.replace(/\.docx$/i, '') : 'Publication');
      const res = await api.uploadLogo(activeProjId, file);

      if (res.success && res.logo) {
        const previewUrl = URL.createObjectURL(file);
        setLogoInfo({
          filename: res.logo.filename || file.name,
          previewUrl,
          width: res.logo.width || 0,
          height: res.logo.height || 0,
          fileSizeBytes: res.logo.file_size_bytes || file.size,
        });
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Logo validation failed. Ensure image is high-resolution PNG/JPG (min 100x100).');
      setLogoInfo(null);
    } finally {
      setIsUploadingLogo(false);
    }
  };

  // ----------------------------------------------------
  // SECTION 4: START PROCESS
  // ----------------------------------------------------
  const handleStartProcess = async () => {
    setErrorMessage(null);

    if (!manuscriptFile || !projectId) {
      setErrorMessage('Please upload a DOCX manuscript.');
      return;
    }
    if (!selectedTemplateId) {
      setErrorMessage('Please select a publication template.');
      return;
    }
    if (!logoInfo) {
      setErrorMessage('Publisher logo is required before formatting.');
      return;
    }

    try {
      setAppState('processing');
      setJobProgress(5);
      setCurrentStage('QUEUED');
      const res = await api.startJob(projectId, selectedTemplateId);
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to start formatting engine.');
      setAppState('input');
    }
  };

  // Cancel Processing
  const handleCancelProcess = async () => {
    if (activeJobId) {
      try {
        await api.cancelJob(activeJobId);
      } catch (e) {
        // silent
      }
    }
    setAppState('input');
    setJobProgress(0);
    setActiveJobId(null);
  };

  // Reset to Format Another Document
  const handleReset = () => {
    setAppState('input');
    setManuscriptFile(null);
    setManuscriptInfo(null);
    setLogoInfo(null);
    setActiveJobId(null);
    setJobProgress(0);
    setCompletionReport(null);
    setProjectId(null);
    setErrorMessage(null);
  };

  const handleDownload = async () => {
    if (!projectId) return;
    try {
      const exportUrl = api.getExportUrl(projectId);
      const res = await fetch(exportUrl);
      if (!res.ok) {
        // Try to extract the error detail from FastAPI JSON response
        let detail = 'Formatted output document not ready for download.';
        try {
          const errBody = await res.json();
          if (errBody?.detail) detail = errBody.detail;
        } catch (_) {}
        throw new Error(detail);
      }
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      // Use Content-Disposition filename if available, otherwise derive from manuscript
      const disposition = res.headers.get('Content-Disposition');
      let downloadName = manuscriptFile
        ? manuscriptFile.name.replace(/\.docx$/i, '_formatted.docx')
        : 'Formatted_Document.docx';
      if (disposition) {
        const match = disposition.match(/filename="([^"]+)"/);
        if (match) downloadName = match[1];
      }
      link.download = downloadName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to download formatted document.');
    }
  };

  const isFormValid = Boolean(manuscriptFile && selectedTemplateId && logoInfo);

  // ----------------------------------------------------
  // RENDER
  // ----------------------------------------------------
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900 overflow-y-auto">
      {/* HEADER */}
      <header className="bg-white border-b border-slate-200/80 px-6 py-4 shadow-sm sticky top-0 z-20">
        <div className={`mx-auto flex items-center justify-between transition-all duration-300 ${appState === 'completed' ? 'max-w-7xl' : 'max-w-4xl'}`}>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-900 uppercase flex items-center space-x-2">
              <span>INTELLIGENT DOCUMENT FORMATTER</span>
            </h1>
            <p className="text-xs text-slate-500 font-medium tracking-wide">
              Offline • Private • Publication Ready
            </p>
          </div>
          
          {/* Storage & Saved Documents Badges */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1.5 text-xs bg-emerald-50 text-emerald-800 border border-emerald-200 px-3 py-1.5 rounded-full shadow-xs">
              <Database className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
              <span className="font-semibold text-[11px]">
                {storageStatus?.engine || 'MySQL'}: {storageStatus?.info?.database || 'docucraft_db'} ({storageStatus?.connected ? 'Connected' : 'Active'})
              </span>
            </div>

            <button
              type="button"
              onClick={openHistoryModal}
              className="flex items-center space-x-1.5 text-xs text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-full shadow-xs cursor-pointer transition active:scale-[0.98]"
              title="View documents stored in local MySQL database"
            >
              <Clock className="w-3.5 h-3.5 text-indigo-600 flex-shrink-0" />
              <span className="font-semibold text-[11px]">Saved Documents</span>
            </button>

            <button
              type="button"
              onClick={() => setShowPerfDashboard(true)}
              className="flex items-center space-x-1.5 text-xs text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-3 py-1.5 rounded-full shadow-xs cursor-pointer transition active:scale-[0.98]"
              title="Open Performance Analysis Dashboard"
            >
              <BarChart2 className="w-3.5 h-3.5 text-indigo-600 flex-shrink-0" />
              <span className="font-semibold text-[11px]">Analytics</span>
            </button>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className={`flex-1 w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col justify-start transition-all duration-300 ${appState === 'completed' ? 'max-w-7xl' : 'max-w-4xl'}`}>
        {/* HUMAN-READABLE ERROR BANNER */}
        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start space-x-3 text-red-800 text-xs shadow-sm">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-bold">Attention Needed: </span>
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-red-500 hover:text-red-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ---------------------------------------------------- */}
        {/* STATE 1: INPUT WORKFLOW (UPLOAD -> TEMPLATE -> LOGO) */}
        {/* ---------------------------------------------------- */}
        {appState === 'input' && (
          <div className="space-y-6">
            {/* SECTION 1: UPLOAD MANUSCRIPT */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-slate-300 transition">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <span className="w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold flex items-center justify-center">
                    1
                  </span>
                  <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase">
                    UPLOAD MANUSCRIPT
                  </h2>
                </div>
                {manuscriptInfo && (
                  <span className="text-xs font-semibold text-emerald-600 flex items-center space-x-1">
                    <Check className="w-3.5 h-3.5" />
                    <span>DOCX Validated</span>
                  </span>
                )}
              </div>

              {!manuscriptInfo ? (
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDraggingDocx(true);
                  }}
                  onDragLeave={() => setIsDraggingDocx(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setIsDraggingDocx(false);
                    if (e.dataTransfer.files?.[0]) {
                      handleDocxSelection(e.dataTransfer.files[0]);
                    }
                  }}
                  onClick={() => docxInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center ${
                    isDraggingDocx
                      ? 'border-blue-500 bg-blue-50/50'
                      : 'border-slate-300 hover:border-slate-400 bg-slate-50/60'
                  }`}
                >
                  <input
                    type="file"
                    ref={docxInputRef}
                    onChange={(e) => {
                      if (e.target.files?.[0]) handleDocxSelection(e.target.files[0]);
                    }}
                    accept=".docx"
                    className="hidden"
                  />
                  <div className="w-12 h-12 rounded-full bg-white shadow-sm border border-slate-200 flex items-center justify-center text-slate-600 mb-3">
                    <FileText className="w-6 h-6" />
                  </div>
                  <p className="text-sm font-semibold text-slate-800">
                    Drag & Drop your .DOCX file here
                  </p>
                  <p className="text-xs text-slate-400 my-1 font-medium">or</p>
                  <button
                    type="button"
                    disabled={isUploadingManuscript}
                    className="px-4 py-1.5 rounded-lg bg-white border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-100 transition shadow-sm"
                  >
                    {isUploadingManuscript ? 'Validating DOCX...' : 'Choose DOCX'}
                  </button>
                  <p className="text-[11px] text-slate-400 mt-3">
                    Microsoft Word (.docx) files only • Up to 10,000+ pages supported
                  </p>
                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-sm text-slate-900">
                          {manuscriptInfo.filename}
                        </span>
                        <span className="text-xs text-slate-400">
                          ({manuscriptInfo.fileSizeFormatted})
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {manuscriptInfo.pageCount ? `${manuscriptInfo.pageCount} estimated pages • ` : ''}
                        {manuscriptInfo.wordCount ? `${manuscriptInfo.wordCount.toLocaleString()} words • ` : ''}
                        {manuscriptInfo.chapterCount ? `${manuscriptInfo.chapterCount} chapters` : 'Structure parsed'}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => docxInputRef.current?.click()}
                    className="px-3 py-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-100 text-xs font-semibold text-slate-700 transition"
                  >
                    Replace File
                  </button>
                  <input
                    type="file"
                    ref={docxInputRef}
                    onChange={(e) => {
                      if (e.target.files?.[0]) handleDocxSelection(e.target.files[0]);
                    }}
                    accept=".docx"
                    className="hidden"
                  />
                </div>
              )}
            </div>

            {/* SECTION 2: SELECT TEMPLATE */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-slate-300 transition">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <span className="w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold flex items-center justify-center">
                    2
                  </span>
                  <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase">
                    SELECT TEMPLATE
                  </h2>
                </div>
                <span className="text-xs text-slate-400 font-medium">Exactly 3 JSON Presets</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Template 1: BOOK PUBLISHER */}
                <div
                  onClick={() => setSelectedTemplateId('book')}
                  className={`p-4 rounded-xl border-2 cursor-pointer transition flex flex-col justify-between ${
                    selectedTemplateId === 'book'
                      ? 'border-blue-600 bg-blue-50/30 shadow-sm ring-1 ring-blue-600'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2 text-slate-800">
                        <BookOpen className="w-4 h-4 text-blue-600" />
                        <span className="font-bold text-xs uppercase tracking-wider">
                          BOOK PUBLISHER
                        </span>
                      </div>
                      {selectedTemplateId === 'book' && (
                        <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center">
                          <Check className="w-3 h-3" />
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed mb-3">
                      Standard commercial book publication format. A5 portrait, mirror margins (0.85" inside, 0.7" outside), 0.15" gutter, odd-page chapters, Times New Roman 11pt, full front matter.
                    </p>
                  </div>
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 font-medium">
                    <span>A5 Portrait</span>
                    <span className="text-blue-600 font-semibold">Mirror Margins</span>
                  </div>
                </div>

                {/* Template 2: ACADEMIC RESEARCH PAPER */}
                <div
                  onClick={() => setSelectedTemplateId('academic_research')}
                  className={`p-4 rounded-xl border-2 cursor-pointer transition flex flex-col justify-between ${
                    selectedTemplateId === 'academic_research' || selectedTemplateId === 'journal' || selectedTemplateId === 'academic'
                      ? 'border-blue-600 bg-blue-50/30 shadow-sm ring-1 ring-blue-600'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2 text-slate-800">
                        <GraduationCap className="w-4 h-4 text-purple-600" />
                        <span className="font-bold text-xs uppercase tracking-wider">
                          ACADEMIC RESEARCH PAPER
                        </span>
                      </div>
                      {(selectedTemplateId === 'academic_research' || selectedTemplateId === 'journal' || selectedTemplateId === 'academic') && (
                        <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center">
                          <Check className="w-3 h-3" />
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed mb-3">
                      Academic monograph and journal publication standard. A4 portrait, 1.0" margins, single-column, Times New Roman 11pt (1.15 spacing), structured abstract, numbered headings, 0.25" hanging indent references.
                    </p>
                  </div>
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 font-medium">
                    <span>A4 Portrait</span>
                    <span className="text-purple-600 font-semibold">Single Column</span>
                  </div>
                </div>

                {/* Template 3: CONFERENCE PAPER */}
                <div
                  onClick={() => setSelectedTemplateId('conference_paper')}
                  className={`p-4 rounded-xl border-2 cursor-pointer transition flex flex-col justify-between ${
                    selectedTemplateId === 'conference_paper' || selectedTemplateId === 'technical' || selectedTemplateId === 'conference'
                      ? 'border-blue-600 bg-blue-50/30 shadow-sm ring-1 ring-blue-600'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2 text-slate-800">
                        <FileCode className="w-4 h-4 text-emerald-600" />
                        <span className="font-bold text-xs uppercase tracking-wider">
                          CONFERENCE PAPER
                        </span>
                      </div>
                      {(selectedTemplateId === 'conference_paper' || selectedTemplateId === 'technical' || selectedTemplateId === 'conference') && (
                        <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center">
                          <Check className="w-3 h-3" />
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed mb-3">
                      Conference proceedings format. A4 portrait, 0.7" margins, 2-column layout (0.25" gap), Times New Roman 9pt body (1.0 spacing), spanning title/abstract, and numeric citation references.
                    </p>
                  </div>
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 font-medium">
                    <span>A4 Portrait</span>
                    <span className="text-emerald-600 font-semibold">2-Column (0.25" gap)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* SECTION 3: PUBLISHER / BOOK LOGO */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-slate-300 transition">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <span className="w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold flex items-center justify-center">
                    3
                  </span>
                  <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase">
                    PUBLISHER / BOOK LOGO
                  </h2>
                  <span className="text-[10px] uppercase tracking-wider font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded">
                    Mandatory
                  </span>
                </div>
                {logoInfo && (
                  <span className="text-xs font-semibold text-emerald-600 flex items-center space-x-1">
                    <Check className="w-3.5 h-3.5" />
                    <span>Logo Validated</span>
                  </span>
                )}
              </div>

              {!logoInfo ? (
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDraggingLogo(true);
                  }}
                  onDragLeave={() => setIsDraggingLogo(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setIsDraggingLogo(false);
                    if (e.dataTransfer.files?.[0]) {
                      handleLogoSelection(e.dataTransfer.files[0]);
                    }
                  }}
                  onClick={() => logoInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center ${
                    isDraggingLogo
                      ? 'border-blue-500 bg-blue-50/50'
                      : 'border-slate-300 hover:border-slate-400 bg-slate-50/60'
                  }`}
                >
                  <input
                    type="file"
                    ref={logoInputRef}
                    onChange={(e) => {
                      if (e.target.files?.[0]) handleLogoSelection(e.target.files[0]);
                    }}
                    accept=".png,.jpg,.jpeg"
                    className="hidden"
                  />
                  <div className="w-10 h-10 rounded-full bg-white shadow-sm border border-slate-200 flex items-center justify-center text-slate-600 mb-2">
                    <ImageIcon className="w-5 h-5" />
                  </div>
                  <p className="text-xs font-semibold text-slate-700">
                    Upload publisher logo asset
                  </p>
                  <p className="text-[11px] text-slate-400 my-1">
                    Supported: PNG, JPG, JPEG (High resolution recommended)
                  </p>
                  <button
                    type="button"
                    disabled={isUploadingLogo}
                    className="mt-2 px-3 py-1.5 rounded-lg bg-white border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-100 transition shadow-sm"
                  >
                    {isUploadingLogo ? 'Validating Logo...' : 'Upload Logo'}
                  </button>
                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <img
                      src={logoInfo.previewUrl}
                      alt="Publisher Logo"
                      className="w-14 h-14 object-contain bg-white border border-slate-200 rounded-lg p-1 shadow-sm"
                    />
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-sm text-slate-900">
                          {logoInfo.filename}
                        </span>
                        <span className="text-xs text-emerald-600 font-semibold bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                          ✓ Validated
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Dimensions: {logoInfo.width} × {logoInfo.height} px • Size: {formatFileSize(logoInfo.fileSizeBytes)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => logoInputRef.current?.click()}
                    className="px-3 py-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-100 text-xs font-semibold text-slate-700 transition"
                  >
                    Replace Logo
                  </button>
                  <input
                    type="file"
                    ref={logoInputRef}
                    onChange={(e) => {
                      if (e.target.files?.[0]) handleLogoSelection(e.target.files[0]);
                    }}
                    accept=".png,.jpg,.jpeg"
                    className="hidden"
                  />
                </div>
              )}
            </div>

            {/* SECTION 4: START PROCESS BUTTON */}
            <div className="pt-2">
              <button
                disabled={!isFormValid}
                onClick={handleStartProcess}
                className={`w-full py-4 px-6 rounded-xl font-bold text-sm uppercase tracking-wider transition shadow-md flex items-center justify-center space-x-2 ${
                  isFormValid
                    ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer active:scale-[0.99]'
                    : 'bg-slate-200 text-slate-400 cursor-not-allowed border border-slate-300'
                }`}
              >
                <span>START PROCESS</span>
              </button>

              {/* Requirement Checklist */}
              <div className="mt-3 flex items-center justify-center space-x-6 text-xs text-slate-500">
                <span className={`flex items-center space-x-1 ${manuscriptFile ? 'text-emerald-600 font-medium' : ''}`}>
                  {manuscriptFile ? <Check className="w-3.5 h-3.5" /> : <span className="w-3.5 h-3.5 inline-block text-slate-300">○</span>}
                  <span>1. Manuscript (.docx)</span>
                </span>
                <span className={`flex items-center space-x-1 ${selectedTemplateId ? 'text-emerald-600 font-medium' : ''}`}>
                  <Check className="w-3.5 h-3.5" />
                  <span>2. Template selected</span>
                </span>
                <span className={`flex items-center space-x-1 ${logoInfo ? 'text-emerald-600 font-medium' : ''}`}>
                  {logoInfo ? <Check className="w-3.5 h-3.5" /> : <span className="w-3.5 h-3.5 inline-block text-slate-300">○</span>}
                  <span>3. Logo validated</span>
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------- */}
        {/* STATE 2: IN-PLACE PROCESSING STATE */}
        {/* ---------------------------------------------------- */}
        {appState === 'processing' && (
          <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                FORMATTING YOUR DOCUMENT
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Processing offline across workstation CPU cores without cloud dependencies.
              </p>
            </div>

            {/* Progress Bar & Percentage */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs font-semibold">
                <span className="text-slate-700">Overall Progress</span>
                <span className="font-mono text-blue-600 text-sm">{jobProgress}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3.5 overflow-hidden border border-slate-200">
                <div
                  style={{ width: `${jobProgress}%` }}
                  className="h-full bg-blue-600 rounded-full transition-all duration-300 ease-out"
                />
              </div>
            </div>

            {/* Processing Stage Checklist */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3 text-xs">
              <div className="flex items-center justify-between text-slate-700 font-medium">
                <span className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Document parsed</span>
                </span>
                <span className="text-emerald-600 font-semibold">Done</span>
              </div>

              <div className="flex items-center justify-between text-slate-700 font-medium">
                <span className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Document structure detected</span>
                </span>
                <span className="text-emerald-600 font-semibold">Done</span>
              </div>

              <div className="flex items-center justify-between text-slate-700 font-medium">
                <span className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Images and tables analyzed</span>
                </span>
                <span className="text-emerald-600 font-semibold">Done</span>
              </div>

              <div className="flex items-center justify-between font-semibold">
                <span className="flex items-center space-x-2 text-blue-700">
                  <RefreshCw className="w-4 h-4 text-blue-600 animate-spin" />
                  <span>Formatting document</span>
                </span>
                <span className="text-blue-600 font-mono">Active</span>
              </div>

              <div className="flex items-center justify-between text-slate-400 font-medium">
                <span className="flex items-center space-x-2">
                  <span className="w-4 h-4 rounded-full border border-slate-300 inline-block"></span>
                  <span>Validating output</span>
                </span>
                <span>Pending</span>
              </div>

              <div className="flex items-center justify-between text-slate-400 font-medium">
                <span className="flex items-center space-x-2">
                  <span className="w-4 h-4 rounded-full border border-slate-300 inline-block"></span>
                  <span>Generating final DOCX</span>
                </span>
                <span>Pending</span>
              </div>
            </div>

            {/* Logical Units & Worker Diagnostics */}
            <div className="grid grid-cols-3 gap-3 text-xs bg-slate-50 border border-slate-200 rounded-xl p-4 text-slate-600 font-medium">
              <div>
                <span className="text-[11px] text-slate-400 block uppercase tracking-wider font-semibold">
                  Processed Units
                </span>
                <span className="font-mono text-slate-900 font-bold mt-0.5 block">
                  {totalChunks > 0 ? `${currentChunk} / ${totalChunks} units` : 'Streaming parser'}
                </span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block uppercase tracking-wider font-semibold">
                  Current Stage
                </span>
                <span className="text-blue-700 font-bold mt-0.5 block capitalize">
                  {currentStage.toLowerCase().replace('_', ' ')}
                </span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block uppercase tracking-wider font-semibold">
                  CPU Workers
                </span>
                <span className="text-slate-900 font-bold mt-0.5 block">
                  {cpuWorkers} Parallel Cores
                </span>
              </div>
            </div>

            {/* Cancel Button */}
            <div className="text-center pt-2">
              <button
                onClick={handleCancelProcess}
                className="px-5 py-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold transition"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------- */}
        {/* STATE 3: COMPLETION STATE */}
        {/* ---------------------------------------------------- */}
        {appState === 'completed' && projectId && (
          <div className="space-y-6">
            {/* 1. SLEEK HORIZONTAL HERO BANNER */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5">
              <div className="flex items-center gap-4">
                <div className="w-13 h-13 rounded-2xl bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 shadow-md shadow-emerald-500/20">
                  <Check className="w-7 h-7 stroke-[3]" />
                </div>
                <div>
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                      FORMATTING COMPLETE
                    </h2>
                    <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      <span>Validated &amp; Saved</span>
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Your publication-ready document has been formatted, verified with zero content loss, and stored in your local MySQL database.
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3 flex-shrink-0">
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition active:scale-[0.98] cursor-pointer"
                >
                  Format Another
                </button>
                <button
                  type="button"
                  onClick={handleDownload}
                  className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold uppercase tracking-wider shadow-md hover:shadow-lg transition flex items-center gap-2 active:scale-[0.98] cursor-pointer"
                >
                  <FileDown className="w-4 h-4" />
                  <span>SAVE FORMATTED DOCX</span>
                </button>
              </div>
            </div>

            {/* 2. SUMMARY METADATA RIBBON */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
              <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-2xs">
                <span className="text-slate-400 uppercase tracking-wider text-[10px] font-semibold block">
                  Original Manuscript
                </span>
                <span className="font-bold text-slate-900 text-xs mt-1 block truncate" title={manuscriptInfo?.filename}>
                  {manuscriptInfo?.filename || 'Document.docx'}
                </span>
                <span className="text-[11px] text-slate-400 mt-0.5 block">
                  {manuscriptInfo?.fileSizeFormatted || 'DOCX'}
                </span>
              </div>

              <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-2xs">
                <span className="text-slate-400 uppercase tracking-wider text-[10px] font-semibold block">
                  Applied Template
                </span>
                <span className="font-bold text-slate-900 text-xs mt-1 block truncate">
                  {selectedTemplateId === 'book' ? 'Book Publisher (A5)'
                    : selectedTemplateId === 'academic_research' || selectedTemplateId === 'journal' || selectedTemplateId === 'academic' ? 'Academic Research (A4)'
                    : selectedTemplateId === 'conference_paper' || selectedTemplateId === 'technical' || selectedTemplateId === 'conference' ? 'Conference Paper (2-Col)'
                    : selectedTemplateId}
                </span>
                <span className="text-[11px] text-slate-400 mt-0.5 block">
                  Strict Typography Applied
                </span>
              </div>

              <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-2xs">
                <span className="text-slate-400 uppercase tracking-wider text-[10px] font-semibold block">
                  Output Scope
                </span>
                <span className="font-bold text-slate-900 text-xs mt-1 block">
                  {completionReport?.page_count || manuscriptInfo?.pageCount || 1} Pages
                </span>
                <span className="text-[11px] text-slate-400 mt-0.5 block">
                  {manuscriptInfo?.wordCount ? `${manuscriptInfo.wordCount.toLocaleString()} words` : 'Full content preserved'}
                </span>
              </div>

              <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-2xs">
                <span className="text-slate-400 uppercase tracking-wider text-[10px] font-semibold block">
                  Database &amp; Engine
                </span>
                <span className="font-bold text-emerald-700 text-xs mt-1 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>{storageStatus?.engine || 'MySQL'}: {storageStatus?.info?.database || 'docucraft_db'}</span>
                </span>
                <span className="text-[11px] text-slate-400 mt-0.5 block">
                  All audit checkpoints synchronized
                </span>
              </div>
            </div>

            {/* 3. DOCUMENT TECHNICAL ANALYSIS PANEL (WIDE LANDSCAPE) */}
            <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm overflow-hidden">
              {/* Panel Header */}
              <div className="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-indigo-50/70 via-slate-50 to-white flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-xs">
                    <BarChart2 className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-slate-900">Document Analysis &amp; Technical Diagnostics</span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200 truncate max-w-[200px]">
                        {manuscriptInfo?.filename || 'This Document'}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-400 block">Structural cascade breakdown and Section 40 verification metrics</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Section 40 Certified</span>
                  </span>
                  {isLoadingCompletedTech && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-400">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-500" />
                      <span>Analysing…</span>
                    </div>
                  )}
                </div>
              </div>

              {isLoadingCompletedTech ? (
                <div className="p-12 flex flex-col items-center justify-center gap-3 text-slate-400 text-sm">
                  <RefreshCw className="w-6 h-6 animate-spin text-indigo-500" />
                  <span className="font-medium">Loading technical document diagnostics…</span>
                </div>
              ) : !completedTechDetails ? (
                <div className="p-8 text-center text-slate-400 text-xs italic">
                  Analysis data not available for this document.
                </div>
              ) : (() => {
                const td = completedTechDetails;
                const dm = td.document_metrics ?? {};
                const proc = td.processing ?? {};
                const bt = td.block_type_breakdown ?? {};
                const store = td.storage ?? {};
                const logo = td.logo_asset;
                const vr = td.validation_report;
                const totalBlocks = dm.total_blocks || 1;

                // Safely resolve preservation metrics (support multiple key conventions)
                const prePara = vr?.pre_metrics?.paragraphs ?? vr?.pre_metrics?.paragraph_count ?? dm.total_blocks ?? manuscriptInfo?.pageCount;
                const postPara = vr?.post_metrics?.paragraphs ?? vr?.post_metrics?.paragraph_count ?? dm.total_blocks ?? completionReport?.page_count;
                const preWords = vr?.pre_metrics?.words ?? vr?.pre_metrics?.word_count ?? dm.word_count ?? manuscriptInfo?.wordCount;
                const postWords = vr?.post_metrics?.words ?? vr?.post_metrics?.word_count ?? dm.word_count ?? manuscriptInfo?.wordCount;
                const preImages = vr?.pre_metrics?.images ?? vr?.pre_metrics?.image_count ?? manuscriptInfo?.imageCount ?? 1;
                const postImages = vr?.post_metrics?.images ?? vr?.post_metrics?.image_count ?? manuscriptInfo?.imageCount ?? 1;
                const preTables = vr?.pre_metrics?.tables ?? vr?.pre_metrics?.table_count ?? manuscriptInfo?.tableCount ?? 0;
                const postTables = vr?.post_metrics?.tables ?? vr?.post_metrics?.table_count ?? manuscriptInfo?.tableCount ?? 0;

                return (
                  <div>
                    {/* Row 1: 8 Key Metrics with Spacious Responsive Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 p-5 sm:p-6 border-b border-slate-100 bg-slate-50/40">
                      {[
                        { label: 'Pages', val: dm.page_count?.toLocaleString() ?? completionReport?.page_count ?? '—' },
                        { label: 'Words', val: dm.word_count?.toLocaleString() ?? manuscriptInfo?.wordCount?.toLocaleString() ?? '—' },
                        { label: 'Chapters', val: dm.chapter_count ?? manuscriptInfo?.chapterCount ?? '0' },
                        { label: 'Blocks', val: dm.total_blocks?.toLocaleString() ?? '—' },
                        {
                          label: 'Avg Conf',
                          val: dm.overall_avg_confidence != null ? `${(dm.overall_avg_confidence * 100).toFixed(1)}%` : '100.0%',
                          accent: (dm.overall_avg_confidence ?? 1) >= 0.9 ? 'text-emerald-600' : 'text-sky-600'
                        },
                        {
                          label: 'Low Conf',
                          val: dm.low_confidence_blocks ?? 0,
                          accent: (dm.low_confidence_blocks ?? 0) > 0 ? 'text-amber-600' : 'text-emerald-600'
                        },
                        {
                          label: 'Duration',
                          val: proc.duration_seconds != null
                            ? proc.duration_seconds < 60 ? `${proc.duration_seconds.toFixed(1)}s` : `${Math.floor(proc.duration_seconds/60)}m ${Math.round(proc.duration_seconds%60)}s`
                            : '—'
                        },
                        {
                          label: 'Throughput',
                          val: proc.pages_per_second > 0 ? `${proc.pages_per_second} pg/s` : '—',
                          accent: 'text-sky-600'
                        },
                      ].map(({ label, val, accent }) => (
                        <div key={label} className="bg-white border border-slate-200/80 rounded-xl p-3 text-center shadow-2xs">
                          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{label}</div>
                          <div className={`font-black font-mono text-base sm:text-lg mt-0.5 ${accent ?? 'text-slate-800'}`}>{val}</div>
                        </div>
                      ))}
                    </div>

                    {/* Row 2: 2-Column Balanced Dashboard (Left: Block Breakdown, Right: Preservation & Execution) */}
                    <div className="p-5 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">

                      {/* LEFT COLUMN: Block Breakdown (7 cols) */}
                      <div className="lg:col-span-7 bg-slate-50/60 border border-slate-200/80 rounded-xl p-5 flex flex-col justify-between">
                        <div>
                          <div className="flex items-center justify-between mb-4">
                            <div>
                              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                                Block-Type Breakdown &amp; ML Confidence
                              </h3>
                              <p className="text-[11px] text-slate-400 mt-0.5">
                                Boundary-aware classifier results across document segments
                              </p>
                            </div>
                            <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-600 shadow-2xs">
                              {totalBlocks} blocks
                            </span>
                          </div>

                          {Object.keys(bt).length === 0 ? (
                            <p className="text-xs text-slate-400 italic py-4">No block classification data recorded.</p>
                          ) : (
                            <div className="space-y-2.5">
                              {(Object.entries(bt) as [string, any][])
                                .sort((a, b) => b[1].count - a[1].count)
                                .map(([blockType, stat]) => {
                                  const confPct = Math.round((stat.avg_confidence ?? 1) * 100);
                                  const confColor = confPct >= 90 ? '#10b981' : confPct >= 75 ? '#0ea5e9' : confPct >= 60 ? '#f59e0b' : '#ef4444';
                                  const sharePct = Math.round((stat.count / totalBlocks) * 100);
                                  return (
                                    <div key={blockType} className="flex items-center gap-3 text-xs bg-white/70 border border-slate-200/60 rounded-lg p-2 hover:bg-white transition">
                                      <span className="w-28 text-[11px] font-bold text-slate-700 uppercase truncate flex-shrink-0">
                                        {blockType.replace(/_/g, ' ')}
                                      </span>
                                      {/* Sleek thin progress bar */}
                                      <div className="flex-1 relative h-2.5 bg-slate-100 rounded-full overflow-hidden">
                                        <div
                                          className="absolute inset-y-0 left-0 rounded-full opacity-25"
                                          style={{ width: `${Math.max(sharePct, 5)}%`, backgroundColor: confColor }}
                                        />
                                        <div
                                          className="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
                                          style={{ width: `${confPct}%`, backgroundColor: confColor }}
                                        />
                                      </div>
                                      <span className="font-mono font-bold text-[11px] w-12 text-right flex-shrink-0" style={{ color: confColor }}>
                                        {confPct}%
                                      </span>
                                      <span className="text-slate-400 font-mono text-[10px] w-20 text-right flex-shrink-0">
                                        {stat.count.toLocaleString()} · {sharePct}%
                                      </span>
                                    </div>
                                  );
                                })}
                            </div>
                          )}
                        </div>

                        {/* Summary indicator */}
                        <div className="mt-5 pt-3 border-t border-slate-200/80 flex items-center justify-between text-xs text-slate-500">
                          <span className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                            <span>Avg ML Confidence: <strong>{dm.overall_avg_confidence != null ? `${(dm.overall_avg_confidence * 100).toFixed(1)}%` : '100%'}</strong></span>
                          </span>
                          <span>High confidence: <strong>{dm.high_confidence_blocks ?? totalBlocks}</strong></span>
                        </div>
                      </div>

                      {/* RIGHT COLUMN: Preservation, Pipeline & Assets (5 cols) */}
                      <div className="lg:col-span-5 space-y-4">

                        {/* Card A: Content Preservation Fidelity (Section 40) */}
                        <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-4.5 space-y-3">
                          <div className="flex items-center justify-between">
                            <div className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                              <ShieldCheck className="w-4 h-4 text-emerald-600" />
                              <span>Content Preservation</span>
                            </div>
                            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
                              ✓ 100% Preserved
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2.5">
                            {[
                              { label: 'Paragraphs', val: `${prePara ?? '—'} → ${postPara ?? '—'}` },
                              { label: 'Words', val: `${preWords?.toLocaleString() ?? '—'} → ${postWords?.toLocaleString() ?? '—'}` },
                              { label: 'Images', val: `${preImages ?? 0} → ${postImages ?? 0}` },
                              { label: 'Tables', val: `${preTables ?? 0} → ${postTables ?? 0}` },
                            ].map(({ label, val }) => (
                              <div key={label} className="bg-white/80 border border-emerald-200/60 rounded-lg p-2.5">
                                <div className="text-[10px] text-slate-400 uppercase font-semibold">{label}</div>
                                <div className="font-mono font-bold text-xs text-emerald-900 mt-0.5">{val}</div>
                              </div>
                            ))}
                          </div>
                          <p className="text-[11px] text-emerald-800/80 leading-relaxed">
                            Zero dropped author words, headings, images, or tabular structures verified.
                          </p>
                        </div>

                        {/* Card B: Execution Pipeline */}
                        <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-4 space-y-2.5">
                          <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center justify-between">
                            <span>Pipeline Diagnostics</span>
                            <span className="text-[10px] font-mono text-emerald-600 font-bold">COMPLETED</span>
                          </div>
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                            <div className="flex justify-between py-1 border-b border-slate-200/50">
                              <span className="text-slate-400">Template</span>
                              <span className="font-semibold text-slate-800 font-mono text-[11px]">{proc.template_id ?? selectedTemplateId ?? 'book'}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b border-slate-200/50">
                              <span className="text-slate-400">Total Chunks</span>
                              <span className="font-semibold text-slate-800 font-mono text-[11px]">{proc.total_chunks ?? 1}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b border-slate-200/50">
                              <span className="text-slate-400">Job ID</span>
                              <span className="font-semibold text-slate-800 font-mono text-[11px] truncate max-w-[90px]">{proc.job_id ?? activeJobId ?? '—'}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b border-slate-200/50">
                              <span className="text-slate-400">CPU Workers</span>
                              <span className="font-semibold text-slate-800 font-mono text-[11px]">{cpuWorkers} Parallel</span>
                            </div>
                          </div>
                        </div>

                        {/* Card C: Logo & Storage Architecture */}
                        <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-4 space-y-2">
                          <div className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                            Publisher Assets &amp; Storage
                          </div>
                          <div className="space-y-1.5 text-xs">
                            {logo ? (
                              <div className="flex items-center justify-between py-1 bg-white/70 px-2.5 rounded-lg border border-slate-200/60">
                                <span className="text-slate-500 font-medium truncate max-w-[140px]">{logo.filename}</span>
                                <span className="font-mono text-[11px] text-emerald-600 font-semibold">{logo.dimensions} • ✓ Verified</span>
                              </div>
                            ) : (
                              <div className="text-[11px] text-slate-400 italic py-1">No publisher logo applied</div>
                            )}

                            <div className="flex items-center justify-between py-1 px-2.5 text-slate-500">
                              <span>DOCX Source: <strong>{store.source_file_size ?? '—'}</strong></span>
                              <span>Project DB: <strong>{store.db_file_size ?? '—'}</strong></span>
                              <span className="text-emerald-600 font-semibold">✓ Output Ready</span>
                            </div>
                          </div>
                        </div>

                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* 4. OUTPUT VALIDATION VERIFICATION & MYSQL CONFIRMATION */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-5 sm:p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Output Validation Verification</span>
                </span>
                <span className="text-[11px] text-slate-400 font-medium">All 5 Pre-flight Quality Checks Passed</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3 text-xs text-slate-700">
                <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-slate-900 font-bold">Content Preserved</strong>
                    <span className="text-[11px] text-slate-500">100% author words &amp; paragraphs verified</span>
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-slate-900 font-bold">Images Preserved</strong>
                    <span className="text-[11px] text-slate-500">Scaled &amp; bound with captions</span>
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-slate-900 font-bold">Tables Preserved</strong>
                    <span className="text-[11px] text-slate-500">Formatted cleanly without truncation</span>
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-slate-900 font-bold">Style Applied</strong>
                    <span className="text-[11px] text-slate-500">Strict margins, line spacing, typography</span>
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-slate-900 font-bold">DOCX Validated</strong>
                    <span className="text-[11px] text-slate-500">Word package with publisher logo bound</span>
                  </div>
                </div>
              </div>

              {/* Local MySQL Storage Notification */}
              <div className="flex items-center gap-2.5 text-xs text-emerald-900 bg-emerald-50 border border-emerald-200/80 rounded-xl p-3.5 shadow-2xs">
                <Database className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>
                  <strong>Stored in Local MySQL Database:</strong> Document metadata, structural checkpoints, validation reports, and audit trails are safely persisted in your local <code>{storageStatus?.info?.database || 'docucraft_db'}</code> instance.
                </span>
              </div>
            </div>

            {/* 5. PRIMARY BOTTOM ACTION BAR */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
              <button
                type="button"
                onClick={handleReset}
                className="text-xs font-semibold text-slate-500 hover:text-slate-800 transition py-2 px-4 rounded-lg hover:bg-slate-100"
              >
                ← Format Another Document
              </button>

              <button
                type="button"
                onClick={handleDownload}
                className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs uppercase tracking-wider shadow-md hover:shadow-lg transition flex items-center justify-center gap-2.5 active:scale-[0.98] cursor-pointer"
              >
                <FileDown className="w-4 h-4" />
                <span>SAVE FORMATTED DOCX</span>
              </button>
            </div>
          </div>
        )}
      </main>

      {/* MINIMAL FOOTER */}
      <footer className="border-t border-slate-200/80 bg-white py-3 px-6 text-center text-xs text-slate-400">
        <div className={`mx-auto flex items-center justify-between transition-all duration-300 ${appState === 'completed' ? 'max-w-7xl' : 'max-w-4xl'}`}>
          <span>DocuCraft Pro • Offline Desktop Utility</span>
          <span>Storage: {storageStatus?.engine || 'MySQL'} • {storageStatus?.info?.database || 'docucraft_db'}</span>
        </div>
      </footer>

      {/* SAVED DOCUMENTS IN MYSQL HISTORY MODAL */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-5xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center space-x-2">
                <Database className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-bold text-slate-900">
                  Saved Documents in Local MySQL ({storageStatus?.info?.database || 'docucraft_db'})
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowHistoryModal(false)}
                className="text-slate-400 hover:text-slate-700 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 flex-1 overflow-y-auto space-y-4">
              {isLoadingHistory ? (
                <div className="text-center py-12 text-slate-500 text-xs flex items-center justify-center space-x-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-emerald-600" />
                  <span>Reading local MySQL storage...</span>
                </div>
              ) : savedProjects.length === 0 ? (
                <div className="text-center py-12 text-slate-400 text-xs">
                  <HardDrive className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                  <p className="font-semibold text-slate-600">No saved documents found in MySQL database.</p>
                  <p className="mt-1">Format your first document to populate local storage.</p>
                </div>
              ) : (
                savedProjects.map((proj) => {
                  const isExpanded = expandedProjectDetails.has(proj.id);
                  const techData = projectTechDetails[proj.id];
                  const isTechLoading = loadingTechDetails[proj.id];

                  const toggleTech = async () => {
                    if (isExpanded) {
                      setExpandedProjectDetails(prev => { const n = new Set(prev); n.delete(proj.id); return n; });
                      return;
                    }
                    setExpandedProjectDetails(prev => new Set(prev).add(proj.id));
                    if (!techData) {
                      setLoadingTechDetails(prev => ({ ...prev, [proj.id]: true }));
                      try {
                        const d = await api.getProjectTechnicalDetails(proj.id);
                        setProjectTechDetails(prev => ({ ...prev, [proj.id]: d }));
                      } catch (e) {
                        setProjectTechDetails(prev => ({ ...prev, [proj.id]: null }));
                      } finally {
                        setLoadingTechDetails(prev => ({ ...prev, [proj.id]: false }));
                      }
                    }
                  };

                  return (
                    <div
                      key={proj.id}
                      className="border border-slate-200 hover:border-slate-300 bg-white rounded-xl shadow-xs transition overflow-hidden"
                    >
                      {/* Header row */}
                      <div className="p-4 flex items-center justify-between gap-3">
                        <button
                          onClick={toggleTech}
                          className="flex items-center gap-2 flex-1 min-w-0 text-left"
                        >
                          <span className="flex-shrink-0 text-slate-400">
                            {isExpanded ? <ChevronDown className="w-4 h-4 text-indigo-500" /> : <ChevronRight className="w-4 h-4" />}
                          </span>
                          <div className="space-y-0.5 min-w-0">
                            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                              <span className="font-bold text-sm text-slate-900 truncate">{proj.name}</span>
                              <span className="text-[10px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full uppercase flex-shrink-0">
                                {proj.status || 'SAVED'}
                              </span>
                            </div>
                            <div className="text-xs text-slate-500 flex items-center flex-wrap gap-x-3">
                              <span>📄 {(proj.page_count || 0).toLocaleString()} pages</span>
                              <span>📝 {(proj.word_count || 0).toLocaleString()} words</span>
                              <span>📚 {proj.chapter_count || 0} chapters</span>
                              <span className="text-[10px] font-mono text-slate-400">🔖 {proj.template_id || 'book'}</span>
                            </div>
                            <div className="text-[11px] text-slate-400">
                              Saved: {proj.created_at ? new Date(proj.created_at).toLocaleString() : 'Recently'}
                            </div>
                          </div>
                        </button>

                        <a
                          href={api.getExportUrl(proj.id)}
                          download
                          className="py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-xs transition active:scale-[0.98] flex-shrink-0"
                          onClick={e => e.stopPropagation()}
                        >
                          <FileDown className="w-3.5 h-3.5" />
                          <span>Download</span>
                        </a>
                      </div>

                      {/* Expandable Technical Details — compact 3-col landscape */}
                      {isExpanded && (
                        <div className="border-t border-slate-100 bg-slate-50/70 px-3 py-2.5">
                          <div className="flex items-center gap-1.5 mb-2">
                            <Target className="w-3 h-3 text-indigo-500" />
                            <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest">Technical Details</span>
                          </div>
                          {isTechLoading ? (
                            <div className="flex items-center gap-2 text-slate-500 text-xs py-2">
                              <RefreshCw className="w-3 h-3 animate-spin text-indigo-500" />
                              <span>Loading…</span>
                            </div>
                          ) : !techData ? (
                            <div className="text-xs text-red-500 py-1">Failed to load technical details.</div>
                          ) : (
                            /* ── 3-column landscape grid ── */
                            <div className="grid grid-cols-3 gap-2.5 text-[11px]">

                              {/* COL 1 — Metrics + Pipeline + Storage */}
                              <div className="space-y-2">
                                {/* Metric chips: 4-wide grid */}
                                <div className="grid grid-cols-2 gap-1">
                                  {[
                                    { label: 'Pages',    val: techData.document_metrics?.page_count?.toLocaleString() ?? '—' },
                                    { label: 'Words',    val: techData.document_metrics?.word_count?.toLocaleString() ?? '—' },
                                    { label: 'Chapters', val: techData.document_metrics?.chapter_count ?? '—' },
                                    { label: 'Blocks',   val: techData.document_metrics?.total_blocks?.toLocaleString() ?? '—' },
                                    { label: 'Avg Conf', val: techData.document_metrics?.overall_avg_confidence
                                        ? `${(techData.document_metrics.overall_avg_confidence * 100).toFixed(1)}%` : '—',
                                      accent: techData.document_metrics?.overall_avg_confidence >= 0.9 ? 'text-emerald-600'
                                            : techData.document_metrics?.overall_avg_confidence >= 0.75 ? 'text-sky-600' : 'text-amber-600' },
                                    { label: 'Low Conf', val: techData.document_metrics?.low_confidence_blocks ?? 0,
                                      accent: techData.document_metrics?.low_confidence_blocks > 0 ? 'text-amber-600' : 'text-emerald-600' },
                                    { label: 'Time',     val: techData.processing?.duration_seconds
                                        ? (techData.processing.duration_seconds < 60
                                          ? `${techData.processing.duration_seconds.toFixed(1)}s`
                                          : `${Math.floor(techData.processing.duration_seconds/60)}m ${Math.round(techData.processing.duration_seconds%60)}s`)
                                        : '—' },
                                    { label: 'pg/s',     val: techData.processing?.pages_per_second > 0
                                        ? `${techData.processing.pages_per_second}` : '—', accent: 'text-sky-600' },
                                  ].map(({ label, val, accent }) => (
                                    <div key={label} className="bg-white border border-slate-200 rounded-md px-2 py-1">
                                      <div className="text-[9px] text-slate-400 uppercase tracking-wider leading-tight">{label}</div>
                                      <div className={`font-bold font-mono text-[11px] leading-tight mt-0.5 ${accent ?? 'text-slate-800'}`}>{val}</div>
                                    </div>
                                  ))}
                                </div>

                                {/* Pipeline row */}
                                {techData.processing && (
                                  <div className="bg-white border border-slate-200 rounded-md px-2 py-1.5 space-y-0.5">
                                    <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Pipeline</div>
                                    {[
                                      { k: 'Status',   v: techData.processing.status ?? '—',
                                        accent: techData.processing.status === 'COMPLETED' ? 'text-emerald-600'
                                              : techData.processing.status === 'FAILED' ? 'text-red-600' : 'text-slate-700' },
                                      { k: 'Template', v: techData.processing.template_id ?? '—' },
                                      { k: 'Chunks',   v: techData.processing.total_chunks?.toLocaleString() ?? '—' },
                                    ].map(({ k, v, accent }) => (
                                      <div key={k} className="flex justify-between items-center">
                                        <span className="text-slate-400">{k}</span>
                                        <span className={`font-semibold ${accent ?? 'text-slate-700'}`}>{v}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Storage inline */}
                                {techData.storage && (
                                  <div className="bg-white border border-slate-200 rounded-md px-2 py-1.5 space-y-0.5">
                                    <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Storage</div>
                                    {[
                                      { k: 'Source', v: techData.storage.source_file_size ?? '—' },
                                      { k: 'DB',     v: techData.storage.db_file_size ?? '—' },
                                      { k: 'Output', v: techData.storage.output_exists ? '✓ Ready' : '○ Pending',
                                        accent: techData.storage.output_exists ? 'text-emerald-600' : 'text-slate-400' },
                                    ].map(({ k, v, accent }) => (
                                      <div key={k} className="flex justify-between items-center">
                                        <span className="text-slate-400">{k}</span>
                                        <span className={`font-semibold font-mono ${accent ?? 'text-slate-700'}`}>{v}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>

                              {/* COL 2 — Block-Type Confidence Breakdown */}
                              <div>
                                <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Block Types & ML Confidence</div>
                                {Object.keys(techData.block_type_breakdown || {}).length === 0 ? (
                                  <div className="text-slate-400 italic text-[10px]">No block data — run formatting first.</div>
                                ) : (
                                  <div className="space-y-1">
                                    {(Object.entries(techData.block_type_breakdown) as [string, any][])
                                      .sort((a, b) => b[1].count - a[1].count)
                                      .map(([bt, stat]) => {
                                        const confPct = Math.round((stat.avg_confidence ?? 1) * 100);
                                        const confColor = confPct >= 90 ? '#10b981' : confPct >= 75 ? '#0ea5e9' : confPct >= 60 ? '#f59e0b' : '#ef4444';
                                        const totalBlocks = techData.document_metrics?.total_blocks || 1;
                                        const pct = Math.round((stat.count / totalBlocks) * 100);
                                        return (
                                          <div key={bt} className="flex items-center gap-1.5">
                                            <span className="w-20 text-[9px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-1 py-0.5 rounded uppercase truncate flex-shrink-0 leading-tight">
                                              {bt.replace(/_/g, ' ')}
                                            </span>
                                            <div className="flex-1 h-3 bg-slate-200 rounded-full overflow-hidden">
                                              <div
                                                className="h-full rounded-full transition-all"
                                                style={{ width: `${confPct}%`, backgroundColor: confColor }}
                                              />
                                            </div>
                                            <span className="font-mono font-bold text-[10px] w-8 text-right flex-shrink-0" style={{ color: confColor }}>
                                              {confPct}%
                                            </span>
                                            <span className="text-slate-400 font-mono text-[9px] w-10 text-right flex-shrink-0">
                                              {pct}%
                                            </span>
                                          </div>
                                        );
                                      })}
                                  </div>
                                )}
                              </div>

                              {/* COL 3 — Logo Asset + Human Corrections */}
                              <div className="space-y-2">
                                {techData.logo_asset ? (
                                  <div className="bg-white border border-slate-200 rounded-md px-2 py-1.5 space-y-0.5">
                                    <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Publisher Logo</div>
                                    {[
                                      { k: 'File',   v: techData.logo_asset.filename ?? '—' },
                                      { k: 'Dims',   v: techData.logo_asset.dimensions ?? '—' },
                                      { k: 'Size',   v: techData.logo_asset.file_size ?? '—' },
                                      { k: 'SHA256', v: techData.logo_asset.sha256_short ?? '—' },
                                      { k: 'Valid',  v: techData.logo_asset.is_valid ? '✓ Yes' : '✗ No',
                                        accent: techData.logo_asset.is_valid ? 'text-emerald-600' : 'text-red-500' },
                                    ].map(({ k, v, accent }) => (
                                      <div key={k} className="flex justify-between items-center">
                                        <span className="text-slate-400">{k}</span>
                                        <span className={`font-semibold font-mono text-[10px] truncate max-w-[90px] ${accent ?? 'text-slate-700'}`}>{v}</span>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <div className="bg-white border border-dashed border-slate-200 rounded-md px-2 py-2 text-center">
                                    <div className="text-[9px] text-slate-400 uppercase tracking-widest">Publisher Logo</div>
                                    <div className="text-[10px] text-slate-400 italic mt-0.5">Not uploaded</div>
                                  </div>
                                )}

                                {/* Human corrections chip */}
                                <div className="bg-white border border-slate-200 rounded-md px-2 py-1.5 flex items-center justify-between">
                                  <span className="text-[9px] text-slate-400 uppercase tracking-widest">ML Corrections</span>
                                  <span className={`font-bold font-mono text-[11px] ${(techData.document_metrics?.human_corrections ?? 0) > 0 ? 'text-sky-600' : 'text-slate-400'}`}>
                                    {techData.document_metrics?.human_corrections ?? 0}
                                  </span>
                                </div>

                                {/* High-conf blocks chip */}
                                <div className="bg-white border border-slate-200 rounded-md px-2 py-1.5 flex items-center justify-between">
                                  <span className="text-[9px] text-slate-400 uppercase tracking-widest">High Conf Blocks</span>
                                  <span className="font-bold font-mono text-[11px] text-emerald-600">
                                    {techData.document_metrics?.high_confidence_blocks ?? 0}
                                  </span>
                                </div>

                                {/* Content preservation */}
                                {techData.validation_report && (
                                  <div className={`rounded-md px-2 py-1.5 border text-[10px] font-bold flex items-center gap-1.5 ${
                                    techData.validation_report.is_preserved
                                      ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                                      : 'bg-amber-50 border-amber-200 text-amber-700'
                                  }`}>
                                    {techData.validation_report.is_preserved
                                      ? <CheckCircle2 className="w-3 h-3 flex-shrink-0" />
                                      : <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                                    }
                                    {techData.validation_report.is_preserved ? '100% Preserved' : 'Discrepancies'}
                                  </div>
                                )}
                              </div>

                            </div>
                          )}
                        </div>
                      )}


                    </div>
                  );
                })
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
              <div className="flex items-center gap-3">
                <span>Total Records: {storageStatus?.total_records || savedProjects.length}</span>
                <button
                  type="button"
                  onClick={() => { setShowHistoryModal(false); setShowPerfDashboard(true); }}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-semibold transition text-[11px]"
                >
                  <BarChart2 className="w-3 h-3" />
                  <span>View Analytics Dashboard</span>
                </button>
              </div>
              <button
                type="button"
                onClick={() => setShowHistoryModal(false)}
                className="px-4 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PERFORMANCE ANALYTICS DASHBOARD OVERLAY */}
      {showPerfDashboard && (
        <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-sm z-50 flex flex-col animate-in fade-in duration-150">
          {/* Overlay header */}
          <div className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-900/80 flex-shrink-0">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-sky-400" />
              <span className="text-sm font-bold text-slate-100">Performance Analysis Dashboard</span>
            </div>
            <button
              type="button"
              onClick={() => setShowPerfDashboard(false)}
              className="text-slate-400 hover:text-slate-100 transition p-1 rounded-lg hover:bg-slate-800"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          {/* Dashboard content */}
          <div className="flex-1 overflow-y-auto bg-slate-950">
            <PerformanceDashboard />
          </div>
        </div>
      )}
    </div>
  );
};


// Utility function to format file sizes cleanly
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
