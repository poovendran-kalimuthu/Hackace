import { BookTemplate, JobStatus, Project, ReviewItem } from '../types';

const API_BASE = '/api';

export const api = {
  // Projects
  async getProjects(): Promise<Project[]> {
    const res = await fetch(`${API_BASE}/projects`);
    if (!res.ok) throw new Error('Failed to load projects');
    return res.json();
  },

  async getProject(id: string): Promise<Project> {
    const res = await fetch(`${API_BASE}/projects/${id}`);
    if (!res.ok) throw new Error('Failed to load project');
    return res.json();
  },

  async createProject(name: string, description: string = '', template_id: string = 'book'): Promise<Project> {
    const res = await fetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description, template_id }),
    });
    if (!res.ok) throw new Error('Failed to create project');
    return res.json();
  },

  async deleteProject(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/projects/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete project');
  },

  async duplicateProject(id: string, newName: string): Promise<Project> {
    const res = await fetch(`${API_BASE}/projects/${id}/duplicate?new_name=${encodeURIComponent(newName)}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to duplicate project');
    return res.json();
  },

  async uploadManuscript(projectId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/projects/${projectId}/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to upload manuscript' }));
      throw new Error(err.detail || 'Failed to upload manuscript');
    }
    return res.json();
  },

  // Mandatory Publisher Logo Operations
  async uploadLogo(projectId: string, file: File): Promise<{ success: boolean; logo: any }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/projects/${projectId}/logo`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to upload logo' }));
      throw new Error(err.detail || 'Failed to upload logo');
    }
    return res.json();
  },

  async getLogo(projectId: string): Promise<{ has_logo: boolean; logo: any }> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/logo`);
    if (!res.ok) return { has_logo: false, logo: null };
    return res.json();
  },

  async deleteLogo(projectId: string): Promise<void> {
    await fetch(`${API_BASE}/projects/${projectId}/logo`, { method: 'DELETE' });
  },

  async getComparison(projectId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/comparison`);
    if (!res.ok) throw new Error('Failed to fetch comparison report');
    return res.json();
  },

  getExportUrl(projectId: string): string {
    return `${API_BASE}/projects/${projectId}/export`;
  },

  // Jobs
  async startJob(projectId: string, templateId: string): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template_id: templateId }),
    });
    if (!res.ok) throw new Error('Failed to start formatting job');
    return res.json();
  },

  async getJobStatus(jobId: string): Promise<JobStatus> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!res.ok) throw new Error('Failed to load job status');
    return res.json();
  },

  async pauseJob(jobId: string): Promise<void> {
    await fetch(`${API_BASE}/jobs/${jobId}/pause`, { method: 'POST' });
  },

  async resumeJob(jobId: string): Promise<void> {
    await fetch(`${API_BASE}/jobs/${jobId}/resume`, { method: 'POST' });
  },

  async cancelJob(jobId: string): Promise<void> {
    await fetch(`${API_BASE}/jobs/${jobId}/cancel`, { method: 'POST' });
  },

  // Review Queue
  async getReviewQueue(projectId: string): Promise<ReviewItem[]> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/review`);
    if (!res.ok) throw new Error('Failed to load review items');
    return res.json();
  },

  async submitCorrection(projectId: string, blockId: string, correctedType: string, predictedType: string, originalText: string): Promise<void> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/review/correct`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        block_id: blockId,
        corrected_type: correctedType,
        predicted_type: predictedType,
        original_text: originalText,
      }),
    });
    if (!res.ok) throw new Error('Failed to submit correction');
  },

  // Templates
  async getTemplates(): Promise<BookTemplate[]> {
    const res = await fetch(`${API_BASE}/templates`);
    if (!res.ok) throw new Error('Failed to load templates');
    return res.json();
  },

  async saveTemplate(template: BookTemplate): Promise<BookTemplate> {
    const res = await fetch(`${API_BASE}/templates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(template),
    });
    if (!res.ok) throw new Error('Failed to save template');
    return res.json();
  },

  // Preview & Search
  async getPagePreview(projectId: string, pageNumber: number): Promise<{ page_number: number; total_pages: number; blocks: any[] }> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/preview/page/${pageNumber}`);
    if (!res.ok) throw new Error('Failed to load page preview');
    return res.json();
  },

  async searchDocument(projectId: string, query: string): Promise<any[]> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error('Search failed');
    return res.json();
  },

  async getStructure(projectId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/structure`);
    if (!res.ok) throw new Error('Failed to load document structure');
    return res.json();
  },

  // Diagnostics
  async getDiagnostics(): Promise<any> {
    const res = await fetch(`${API_BASE}/diagnostics`);
    if (!res.ok) throw new Error('Failed to load diagnostics');
    return res.json();
  },

  // Synthetic Generator
  async generateSample(pages: number, projectId?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/generator/sample`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pages, project_id: projectId }),
    });
    if (!res.ok) throw new Error('Failed to generate sample');
    return res.json();
  },
};
