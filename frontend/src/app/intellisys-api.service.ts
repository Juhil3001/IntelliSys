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
  alert_webhook_url?: string | null;
  github_app_installation_id?: string | null;
}

/** Mirrors backend ScanRunOut / scan run JSON. */
export interface ScanRunOut {
  id: number;
  project_id: number;
  status: string;
  source_root: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

export interface ApiListRow {
  id: number;
  method: string;
  endpoint: string;
  name?: string | null;
}

export interface IssueListRow {
  id: number;
  type: string;
  description: string;
  severity: string | null;
  resolved?: boolean;
  source?: string;
  external_url?: string | null;
  api_id?: number | null;
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

  /** Clear active project (e.g. after deleting the current project). */
  clearProjectId(): void {
    this.projectId.set(null);
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('intellisys_project_id');
    }
  }

  deleteProject(id: number) {
    return this.http.delete<void>(`${this._base}/projects/${id}`);
  }

  patchProject(
    id: number,
    body: { alert_webhook_url?: string | null; github_app_installation_id?: string | null }
  ) {
    return this.http.patch<Project>(`${this._base}/projects/${id}`, body);
  }

  getErrorSummary(projectId: number, hours = 24) {
    return this.http.get<{
      project_id: number;
      hours: number;
      total_calls: number;
      error_count: number;
      error_rate: number;
    }>(`${this._base}/monitor/error-summary?project_id=${projectId}&hours=${hours}`);
  }

  getMetrics(projectId: number, hours = 168) {
    return this.http.get<
      {
        api_id: number;
        call_count: number;
        error_count: number;
        error_rate: number;
        avg_response_ms: number;
        p95_response_ms: number;
      }[]
    >(`${this._base}/monitor/metrics?project_id=${projectId}&hours=${hours}`);
  }

  getTimeline(projectId: number) {
    return this.http.get<{
      project_id: number;
      snapshots: {
        snapshot_id: number;
        created_at: string | null;
        scan_run_id: number;
        file_count: number;
        api_count: number;
      }[];
      recurring_patterns: {
        issue_type: string;
        fingerprint: string;
        hit_count: number;
        last_seen_at: string | null;
      }[];
    }>(`${this._base}/projects/${projectId}/timeline`);
  }

  getProjectGraph(projectId: number) {
    return this.http.get<Record<string, unknown>>(`${this._base}/projects/${projectId}/graph`);
  }

  exportIssueToGithub(issueId: number) {
    return this.http.post<{
      html_url: string | null;
      github_number: number;
      issue_id: number;
    }>(`${this._base}/issues/${issueId}/github-export`, {});
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
    return this.http.post<ScanRunOut>(`${this._base}/scans`, {
      project_id: projectId,
      source_root: sourceRoot ?? null,
      with_snapshot: withSnapshot,
    });
  }

  patchIssue(issueId: number, body: { resolved: boolean }) {
    return this.http.patch<IssueListRow>(`${this._base}/issues/${issueId}`, body);
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
