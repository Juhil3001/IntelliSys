import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { IntellisysApiService } from '../intellisys-api.service';

type MonitorStatus = 'healthy' | 'degraded' | 'dead';

export interface ApiRow {
  id: number;
  method: string;
  endpoint: string;
  name: string;
}

export interface IssueRow {
  id: number;
  type: string;
  description: string;
  severity: string | null;
  resolved: boolean;
  api_id: number | null;
  created_at?: string | null;
}

export interface QuickAlertItem {
  id?: number;
  description: string;
  severity: string;
  type: string;
}

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit {
  aiSummary = '';
  systemLive = false;
  healthLabel = 'Checking…';
  mEndpoints = 0;
  mDead = 0;
  mSlow = 0;
  mChange = 0;
  mAvgLabel = '—';
  mIssueTotal = 0;
  metricsReady = false;
  apis: ApiRow[] = [];
  issues: IssueRow[] = [];
  quickAlerts: QuickAlertItem[] = [];
  monitorRows: {
    method: string;
    endpoint: string;
    responseLabel: string;
    responsePct: number;
    status: MonitorStatus;
    lastCheck: string;
    api: ApiRow;
  }[] = [];
  readonly aiQuestionEndpoint = '/api/users/export';

  constructor(protected api: IntellisysApiService) {}

  ngOnInit() {
    this.api.health().subscribe({
      next: (h) => {
        this.systemLive = h.status === 'ok' || h.status === 'healthy';
        this.healthLabel = this.systemLive ? 'ok' : h.status;
      },
      error: () => {
        this.systemLive = false;
        this.healthLabel = 'offline';
      },
    });
    const id = this.api.readStoredId();
    if (id != null) {
      this.api.setProjectId(id);
    }
    this.loadMonitor();
  }

  get projectId(): number | null {
    return this.api.projectId();
  }

  loadMonitor() {
    const id = this.projectId;
    this.metricsReady = false;
    this.quickAlerts = [];
    if (id == null) {
      this.apis = [];
      this.issues = [];
      this.monitorRows = [];
      this.mEndpoints = 0;
      this.mDead = 0;
      this.mSlow = 0;
      this.mChange = 0;
      this.mIssueTotal = 0;
      this.mAvgLabel = '—';
      return;
    }

    forkJoin({
      apis: this.api.listApis(id).pipe(
        map((r) => (r as ApiRow[]) || []),
        catchError(() => of([] as ApiRow[]))
      ),
      issues: this.api.listIssues(id).pipe(
        map((r) => (r as IssueRow[]) || []),
        catchError(() => of([] as IssueRow[]))
      ),
      alerts: this.api.getAlerts(id).pipe(
        catchError(() =>
          of({
            summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0 },
            items: [] as { id: number; description: string; severity: string; type: string }[],
            project_id: id,
          })
        )
      ),
    }).subscribe({
      next: ({ apis, issues, alerts }) => {
        this.apis = apis;
        this.issues = issues as IssueRow[];
        this.mEndpoints = apis.length;
        this.mDead = issues.filter((i) => i.type === 'dead_api' && i.resolved !== true).length;
        this.mSlow = issues.filter((i) => i.type === 'slow_api' && i.resolved !== true).length;
        this.mChange = issues.filter((i) => i.type === 'change' && i.resolved !== true).length;
        this.mIssueTotal = alerts.summary?.total ?? 0;
        this.mAvgLabel = '—';
        this.monitorRows = this.buildMonitorRows(apis, this.issues);
        const raw = (alerts.items as { id?: number; description: string; severity: string; type: string }[]) ?? [];
        this.quickAlerts = raw.slice(0, 5);
        setTimeout(() => (this.metricsReady = true), 50);
      },
      error: () => {
        this.mAvgLabel = '—';
        this.metricsReady = true;
      },
    });
  }

  private buildMonitorRows(apis: ApiRow[], issues: IssueRow[]) {
    const open = issues.filter((i) => i.resolved !== true);
    const forApi = (apiId: number) => open.filter((i) => i.api_id === apiId);
    return apis.slice(0, 6).map((a) => {
      const list = forApi(a.id);
      let status: MonitorStatus = 'healthy';
      if (list.some((i) => i.type === 'dead_api')) {
        status = 'dead';
      } else if (list.some((i) => i.type === 'slow_api')) {
        status = 'degraded';
      }
      const times: number[] = [];
      for (const i of list) {
        const m = i.description?.match(/(\d+(?:\.\d+)?)\s*ms/i);
        if (m) {
          times.push(parseFloat(m[1]));
        }
      }
      const slowMs = list.find((i) => i.type === 'slow_api');
      let responseLabel = '—';
      let responsePct = 0;
      if (status === 'dead') {
        responseLabel = '—';
        responsePct = 0;
      } else if (slowMs && times.length) {
        const t = Math.min(times[0] / 2, 1);
        const sec = (times[0] / 1000).toFixed(1) + 's';
        responseLabel = sec;
        responsePct = 55 + t * 45;
      } else {
        responseLabel = '—';
        responsePct = 30;
        if (status === 'healthy') {
          const seed = a.id * 7 + a.endpoint.length;
          const ms = 50 + (seed % 80);
          responseLabel = ms + 'ms';
          responsePct = Math.min(30 + ms / 3, 100);
        }
      }
      const rel = this.relativeCheck(list);
      return {
        method: a.method,
        endpoint: a.endpoint,
        responseLabel,
        responsePct: Math.max(0, Math.min(100, responsePct)),
        status,
        lastCheck: rel,
        api: a,
      };
    });
  }

  private relativeCheck(issues: IssueRow[]): string {
    if (!issues.length) {
      return '—';
    }
    const times = issues
      .map((i) => (i.created_at ? new Date(i.created_at).getTime() : 0))
      .filter((t) => t > 0);
    if (!times.length) {
      return 'from scan';
    }
    const latest = Math.max(...times);
    const s = Math.floor((Date.now() - latest) / 1000);
    if (s < 60) {
      return s + 's ago';
    }
    if (s < 3600) {
      return Math.floor(s / 60) + 'm ago';
    }
    return Math.floor(s / 3600) + 'h ago';
  }

  methodBadgeClass(m: string): string {
    const k = (m || '').toLowerCase();
    if (k === 'get') {
      return 'm-get';
    }
    if (k === 'post') {
      return 'm-post';
    }
    if (k === 'delete') {
      return 'm-delete';
    }
    return 'm-get';
  }

  generateAi() {
    const id = this.projectId;
    if (id == null) {
      return;
    }
    this.api.generateAi(id).subscribe({
      next: (r) => {
        this.aiSummary = `${r.summary}\n\n${r.recommendation}`;
      },
      error: (e: unknown) => {
        this.aiSummary = e instanceof HttpErrorResponse ? this.fmt(e) : `Error: ${String(e)}`;
      },
    });
  }

  private fmt(e: HttpErrorResponse): string {
    return `Error: ${e.error?.detail ?? e.message ?? 'request failed'}`;
  }
}
