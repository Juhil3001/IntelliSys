import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IntellisysApiService, Project } from '../intellisys-api.service';

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit {
  healthStatus = '—';
  projects: Project[] = [];
  projectName = 'My project';
  rootPath = '';
  githubUrl = '';
  defaultBranch = 'main';
  busy = false;
  lastAction = '';
  aiSummary = '';

  constructor(protected api: IntellisysApiService) {}

  ngOnInit() {
    this.api.health().subscribe({
      next: (h) => (this.healthStatus = h.status),
      error: () => (this.healthStatus = 'offline'),
    });
    this.refreshProjects();
    const id = this.api.readStoredId();
    if (id != null) this.api.setProjectId(id);
  }

  refreshProjects() {
    this.api.listProjects().subscribe((p) => (this.projects = p));
  }

  get projectId(): number | null {
    return this.api.projectId();
  }

  get activeProject(): Project | undefined {
    const id = this.projectId;
    if (id == null) return undefined;
    return this.projects.find((x) => x.id === id);
  }

  /** n8n POST /automation/n8n-webhook JSON example with current id */
  get n8nBodyExample(): string {
    const id = this.projectId;
    if (id == null) return '';
    return `{ "action": "daily_scan", "project_id": ${id}, "with_snapshot": true }`;
  }

  get canRegister(): boolean {
    return !!(this.rootPath.trim() || this.githubUrl.trim());
  }

  createProject() {
    if (!this.canRegister) {
      this.lastAction = 'Enter a local root path and/or a GitHub URL.';
      return;
    }
    this.busy = true;
    const body: {
      name: string;
      root_path?: string;
      github_repo_url?: string;
      default_branch?: string;
    } = { name: this.projectName.trim() };
    if (this.githubUrl.trim()) {
      body.github_repo_url = this.githubUrl.trim();
      body.default_branch = (this.defaultBranch || 'main').trim();
    }
    if (this.rootPath.trim()) {
      body.root_path = this.rootPath.trim();
    }
    this.api.createProject(body).subscribe({
      next: (p) => {
        this.api.setProjectId(p.id);
        this.refreshProjects();
        this.lastAction = `Created project #${p.id}`;
        this.busy = false;
      },
      error: (e) => {
        this.lastAction = String(e?.error?.detail ?? e?.message ?? e);
        this.busy = false;
      },
    });
  }

  useProject(id: number) {
    this.api.setProjectId(id);
    this.lastAction = `Active project: ${id}`;
  }

  runScan() {
    const id = this.projectId;
    if (id == null) return;
    this.busy = true;
    this.api.startScan(id).subscribe({
      next: () => {
        this.lastAction = 'Scan finished (recompute + snapshot included for GitHub projects).';
        this.busy = false;
        this.refreshProjects();
      },
      error: (e) => {
        this.lastAction = String(e?.error?.detail ?? e?.message ?? e);
        this.busy = false;
      },
    });
  }

  fullSyncAndScan() {
    const id = this.projectId;
    if (id == null) return;
    this.busy = true;
    this.api.syncAndScan(id, true).subscribe({
      next: (r) => {
        this.lastAction = `Pipeline: scan #${r['scan_run_id']}, issues ${r['issues_recomputed']}, commit ${r['last_commit_sha'] ?? '—'}`;
        this.busy = false;
        this.refreshProjects();
      },
      error: (e) => {
        this.lastAction = String(e?.error?.detail ?? e?.message ?? e);
        this.busy = false;
      },
    });
  }

  recompute() {
    const id = this.projectId;
    if (id == null) return;
    this.busy = true;
    this.api.recompute(id).subscribe({
      next: (r: { issues_created?: number }) => {
        this.lastAction = `Issues updated: ${r?.issues_created ?? 0}`;
        this.busy = false;
      },
      error: (e) => {
        this.lastAction = String(e?.error?.detail ?? e?.message ?? e);
        this.busy = false;
      },
    });
  }

  generateAi() {
    const id = this.projectId;
    if (id == null) return;
    this.busy = true;
    this.api.generateAi(id).subscribe({
      next: (r) => {
        this.aiSummary = `${r.summary}\n\n${r.recommendation}`;
        this.lastAction = `AI insight (model ${r.model})`;
        this.busy = false;
      },
      error: (e) => {
        this.lastAction = String(e?.error?.detail ?? e?.message ?? e);
        this.busy = false;
      },
    });
  }
}
