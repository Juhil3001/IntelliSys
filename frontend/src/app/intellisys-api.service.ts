import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { environment } from '../environments/environment';

export interface Project {
  id: number;
  name: string;
  root_path: string;
  github_repo_url?: string | null;
  default_branch?: string | null;
  last_commit_sha?: string | null;
  last_sync_at?: string | null;
}

@Injectable({ providedIn: 'root' })
export class IntellisysApiService {
  private readonly _base = environment.apiBaseUrl;
  /** Active project for API calls that need `project_id`. */
  projectId = signal<number | null>(this.readStoredId());

  constructor(private http: HttpClient) {}

  withProjectHeaders(): HttpHeaders {
    const id = this.projectId();
    return id == null
      ? new HttpHeaders()
      : new HttpHeaders({ 'X-Project-Id': String(id) });
  }

  setProjectId(id: number) {
    this.projectId.set(id);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('intellisys_project_id', String(id));
    }
  }

  readStoredId(): number | null {
    if (typeof localStorage === 'undefined') return null;
    const s = localStorage.getItem('intellisys_project_id');
    if (s == null) return null;
    const n = parseInt(s, 10);
    return Number.isNaN(n) ? null : n;
  }

  health() {
    return this.http.get<{ status: string }>(`${this._base}/health`);
  }

  listProjects() {
    return this.http.get<Project[]>(`${this._base}/projects`);
  }

  createProject(body: {
    name: string;
    root_path?: string;
    github_repo_url?: string;
    default_branch?: string;
  }) {
    return this.http.post<Project>(`${this._base}/projects`, body);
  }

  startScan(projectId: number, sourceRoot?: string, withSnapshot = true) {
    return this.http.post(`${this._base}/scans`, {
      project_id: projectId,
      source_root: sourceRoot ?? null,
      with_snapshot: withSnapshot,
    });
  }

  syncAndScan(projectId: number, withSnapshot = true) {
    const q = withSnapshot ? 'true' : 'false';
    return this.http.post<Record<string, unknown>>(
      `${this._base}/projects/${projectId}/sync-and-scan?with_snapshot=${q}`,
      {}
    );
  }

  recompute(projectId: number) {
    return this.http.post(`${this._base}/insights/recompute?project_id=${projectId}`, {});
  }

  listApis(projectId: number) {
    return this.http.get<unknown[]>(`${this._base}/apis?project_id=${projectId}`);
  }

  listIssues(projectId: number) {
    return this.http.get<unknown[]>(`${this._base}/issues?project_id=${projectId}`);
  }

  getAlerts(projectId: number) {
    return this.http.get<{
      project_id: number;
      summary: {
        critical: number;
        high: number;
        medium: number;
        low: number;
        total: number;
      };
      items: unknown[];
    }>(`${this._base}/alerts?project_id=${projectId}`);
  }

  generateAi(projectId: number) {
    return this.http.post<{
      id: number;
      summary: string;
      recommendation: string;
      model: string;
    }>(`${this._base}/ai/generate?project_id=${projectId}`, {});
  }

  chatMessage(projectId: number, message: string) {
    return this.http.post<{ reply: string }>(`${this._base}/chat/${projectId}/message`, {
      message,
    });
  }
}
