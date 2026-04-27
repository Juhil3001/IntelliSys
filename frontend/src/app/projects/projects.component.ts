import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IntellisysApiService, Project } from '../intellisys-api.service';

@Component({
  selector: 'app-projects',
  imports: [CommonModule, FormsModule],
  templateUrl: './projects.component.html',
  styleUrl: './projects.component.css',
})
export class ProjectsComponent implements OnInit {
  projects: Project[] = [];
  projectName = 'My project';
  rootPath = '';
  githubUrl = '';
  defaultBranch = 'main';
  busy = false;
  lastAction = '';
  /** Alert webhook URL for the active project (Slack/Teams generic incoming). */
  alertWebhook = '';

  constructor(protected api: IntellisysApiService) {}

  ngOnInit() {
    this.refreshProjects();
    const id = this.api.readStoredId();
    if (id != null) {
      this.api.setProjectId(id);
    }
  }

  get projectId(): number | null {
    return this.api.projectId();
  }

  get activeProject(): Project | undefined {
    const id = this.projectId;
    if (id == null) {
      return undefined;
    }
    return this.projects.find((x) => x.id === id);
  }

  get n8nBodyExample(): string {
    const id = this.projectId;
    if (id == null) {
      return '';
    }
    return `{ "action": "daily_scan", "project_id": ${id}, "with_snapshot": true }`;
  }

  get canRegister(): boolean {
    return !!(this.rootPath.trim() || this.githubUrl.trim());
  }

  refreshProjects() {
    this.api.listProjects().subscribe((p) => {
      this.projects = p;
      const ap = this.activeProject;
      this.alertWebhook = ap?.alert_webhook_url ?? '';
    });
  }

  useProject(id: number) {
    this.api.setProjectId(id);
    this.lastAction = `Active project: ${id}`;
    const ap = this.projects.find((x) => x.id === id);
    this.alertWebhook = ap?.alert_webhook_url ?? '';
  }

  saveAlertWebhook() {
    const id = this.projectId;
    if (id == null) {
      return;
    }
    this.busy = true;
    this.api.patchProject(id, { alert_webhook_url: this.alertWebhook.trim() || null }).subscribe({
      next: () => {
        this.refreshProjects();
        this.lastAction = 'Saved alert webhook URL';
        this.busy = false;
      },
      error: (e) => {
        this.lastAction = this.fmtErr(e);
        this.busy = false;
      },
    });
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
        this.lastAction = this.fmtErr(e);
        this.busy = false;
      },
    });
  }

  deleteProject(p: Project, ev: Event) {
    ev?.stopPropagation();
    if (!window.confirm(`Delete project "${p.name}" (#${p.id})? This cannot be undone.`)) {
      return;
    }
    this.busy = true;
    this.api.deleteProject(p.id).subscribe({
      next: () => {
        if (this.api.projectId() === p.id) {
          this.api.clearProjectId();
        }
        this.refreshProjects();
        this.lastAction = `Deleted project #${p.id}`;
        this.busy = false;
      },
      error: (e) => {
        this.lastAction = this.fmtErr(e);
        this.busy = false;
      },
    });
  }

  private fmtErr(e: unknown): string {
    if (e instanceof HttpErrorResponse) {
      return String(e.error?.detail ?? e.message);
    }
    return String((e as { message?: string })?.message ?? e);
  }
}
