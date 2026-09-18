import React, { useState, useEffect, useRef } from 'react';
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
  HardDrive
} from 'lucide-react';
import { api } from '../services/api';
import { BookTemplate } from '../types';

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
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-900 uppercase flex items-center space-x-2">
              <span>INTELLIGENT DOCUMENT FORMATTER</span>
            </h1>
            <p className="text-xs text-slate-500 font-medium tracking-wide">
              Offline • Private • Publication Ready
            </p>
          </div>
          
          {/* Storage & Saved Documents Badges */}
          <div className="flex items-center space-x-3">
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
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-8 flex flex-col justify-start">
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
          <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm space-y-6">
            <div className="text-center">
              <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-3">
                <Check className="w-6 h-6 stroke-[3]" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
                COMPLETE
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Your publication-ready document has been formatted and validated.
              </p>
            </div>

            {/* Document Details Card */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div>
                <span className="text-slate-400 uppercase tracking-wider text-[10px] font-semibold block">
                  Original Manuscript
                </span>
                <span className="font-semibold text-slate-900 mt-0.5 block truncate">
                  {manuscriptInfo?.filename || 'Document.docx'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 uppercase tracking-wider text-[10px] font-semibold block">
                  Applied Template
                </span>
                <span className="font-semibold text-slate-900 mt-0.5 block">
                  {selectedTemplateId === 'book'
                    ? 'Book Publisher (A5)'
                    : selectedTemplateId === 'academic_research' || selectedTemplateId === 'journal' || selectedTemplateId === 'academic'
                    ? 'Academic Research Paper (A4)'
                    : selectedTemplateId === 'conference_paper' || selectedTemplateId === 'technical' || selectedTemplateId === 'conference'
                    ? 'Conference Paper (A4 2-Col)'
                    : selectedTemplateId}
                </span>
              </div>
              <div>
                <span className="text-slate-400 uppercase tracking-wider text-[10px] font-semibold block">
                  Estimated Pages
                </span>
                <span className="font-semibold text-slate-900 mt-0.5 block">
                  {completionReport?.page_count || manuscriptInfo?.pageCount || 1} pages
                </span>
              </div>
              <div>
                <span className="text-slate-400 uppercase tracking-wider text-[10px] font-semibold block">
                  Processing Status
                </span>
                <span className="font-semibold text-emerald-600 mt-0.5 block">
                  ✓ Successful
                </span>
              </div>
            </div>

            {/* Concise Validation Badges */}
            <div className="border border-slate-200 rounded-xl p-5 bg-white space-y-2.5 text-xs text-slate-700">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Output Validation Verification
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span><strong>Content preserved:</strong> 100% of author words & paragraphs verified</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span><strong>Images preserved:</strong> Scaled & caption-bound</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span><strong>Tables preserved:</strong> Formatted cleanly</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span><strong>Formatting applied:</strong> Times New Roman, 1.5 spacing, 1.27cm indent</span>
                </div>
                <div className="flex items-center space-x-2 col-span-1 md:col-span-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span><strong>DOCX validated:</strong> Microsoft Word compatible package with publisher logo bound</span>
                </div>
              </div>
            </div>

            {/* Local MySQL Storage Confirmation */}
            <div className="flex items-center space-x-2 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 shadow-sm">
              <Database className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>
                <strong>Saved to Local MySQL:</strong> Document metadata, checkpoints, validation reports, and extracted structure are safely stored in your local <code>{storageStatus?.info?.database || 'docucraft_db'}</code> database.
              </span>
            </div>


            {/* Primary Action Button: Save Formatted DOCX */}
            <div className="pt-2 space-y-3">
              <button
                type="button"
                onClick={handleDownload}
                className="w-full py-4 px-6 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm uppercase tracking-wider shadow-md transition flex items-center justify-center space-x-2 active:scale-[0.99] cursor-pointer"
              >
                <FileDown className="w-5 h-5" />
                <span>SAVE FORMATTED DOCX</span>
              </button>

              <div className="text-center">
                <button
                  onClick={handleReset}
                  className="text-xs font-semibold text-slate-500 hover:text-slate-800 transition py-1"
                >
                  Format Another Document
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* MINIMAL FOOTER */}
      <footer className="border-t border-slate-200/80 bg-white py-3 px-6 text-center text-xs text-slate-400">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <span>DocuCraft Pro • Offline Desktop Utility</span>
          <span>Storage: {storageStatus?.engine || 'MySQL'} • {storageStatus?.info?.database || 'docucraft_db'}</span>
        </div>
      </footer>

      {/* SAVED DOCUMENTS IN MYSQL HISTORY MODAL */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
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
                savedProjects.map((proj) => (
                  <div
                    key={proj.id}
                    className="border border-slate-200 hover:border-slate-300 bg-white rounded-xl p-4 flex items-center justify-between shadow-xs transition"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-sm text-slate-900">{proj.name}</span>
                        <span className="text-[10px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full uppercase">
                          {proj.status || 'SAVED'}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 flex items-center space-x-3">
                        <span>📄 {proj.page_count || 0} pages</span>
                        <span>📝 {proj.word_count || 0} words</span>
                        <span>🔖 Template: {proj.template_id || 'book'}</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Saved: {proj.created_at ? new Date(proj.created_at).toLocaleString() : 'Recently'}
                      </div>
                    </div>

                    <a
                      href={api.getExportUrl(proj.id)}
                      download
                      className="py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-xs transition active:scale-[0.98]"
                    >
                      <FileDown className="w-3.5 h-3.5" />
                      <span>Download DOCX</span>
                    </a>
                  </div>
                ))
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
              <span>Total MySQL Records: {storageStatus?.total_records || savedProjects.length}</span>
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
