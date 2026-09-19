import React, { useEffect, useState, useCallback } from 'react';
import {
  BarChart2,
  Zap,
  FileText,
  BookOpen,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Cpu,
  HardDrive,
  Activity,
  TrendingUp,
  Shield,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Database,
  Layers,
  Target,
} from 'lucide-react';
import { api } from '../services/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface BlockTypeStat {
  count: number;
  avg_confidence: number;
  total_words: number;
}

interface JobMetric {
  job_id: string;
  project_id: string;
  project_name: string;
  template_id: string;
  status: string;
  progress: number;
  total_chunks: number;
  pages: number;
  words: number;
  duration_seconds: number;
  pages_per_second: number;
  words_per_second: number;
  created_at: string;
  updated_at: string;
}

interface PerformanceData {
  summary: {
    total_documents: number;
    total_pages: number;
    total_words: number;
    total_chapters: number;
    total_jobs: number;
    completed_jobs: number;
    failed_jobs: number;
    avg_processing_seconds: number;
    success_rate: number;
  };
  quality_metrics: Record<string, {
    score: number;
    label: string;
    description: string;
    unit: string;
    rating: string;
    detail: Record<string, any>;
  }>;
  job_metrics: JobMetric[];
  block_type_stats: Record<string, BlockTypeStat>;
  system_metrics: any;
  recent_audit_events: any[];
  storage: any;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const BLOCK_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  CHAPTER_TITLE:  { bg: 'bg-sky-500/20',     text: 'text-sky-300',    border: 'border-sky-500/40' },
  HEADING_1:      { bg: 'bg-indigo-500/20',   text: 'text-indigo-300', border: 'border-indigo-500/40' },
  HEADING_2:      { bg: 'bg-violet-500/20',   text: 'text-violet-300', border: 'border-violet-500/40' },
  HEADING_3:      { bg: 'bg-purple-500/20',   text: 'text-purple-300', border: 'border-purple-500/40' },
  BODY:           { bg: 'bg-slate-500/20',    text: 'text-slate-300',  border: 'border-slate-500/40' },
  QUOTE:          { bg: 'bg-amber-500/20',    text: 'text-amber-300',  border: 'border-amber-500/40' },
  CAPTION:        { bg: 'bg-teal-500/20',     text: 'text-teal-300',   border: 'border-teal-500/40' },
  LIST:           { bg: 'bg-cyan-500/20',     text: 'text-cyan-300',   border: 'border-cyan-500/40' },
  TABLE:          { bg: 'bg-emerald-500/20',  text: 'text-emerald-300',border: 'border-emerald-500/40' },
  IMAGE:          { bg: 'bg-rose-500/20',     text: 'text-rose-300',   border: 'border-rose-500/40' },
  PAGE_BREAK:     { bg: 'bg-orange-500/20',   text: 'text-orange-300', border: 'border-orange-500/40' },
  UNKNOWN:        { bg: 'bg-red-500/20',      text: 'text-red-300',    border: 'border-red-500/40' },
};

function blockColor(bt: string) {
  return BLOCK_TYPE_COLORS[bt] ?? { bg: 'bg-slate-700/40', text: 'text-slate-400', border: 'border-slate-600' };
}

function statusColor(status: string) {
  switch (status) {
    case 'COMPLETED': return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    case 'FAILED':    return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
    case 'CANCELLED': return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
    default:          return 'text-sky-400 bg-sky-500/10 border-sky-500/30';
  }
}

function formatDuration(sec: number): string {
  if (!sec || sec <= 0) return '—';
  if (sec < 1)  return `${Math.round(sec * 1000)} ms`;
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}m ${s}s`;
}

function formatNumber(n: number): string {
  if (!n) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function confidenceColor(c: number): string {
  if (c >= 0.9)  return 'text-emerald-400';
  if (c >= 0.75) return 'text-sky-400';
  if (c >= 0.60) return 'text-amber-400';
  return 'text-rose-400';
}

function confidenceBarColor(c: number): string {
  if (c >= 0.9)  return 'bg-emerald-500';
  if (c >= 0.75) return 'bg-sky-500';
  if (c >= 0.60) return 'bg-amber-500';
  return 'bg-rose-500';
}

// ─── Reusable UI Pieces ───────────────────────────────────────────────────────

const KpiCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}> = ({ icon, label, value, sub, accent = 'text-sky-400' }) => (
  <div className="glass-card rounded-xl p-5 flex flex-col gap-2 border border-slate-800/60">
    <div className="flex items-center gap-2">
      <span className={`${accent} opacity-80`}>{icon}</span>
      <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">{label}</span>
    </div>
    <div className={`text-3xl font-black font-mono tracking-tight ${accent}`}>{value}</div>
    {sub && <div className="text-[11px] text-slate-500 font-medium">{sub}</div>}
  </div>
);

const SectionTitle: React.FC<{ icon: React.ReactNode; title: string; badge?: string }> = ({ icon, title, badge }) => (
  <div className="flex items-center gap-2 mb-4">
    <span className="text-sky-400">{icon}</span>
    <h2 className="text-base font-bold text-slate-200 tracking-tight">{title}</h2>
    {badge && (
      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
        {badge}
      </span>
    )}
  </div>
);

// ─── Quality Metric Card ─────────────────────────────────────────────────────

const RATING_STYLE: Record<string, { ring: string; score: string; badge: string; glow: string }> = {
  Excellent: { ring: 'stroke-emerald-400',  score: 'text-emerald-400', badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30', glow: 'shadow-emerald-500/20' },
  Good:      { ring: 'stroke-sky-400',      score: 'text-sky-400',     badge: 'bg-sky-500/15     text-sky-300     border-sky-500/30',     glow: 'shadow-sky-500/20'     },
  Fair:      { ring: 'stroke-amber-400',    score: 'text-amber-400',   badge: 'bg-amber-500/15   text-amber-300   border-amber-500/30',   glow: 'shadow-amber-500/20'   },
  Poor:      { ring: 'stroke-rose-400',     score: 'text-rose-400',    badge: 'bg-rose-500/15    text-rose-300    border-rose-500/30',    glow: 'shadow-rose-500/20'    },
  'No Data': { ring: 'stroke-slate-600',    score: 'text-slate-500',   badge: 'bg-slate-700/30   text-slate-400   border-slate-600',      glow: '' },
};

const QualityMetricCard: React.FC<{
  label: string;
  score: number;
  unit: string;
  rating: string;
  description: string;
  detail: Record<string, any>;
  icon: React.ReactNode;
}> = ({ label, score, unit, rating, description, detail, icon }) => {
  const [expanded, setExpanded] = useState(false);
  const style = RATING_STYLE[rating] ?? RATING_STYLE['No Data'];

  // SVG circular gauge params
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dashOffset = circ - (circ * Math.min(score, 100)) / 100;

  return (
    <div
      className={`glass-card rounded-2xl border border-slate-800/60 p-4 flex flex-col gap-3 hover:border-slate-700 transition shadow-lg ${style.glow}`}
    >
      {/* Top row: gauge + label */}
      <div className="flex items-center gap-3">
        {/* Circular gauge */}
        <div className="relative flex-shrink-0">
          <svg width="68" height="68" className="-rotate-90">
            <circle cx="34" cy="34" r={r} strokeWidth="5" className="stroke-slate-800" fill="none" />
            <circle
              cx="34" cy="34" r={r} strokeWidth="5"
              fill="none"
              className={`${style.ring} transition-all duration-700`}
              strokeLinecap="round"
              strokeDasharray={circ}
              strokeDashoffset={dashOffset}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center rotate-0">
            <span className={`text-[13px] font-black font-mono leading-none ${style.score}`}>
              {score > 0 ? `${score}` : '—'}
            </span>
          </div>
        </div>

        {/* Label + rating */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-slate-400 opacity-80">{icon}</span>
          </div>
          <div className="text-[11px] font-bold text-slate-200 leading-tight">{label}</div>
          <div className="mt-1">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${style.badge}`}>
              {rating}
            </span>
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-[10px] text-slate-500 leading-relaxed">{description}</p>

      {/* Detail toggle */}
      {Object.keys(detail).length > 0 && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-sky-400 transition self-start"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <span>{expanded ? 'Hide' : 'Details'}</span>
        </button>
      )}

      {expanded && (
        <div className="border-t border-slate-800/60 pt-2 space-y-1">
          {Object.entries(detail).filter(([, v]) => v != null).map(([k, v]) => (
            <div key={k} className="flex justify-between items-center text-[10px]">
              <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}</span>
              <span className="font-mono font-bold text-slate-300">
                {typeof v === 'number' ? v.toLocaleString() : String(v)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ─── Technical Details Panel (per-document, lazy-loaded) ──────────────────────

const TechDetailsPanel: React.FC<{ projectId: string }> = ({ projectId }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getProjectTechnicalDetails(projectId)
      .then(d => { if (mounted) { setData(d); setLoading(false); } })
      .catch(e => { if (mounted) { setErr(e.message); setLoading(false); } });
    return () => { mounted = false; };
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-slate-500 text-xs py-4 px-2">
        <RefreshCw className="w-3.5 h-3.5 animate-spin text-sky-400" />
        <span>Loading technical details…</span>
      </div>
    );
  }
  if (err || !data) {
    return <div className="text-xs text-rose-400 py-3 px-2">Failed to load: {err}</div>;
  }

  const { document_metrics: dm, block_type_breakdown: btb, processing: proc, logo_asset, storage, validation_report } = data;
  const totalBlocks = dm?.total_blocks || 1;
  const blockEntries = Object.entries(btb || {}) as [string, any][];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 py-3 px-1">

      {/* ── Left: Metrics + Processing + Storage ── */}
      <div className="space-y-4">

        {/* Document Metrics */}
        <div>
          <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-2">Document Metrics</div>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Pages',            val: dm?.page_count?.toLocaleString()  ?? '—' },
              { label: 'Words',            val: dm?.word_count?.toLocaleString()  ?? '—' },
              { label: 'Chapters',         val: dm?.chapter_count ?? '—' },
              { label: 'Total Blocks',     val: dm?.total_blocks?.toLocaleString() ?? '—' },
              { label: 'Avg Confidence',   val: dm?.overall_avg_confidence ? `${(dm.overall_avg_confidence * 100).toFixed(1)}%` : '—',
                accent: confidenceColor(dm?.overall_avg_confidence ?? 0) },
              { label: 'Low Conf Blocks',  val: dm?.low_confidence_blocks ?? 0,
                accent: dm?.low_confidence_blocks > 0 ? 'text-amber-400' : 'text-emerald-400' },
              { label: 'High Conf Blocks', val: dm?.high_confidence_blocks ?? 0, accent: 'text-emerald-400' },
              { label: 'ML Corrections',   val: dm?.human_corrections ?? 0,
                accent: dm?.human_corrections > 0 ? 'text-sky-400' : 'text-slate-400' },
            ].map(({ label, val, accent }) => (
              <div key={label} className="glass-card rounded-lg p-2.5 border border-slate-800/50">
                <div className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</div>
                <div className={`text-sm font-bold font-mono mt-0.5 ${accent ?? 'text-slate-200'}`}>{val}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline */}
        <div>
          <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-2">Processing Pipeline</div>
          <div className="glass-card rounded-lg border border-slate-800/50 p-3 space-y-2 text-xs">
            {[
              { k: 'Job Status',    v: proc?.status ?? 'Not run',
                accent: proc?.status === 'COMPLETED' ? 'text-emerald-400' : proc?.status === 'FAILED' ? 'text-rose-400' : 'text-sky-300' },
              { k: 'Template',      v: proc?.template_id ?? '—' },
              { k: 'Duration',      v: formatDuration(proc?.duration_seconds ?? 0) },
              { k: 'Throughput',    v: proc?.pages_per_second ? `${proc.pages_per_second} pg/s · ${proc.words_per_second} w/s` : '—' },
              { k: 'Chunks',        v: proc?.total_chunks ? proc.total_chunks.toLocaleString() : '—' },
              { k: 'Job ID',        v: proc?.job_id ? proc.job_id.substring(0, 16) + '…' : '—', mono: true },
              { k: 'Started',       v: proc?.started_at ? new Date(proc.started_at).toLocaleString() : '—' },
              { k: 'Completed',     v: proc?.completed_at ? new Date(proc.completed_at).toLocaleString() : '—' },
            ].map(({ k, v, accent, mono }) => (
              <div key={k} className="flex justify-between items-center py-0.5 border-b border-slate-800/30 last:border-0">
                <span className="text-slate-500">{k}</span>
                <span className={`font-semibold ${mono ? 'font-mono text-[10px]' : ''} ${accent ?? 'text-slate-300'}`}>{v}</span>
              </div>
            ))}
            {proc?.errors?.length > 0 && (
              <div className="mt-1 pt-1 border-t border-rose-500/20">
                <div className="text-[10px] font-bold text-rose-400 mb-1">Errors</div>
                {proc.errors.map((e: string, i: number) => (
                  <div key={i} className="text-[11px] text-rose-300 font-mono">{e}</div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Logo + Storage */}
        <div>
          <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-2">Assets & Storage</div>
          <div className="glass-card rounded-lg border border-slate-800/50 p-3 space-y-2 text-xs">
            {logo_asset ? [
              { k: 'Logo File',   v: logo_asset.filename ?? '—' },
              { k: 'Dimensions',  v: logo_asset.dimensions ?? '—' },
              { k: 'File Size',   v: logo_asset.file_size ?? '—' },
              { k: 'SHA256',      v: logo_asset.sha256_short ?? '—', mono: true },
              { k: 'MIME Type',   v: logo_asset.mime_type ?? '—' },
              { k: 'Valid',       v: logo_asset.is_valid ? '✓ Yes' : '✗ No',
                accent: logo_asset.is_valid ? 'text-emerald-400' : 'text-rose-400' },
            ].map(({ k, v, mono, accent }) => (
              <div key={k} className="flex justify-between items-center py-0.5 border-b border-slate-800/30 last:border-0">
                <span className="text-slate-500">{k}</span>
                <span className={`font-semibold ${mono ? 'font-mono text-[10px]' : ''} ${accent ?? 'text-slate-300'}`}>{v}</span>
              </div>
            )) : (
              <div className="text-slate-500 italic text-[11px]">No publisher logo uploaded</div>
            )}
            {storage && [
              { k: 'Source File',    v: storage.source_file_size ?? '—' },
              { k: 'SQLite DB',      v: storage.db_file_size ?? '—' },
              { k: 'Output Ready',   v: storage.output_exists ? '✓ Available' : '✗ Not yet',
                accent: storage.output_exists ? 'text-emerald-400' : 'text-slate-500' },
            ].map(({ k, v, accent }) => (
              <div key={k} className="flex justify-between items-center py-0.5 border-b border-slate-800/30 last:border-0">
                <span className="text-slate-500">{k}</span>
                <span className={`font-semibold ${accent ?? 'text-slate-300'}`}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Right: Block-Type Breakdown + Validation ── */}
      <div className="space-y-4">
        <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-2">Block-Type Breakdown & ML Confidence</div>

        {blockEntries.length === 0 ? (
          <div className="glass-card rounded-lg border border-slate-800/50 p-4 text-center text-xs text-slate-500 italic">
            No block index data. Run formatting to populate.
          </div>
        ) : (
          <div className="space-y-2">
            {blockEntries.map(([bt, stat]) => {
              const col = blockColor(bt);
              const pct = Math.round((stat.count / totalBlocks) * 100);
              const confPct = Math.round((stat.avg_confidence ?? 1) * 100);
              return (
                <div key={bt} className={`glass-card rounded-lg border ${col.border} p-3 space-y-2`}>
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${col.bg} ${col.text} border ${col.border}`}>
                      {bt.replace(/_/g, ' ')}
                    </span>
                    <div className="flex items-center gap-3 text-[11px]">
                      <span className="text-slate-400 font-mono">{stat.count.toLocaleString()} blocks</span>
                      <span className={`font-bold font-mono ${confidenceColor(stat.avg_confidence ?? 1)}`}>
                        {confPct}% conf
                      </span>
                    </div>
                  </div>
                  {/* Confidence bar */}
                  <div>
                    <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${confidenceBarColor(stat.avg_confidence ?? 1)} transition-all duration-700`}
                        style={{ width: `${confPct}%` }}
                      />
                    </div>
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>{pct}% of document</span>
                    <span className="font-mono">{(stat.total_words ?? 0).toLocaleString()} words</span>
                    {stat.min_confidence != null && (
                      <span className="font-mono">
                        conf {Math.round(stat.min_confidence * 100)}–{Math.round(stat.max_confidence * 100)}%
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Content Preservation */}
        {validation_report && (
          <div>
            <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-2 mt-3">
              Content Preservation Report
            </div>
            <div className={`glass-card rounded-lg border p-3 text-xs space-y-2 ${
              validation_report.is_preserved ? 'border-emerald-500/30' : 'border-amber-500/30'
            }`}>
              <div className={`flex items-center gap-2 font-bold ${validation_report.is_preserved ? 'text-emerald-400' : 'text-amber-400'}`}>
                {validation_report.is_preserved
                  ? <><CheckCircle2 className="w-4 h-4" /> 100% Content Preserved</>
                  : <><AlertTriangle className="w-4 h-4" /> Discrepancies Detected</>
                }
              </div>
              {validation_report.pre_metrics && Object.entries({
                'Input Paragraphs': validation_report.pre_metrics.paragraphs,
                'Output Paragraphs': validation_report.post_metrics?.paragraphs,
                'Input Words': validation_report.pre_metrics.words,
                'Output Words': validation_report.post_metrics?.words,
                'Images': validation_report.pre_metrics.images,
                'Tables': validation_report.pre_metrics.tables,
              }).map(([k, v]) => (
                <div key={k} className="flex justify-between text-slate-400">
                  <span>{k}</span>
                  <span className="font-mono text-slate-300">{v ?? '—'}</span>
                </div>
              ))}
              {validation_report.discrepancies?.length > 0 && (
                <div className="pt-1 border-t border-amber-500/20">
                  <div className="text-amber-400 text-[10px] font-bold mb-1">Discrepancies</div>
                  {validation_report.discrepancies.map((d: string, i: number) => (
                    <div key={i} className="text-[11px] text-amber-300">{d}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Main Component ────────────────────────────────────────────────────────────

export const PerformanceDashboard: React.FC = () => {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await api.getPerformanceAnalytics();
      setData(d);
      setLastRefresh(new Date());
    } catch (e: any) {
      setError(e.message ?? 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const toggleJob = (jobId: string) => {
    setExpandedJobs(prev => {
      const next = new Set(prev);
      next.has(jobId) ? next.delete(jobId) : next.add(jobId);
      return next;
    });
  };

  if (loading && !data) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 border-4 border-sky-500/30 border-t-sky-500 rounded-full animate-spin mx-auto" />
          <p className="text-slate-400 text-sm font-medium">Loading performance analytics…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center glass-card rounded-2xl p-8 border border-rose-500/20 max-w-md w-full">
          <XCircle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
          <h3 className="text-base font-bold text-rose-300 mb-1">Analytics Unavailable</h3>
          <p className="text-xs text-slate-400 mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs font-medium border border-rose-500/30 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { summary: s, job_metrics, block_type_stats, system_metrics, recent_audit_events, storage } = data;
  const qm = data.quality_metrics ?? {};
  const totalBT = Object.values(block_type_stats).reduce((acc, v) => acc + v.count, 0) || 1;
  const maxBTCount = Math.max(...Object.values(block_type_stats).map(v => v.count), 1);

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 max-w-7xl mx-auto w-full">

      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <BarChart2 className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
              Performance Analysis
            </h1>
          </div>
          <p className="text-sm text-slate-400 ml-11">
            Real-time pipeline telemetry, ML confidence analytics, and per-document technical details.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-slate-500 font-mono hidden sm:block">
            Updated {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 text-xs font-medium border border-slate-700 transition active:scale-95"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Quality & Performance Metrics (5 cards) ── */}
      <div>
        <div className="flex items-center gap-2.5 mb-4">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-white" />
          </div>
          <h2 className="text-base font-bold text-slate-200 tracking-tight">Quality &amp; Performance Metrics</h2>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
            5 indicators
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {([
            { key: 'formatting_accuracy',        icon: <FileText className="w-3.5 h-3.5" /> },
            { key: 'structure_recognition_accuracy', icon: <Layers className="w-3.5 h-3.5" /> },
            { key: 'content_preservation',       icon: <Shield className="w-3.5 h-3.5" /> },
            { key: 'processing_efficiency',      icon: <Zap className="w-3.5 h-3.5" /> },
            { key: 'scalability',                icon: <TrendingUp className="w-3.5 h-3.5" /> },
          ] as { key: string; icon: React.ReactNode }[]).map(({ key, icon }) => {
            const m = qm[key];
            if (!m) return (
              <div key={key} className="glass-card rounded-2xl border border-slate-800/40 p-4 flex items-center justify-center text-slate-600 text-xs italic">
                No data yet
              </div>
            );
            return (
              <QualityMetricCard
                key={key}
                label={m.label}
                score={m.score}
                unit={m.unit}
                rating={m.rating}
                description={m.description}
                detail={m.detail}
                icon={icon}
              />
            );
          })}
        </div>
      </div>

      {/* ── KPI Summary Cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard icon={<FileText className="w-4 h-4" />}    label="Documents"  value={s.total_documents}            sub="Formatted projects"          accent="text-sky-400" />
        <KpiCard icon={<BookOpen className="w-4 h-4" />}    label="Total Pages" value={formatNumber(s.total_pages)} sub="Across all docs"              accent="text-indigo-400" />
        <KpiCard icon={<Activity className="w-4 h-4" />}    label="Total Words" value={formatNumber(s.total_words)} sub="Words extracted"              accent="text-violet-400" />
        <KpiCard icon={<Layers className="w-4 h-4" />}      label="Chapters"    value={s.total_chapters}            sub="Structure nodes"             accent="text-purple-400" />
        <KpiCard icon={<CheckCircle2 className="w-4 h-4" />} label="Success Rate" value={`${s.success_rate}%`}     sub={`${s.completed_jobs}/${s.total_jobs} jobs`}
          accent={s.success_rate >= 90 ? 'text-emerald-400' : s.success_rate >= 70 ? 'text-amber-400' : 'text-rose-400'} />
        <KpiCard icon={<Clock className="w-4 h-4" />}       label="Avg Time"    value={formatDuration(s.avg_processing_seconds)} sub="Per document" accent="text-orange-400" />
      </div>

      {/* ── Two-column: Block Distribution + System ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Block-Type Distribution */}
        <div className="glass-card rounded-2xl p-5 border border-slate-800/60">
          <SectionTitle icon={<Layers className="w-4 h-4" />} title="Global Block-Type Distribution" badge={`${Object.keys(block_type_stats).length} types`} />
          {Object.keys(block_type_stats).length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-xs">
              <Database className="w-8 h-8 mx-auto mb-2 text-slate-700" />
              <p>No block index data. Process a document to populate.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {(Object.entries(block_type_stats) as [string, BlockTypeStat][])
                .sort((a, b) => b[1].count - a[1].count)
                .map(([bt, stat]) => {
                  const col = blockColor(bt);
                  const pct = (stat.count / totalBT) * 100;
                  const barPct = (stat.count / maxBTCount) * 100;
                  const confPct = Math.round((stat.avg_confidence ?? 1) * 100);
                  return (
                    <div key={bt} className="flex items-center gap-3 group">
                      <div className={`w-28 text-[10px] font-bold uppercase tracking-wide px-1.5 py-1 rounded text-center flex-shrink-0 ${col.bg} ${col.text} border ${col.border} group-hover:opacity-100 opacity-90 transition`}>
                        {bt.replace(/_/g, ' ')}
                      </div>
                      <div className="flex-1 h-5 rounded-full bg-slate-800/60 overflow-hidden relative">
                        <div
                          className={`h-full rounded-full ${confidenceBarColor(stat.avg_confidence ?? 1)} transition-all duration-700`}
                          style={{ width: `${barPct}%` }}
                        />
                        <span className="absolute right-2 top-0 h-full flex items-center text-[10px] font-mono text-slate-300 font-semibold">
                          {stat.count.toLocaleString()}
                        </span>
                      </div>
                      <div className="w-24 text-right space-y-0.5 flex-shrink-0">
                        <div className="text-[10px] font-mono text-slate-400">{pct.toFixed(1)}%</div>
                        <div className={`text-[10px] font-mono font-bold ${confidenceColor(stat.avg_confidence ?? 1)}`}>
                          {confPct}% conf
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>

        {/* System Telemetry + Storage */}
        <div className="space-y-5">
          {system_metrics && (
            <div className="glass-card rounded-2xl p-5 border border-slate-800/60">
              <SectionTitle icon={<Cpu className="w-4 h-4" />} title="System Telemetry" />
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'CPU Usage',    value: `${system_metrics.cpu_percent ?? 0}%`,
                    accent: (system_metrics.cpu_percent ?? 0) > 80 ? 'text-rose-400' : 'text-sky-400',
                    barPct: system_metrics.cpu_percent ?? 0, barCol: 'bg-sky-500' },
                  { label: 'RAM Usage',    value: `${system_metrics.ram_percent ?? 0}%`,
                    accent: (system_metrics.ram_percent ?? 0) > 85 ? 'text-rose-400' : 'text-indigo-400',
                    barPct: system_metrics.ram_percent ?? 0, barCol: 'bg-indigo-500' },
                ].map(({ label, value, accent, barPct, barCol }) => (
                  <div key={label} className="glass-card rounded-xl p-3 border border-slate-800/40">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{label}</div>
                    <div className={`text-2xl font-black font-mono ${accent}`}>{value}</div>
                    <div className="h-1.5 rounded-full bg-slate-800 mt-2 overflow-hidden">
                      <div className={`h-full rounded-full ${barCol} transition-all`} style={{ width: `${barPct}%` }} />
                    </div>
                  </div>
                ))}
                <div className="glass-card rounded-xl p-3 border border-slate-800/40">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">CPU Workers</div>
                  <div className="text-2xl font-black font-mono text-emerald-400">{system_metrics.cpu_workers ?? '—'}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Parallel cores</div>
                </div>
                <div className="glass-card rounded-xl p-3 border border-slate-800/40">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">RAM Used</div>
                  <div className="text-lg font-black font-mono text-violet-400">
                    {system_metrics.ram_used_gb != null
                      ? `${system_metrics.ram_used_gb.toFixed(1)}/${system_metrics.ram_total_gb?.toFixed(1)} GB`
                      : '—'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {storage && (
            <div className="glass-card rounded-2xl p-5 border border-slate-800/60">
              <SectionTitle icon={<HardDrive className="w-4 h-4" />} title="Storage Engine" />
              <div className="space-y-2 text-xs">
                {[
                  { k: 'Engine',        v: storage.engine ?? '—' },
                  { k: 'Database',      v: storage.info?.database ?? '—' },
                  { k: 'Connected',     v: storage.connected ? '✓ Connected' : '✗ Offline',
                    accent: storage.connected ? 'text-emerald-400' : 'text-rose-400' },
                  { k: 'Total Records', v: storage.total_records?.toLocaleString() ?? '—' },
                ].map(({ k, v, accent }) => (
                  <div key={k} className="flex justify-between items-center py-1.5 border-b border-slate-800/40 last:border-0">
                    <span className="text-slate-500">{k}</span>
                    <span className={`font-semibold font-mono ${accent ?? 'text-slate-300'}`}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Per-Document Job Table ── */}
      <div className="glass-card rounded-2xl p-5 border border-slate-800/60">
        <SectionTitle
          icon={<TrendingUp className="w-4 h-4" />}
          title="Document Processing History"
          badge={`${job_metrics.length} jobs`}
        />

        {job_metrics.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            <FileText className="w-8 h-8 mx-auto mb-2 text-slate-700" />
            <p className="font-semibold text-slate-400">No formatting jobs found.</p>
            <p className="mt-1">Upload and format a document to see processing analytics here.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {job_metrics.map((job) => {
              const isExpanded = expandedJobs.has(job.job_id);
              return (
                <div key={job.job_id} className="glass-card rounded-xl border border-slate-800/50 overflow-hidden transition">
                  {/* Row header — clickable */}
                  <div
                    role="button"
                    className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 cursor-pointer hover:bg-slate-800/20 transition select-none"
                    onClick={() => toggleJob(job.job_id)}
                  >
                    <div className="flex-shrink-0 text-slate-500">
                      {isExpanded
                        ? <ChevronDown className="w-4 h-4 text-sky-400" />
                        : <ChevronRight className="w-4 h-4" />
                      }
                    </div>

                    {/* Name + status */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-slate-100 text-sm truncate">{job.project_name}</span>
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${statusColor(job.status)}`}>
                          {job.status}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500 border border-slate-700 px-1.5 py-0.5 rounded">
                          {job.template_id}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-600 font-mono mt-0.5 truncate">
                        {job.job_id} · {job.created_at ? new Date(job.created_at).toLocaleString() : '—'}
                      </div>
                    </div>

                    {/* Metric pills */}
                    <div className="flex items-center gap-4 flex-shrink-0">
                      {[
                        { val: formatNumber(job.pages),          label: 'pages',    accent: 'text-sky-400' },
                        { val: formatNumber(job.words),          label: 'words',    accent: 'text-indigo-400' },
                        { val: formatDuration(job.duration_seconds), label: 'time', accent: 'text-violet-400' },
                        { val: job.pages_per_second > 0 ? `${job.pages_per_second}` : '—', label: 'pg/s', accent: 'text-emerald-400' },
                        { val: job.total_chunks.toString(),      label: 'chunks',   accent: 'text-orange-400', hidden: true },
                      ].map(({ val, label, accent, hidden }) => (
                        <div key={label} className={`text-center ${hidden ? 'hidden lg:block' : ''}`}>
                          <div className={`text-sm font-black font-mono ${accent}`}>{val}</div>
                          <div className="text-[9px] text-slate-500 uppercase tracking-wider">{label}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Expanded Technical Details */}
                  {isExpanded && (
                    <div className="border-t border-slate-800/60 px-4 pb-4">
                      <div className="flex items-center gap-1.5 py-3">
                        <Target className="w-3.5 h-3.5 text-indigo-400" />
                        <span className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider">
                          Technical Details — {job.project_name}
                        </span>
                      </div>
                      <TechDetailsPanel projectId={job.project_id} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Recent Audit Events ── */}
      {recent_audit_events.length > 0 && (
        <div className="glass-card rounded-2xl p-5 border border-slate-800/60">
          <SectionTitle
            icon={<Shield className="w-4 h-4" />}
            title="Recent Audit Activity"
            badge={`${recent_audit_events.length} events`}
          />
          <div className="space-y-1 max-h-52 overflow-y-auto pr-1">
            {recent_audit_events.map((ev, i) => (
              <div key={i} className="flex items-center gap-3 text-xs py-1.5 px-2 rounded-lg hover:bg-slate-800/30 transition">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-500 flex-shrink-0" />
                <span className="text-sky-300 font-semibold font-mono w-44 flex-shrink-0 truncate">{ev.event_type}</span>
                <span className="text-slate-500 flex-1 truncate font-mono text-[10px]">{ev.project_id}</span>
                <span className="text-slate-600 flex-shrink-0 font-mono text-[10px]">
                  {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bottom padding */}
      <div className="h-4" />
    </div>
  );
};
