import React, { useEffect, useState } from 'react';
import { Plus, FolderPlus, BookOpen, Clock, FileText, Trash2, Copy, Sparkles, Layout, ArrowRight } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';
import { Project } from '../types';

export const Dashboard: React.FC = () => {
  const { projects, loadProjects, selectProject, setCurrentView, templates, loadTemplates } = useAppStore();
  const [showNewModal, setShowNewModal] = useState(false);
  const [showGenModal, setShowGenModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState('classic_novel');
  const [genPages, setGenPages] = useState<number>(100);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    loadProjects();
    loadTemplates();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      const proj = await api.createProject(newProjectName, newProjectDesc, selectedTemplateId);
      await loadProjects();
      selectProject(proj);
      setShowNewModal(false);
      setNewProjectName('');
      setNewProjectDesc('');
      setCurrentView('project');
    } catch (err) {
      alert('Failed to create project');
    }
  };

  const handleGenerateSample = async () => {
    setIsGenerating(true);
    try {
      const proj = await api.createProject(`Benchmark Test (${genPages} Pages)`, `Synthetic benchmark manuscript with ${genPages} pages.`);
      await api.generateSample(genPages, proj.id);
      await loadProjects();
      selectProject(proj);
      setShowGenModal(false);
      setCurrentView('project');
    } catch (err) {
      alert('Failed to generate benchmark document');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleOpenProject = (proj: Project) => {
    selectProject(proj);
    setCurrentView('project');
  };

  const handleDeleteProject = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this project?')) {
      await api.deleteProject(id);
      await loadProjects();
    }
  };

  const handleDuplicateProject = async (e: React.MouseEvent, id: string, name: string) => {
    e.stopPropagation();
    await api.duplicateProject(id, `${name} (Copy)`);
    await loadProjects();
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 max-w-7xl mx-auto w-full">
      {/* Hero Welcome & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
            Intelligent Document & Book Formatter
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Offline structural manuscript analysis, smart pagination, and professional layout automation for up to 10,000+ pages.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowGenModal(true)}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span>Generate Benchmark (100–10k pgs)</span>
          </button>

          <button
            onClick={() => setShowNewModal(true)}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-sky-500/20 transition transform active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Projects Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-200 flex items-center space-x-2">
            <BookOpen className="w-4 h-4 text-sky-400" />
            <span>Recent Projects</span>
          </h2>
          <span className="text-xs text-slate-400">{projects.length} Total</span>
        </div>

        {projects.length === 0 ? (
          <div className="glass-card rounded-2xl p-12 text-center border border-dashed border-slate-800">
            <FolderPlus className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-300">No Projects Found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
              Create a new project or generate a synthetic 100 to 10,000-page test document to explore the formatting pipeline.
            </p>
            <button
              onClick={() => setShowNewModal(true)}
              className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-white text-xs font-medium inline-flex items-center space-x-2 transition"
            >
              <Plus className="w-4 h-4" />
              <span>Create Your First Project</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {projects.map((proj) => (
              <div
                key={proj.id}
                onClick={() => handleOpenProject(proj)}
                className="glass-card rounded-xl p-5 cursor-pointer flex flex-col justify-between transition group relative"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 mb-3">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition">
                      <button
                        title="Duplicate"
                        onClick={(e) => handleDuplicateProject(e, proj.id, proj.name)}
                        className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 transition"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                      <button
                        title="Delete"
                        onClick={(e) => handleDeleteProject(e, proj.id)}
                        className="p-1 rounded-md text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <h3 className="font-semibold text-slate-100 text-base group-hover:text-sky-300 transition line-clamp-1">
                    {proj.name}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2 min-h-[32px]">
                    {proj.description || 'No description provided.'}
                  </p>
                </div>

                <div className="pt-4 mt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center space-x-3">
                    <span className="font-mono text-slate-300 font-medium">
                      {proj.page_count ? `${proj.page_count.toLocaleString()} pgs` : 'Not analyzed'}
                    </span>
                    {proj.chapter_count > 0 && (
                      <span className="text-slate-500">• {proj.chapter_count} chaps</span>
                    )}
                  </div>

                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                    proj.status === 'EXPORTED'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : proj.status === 'ANALYZED'
                      ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}>
                    {proj.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Template Presets Gallery */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-200 flex items-center space-x-2">
            <Layout className="w-4 h-4 text-indigo-400" />
            <span>Built-in Formatting Templates</span>
          </h2>
          <button
            onClick={() => setCurrentView('template-editor')}
            className="text-xs text-sky-400 hover:text-sky-300 flex items-center space-x-1"
          >
            <span>Open Studio</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {templates.map((tpl) => (
            <div
              key={tpl.id}
              onClick={() => {
                useAppStore.getState().selectTemplate(tpl);
                setCurrentView('template-editor');
              }}
              className="glass-card rounded-xl p-4 cursor-pointer hover:border-indigo-500/40 transition flex flex-col justify-between"
            >
              <div>
                <span className="text-[10px] uppercase tracking-wider font-semibold text-indigo-400">
                  {tpl.category}
                </span>
                <h4 className="font-semibold text-slate-200 text-sm mt-1">{tpl.name}</h4>
                <p className="text-xs text-slate-400 mt-1 line-clamp-3">
                  {tpl.description}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] text-slate-400 flex justify-between">
                <span>{tpl.page.width}" × {tpl.page.height}"</span>
                <span className="text-indigo-300 font-serif font-medium">
                  {tpl.styles.body?.font_family || 'Garamond'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* New Project Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="glass-panel w-full max-w-md rounded-2xl p-6 border border-slate-800 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Create New Project</h3>
            <p className="text-xs text-slate-400 mb-5">
              Initialize a clean workspace for your manuscript analysis and publication formatting.
            </p>

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., The Quantum Odyssey"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-sky-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Brief notes about the book or genre..."
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-sky-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Default Template Preset</label>
                <select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-sky-500 transition"
                >
                  {templates.map((tpl) => (
                    <option key={tpl.id} value={tpl.id}>
                      {tpl.name} ({tpl.page.width}x{tpl.page.height} in)
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end space-x-2.5 pt-3">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-white text-xs font-semibold shadow-md shadow-sky-500/20 transition"
                >
                  Create & Open
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Benchmark Generator Modal */}
      {showGenModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 z-50">
          <div className="glass-panel w-full max-w-md rounded-2xl p-6 border border-slate-800 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1 flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-amber-400" />
              <span>Synthetic Benchmark Generator</span>
            </h3>
            <p className="text-xs text-slate-400 mb-5">
              Select document scale to validate high-throughput chunking, memory control, and crash recovery.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-2">Target Volume</label>
                <div className="grid grid-cols-3 gap-2">
                  {[100, 500, 1000, 5000, 10000].map((p) => (
                    <button
                      key={p}
                      onClick={() => setGenPages(p)}
                      className={`py-2 px-3 rounded-xl text-xs font-medium border transition ${
                        genPages === p
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-semibold'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {p.toLocaleString()} Pages
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-400 space-y-1">
                <div className="flex justify-between">
                  <span>Estimated Words:</span>
                  <span className="font-mono text-slate-200">{(genPages * 280).toLocaleString()} words</span>
                </div>
                <div className="flex justify-between">
                  <span>Estimated Chapters:</span>
                  <span className="font-mono text-slate-200">~{Math.max(3, Math.round(genPages / 15))} chapters</span>
                </div>
                <div className="flex justify-between">
                  <span>Elements Included:</span>
                  <span className="text-slate-300">Chapters, Headings, Quotes, Tables, Captions</span>
                </div>
              </div>

              <div className="flex items-center justify-end space-x-2.5 pt-3">
                <button
                  type="button"
                  disabled={isGenerating}
                  onClick={() => setShowGenModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleGenerateSample}
                  disabled={isGenerating}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white text-xs font-semibold shadow-md shadow-amber-500/20 transition flex items-center space-x-2"
                >
                  {isGenerating ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Generating Document...</span>
                    </>
                  ) : (
                    <span>Generate & Open</span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
