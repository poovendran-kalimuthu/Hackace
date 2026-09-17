import { create } from 'zustand';
import { BookTemplate, JobStatus, Project } from '../types';
import { api } from '../services/api';

export type AppView = 'dashboard' | 'project' | 'review' | 'template-editor' | 'preview';

interface AppState {
  currentView: AppView;
  projects: Project[];
  activeProject: Project | null;
  templates: BookTemplate[];
  activeTemplate: BookTemplate | null;
  activeJob: JobStatus | null;
  isProcessing: boolean;
  diagnostics: any | null;

  setCurrentView: (view: AppView) => void;
  loadProjects: () => Promise<void>;
  selectProject: (project: Project) => void;
  loadTemplates: () => Promise<void>;
  selectTemplate: (template: BookTemplate) => void;
  setActiveJob: (job: JobStatus | null) => void;
  fetchDiagnostics: () => Promise<void>;
  connectWebSocket: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  currentView: 'dashboard',
  projects: [],
  activeProject: null,
  templates: [],
  activeTemplate: null,
  activeJob: null,
  isProcessing: false,
  diagnostics: null,

  setCurrentView: (view) => set({ currentView: view }),

  loadProjects: async () => {
    try {
      const projects = await api.getProjects();
      set({ projects });
    } catch (e) {
      console.error('Failed to load projects', e);
    }
  },

  selectProject: (project) => {
    set({ activeProject: project });
  },

  loadTemplates: async () => {
    try {
      const templates = await api.getTemplates();
      set({
        templates,
        activeTemplate: templates[0] || null,
      });
    } catch (e) {
      console.error('Failed to load templates', e);
    }
  },

  selectTemplate: (template) => set({ activeTemplate: template }),

  setActiveJob: (job) => {
    const isProc = job !== null && !['COMPLETED', 'FAILED', 'CANCELLED'].includes(job.status);
    set({ activeJob: job, isProcessing: isProc });
  },

  fetchDiagnostics: async () => {
    try {
      const diagnostics = await api.getDiagnostics();
      set({ diagnostics });
    } catch (e) {
      // offline silent
    }
  },

  connectWebSocket: () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/ws/telemetry`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.job_id) {
          const isProc = !['COMPLETED', 'FAILED', 'CANCELLED'].includes(data.status);
          set({
            activeJob: data,
            isProcessing: isProc,
            diagnostics: data.telemetry || get().diagnostics,
          });
        }
      } catch (e) {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      // Suppress unhandled error logs on reconnect
    };

    ws.onclose = () => {
      // Reconnect after 3s
      setTimeout(() => {
        get().connectWebSocket();
      }, 3000);
    };
  },
}));
