import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { IntellisysApiService, Project } from '../intellisys-api.service';

type ActionKey = 'scan' | 'sync' | 'recompute' | 'ai';

@Component({
  selector: 'app-actions',
  imports: [CommonModule, RouterLink],
  templateUrl: './actions.component.html',
  styleUrl: './actions.component.css',
})
export class ActionsComponent implements OnInit {
  selected: ActionKey = 'scan';
  busy = false;
  lastResult = '';
  aiSummary = '';

  readonly actions: { key: ActionKey; label: string; blurb: string; icon: string }[] = [
    { key: 'scan', label: 'Run scan', blurb: 'Start a repository scan, recompute, and snapshot (when applicable).', icon: 'radar' },
    { key: 'sync', label: 'Sync & full scan (Git)', blurb: 'Git fetch + full pipeline for GitHub-backed projects.', icon: 'git' },
    { key: 'recompute', label: 'Recompute issues', blurb: 'Regenerate issues from latest traffic and heuristics.', icon: 'refresh' },
    { key: 'ai', label: 'Generate AI insight', blurb: 'Ask the AI engine for a summary and recommendations.', icon: 'spark' },
  ];

  projects: Project[] = [];

  constructor(protected api: IntellisysApiService) {}

  ngOnInit() {
    this.api.listProjects().subscribe((p) => (this.projects = p));
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

  select(key: ActionKey) {
    this.selected = key;
    this.lastResult = '';
  }

  private fmt(e: unknown): string {
    if (e instanceof HttpErrorResponse) {
      return String(e.error?.detail ?? e.message);
    }
    return String((e as { message?: string })?.message ?? e);
  }

  runScan() {
    const id = this.projectId;
    if (id == null) {
      return;
    }
    this.busy = true;
    this.api.startScan(id).subscribe({
      next: () => {
        this.lastResult = 'Scan finished (recompute + snapshot where applicable).';
        this.busy = false;
      },
      error: (e) => {
        this.lastResult = this.fmt(e);
        this.busy = false;
      },
    });
  }

  runSync() {
    const id = this.projectId;
    if (id == null) {
      return;
    }
    this.busy = true;
    this.api.syncAndScan(id, true).subscribe({
      next: (r) => {
        this.lastResult = `Scan #${r['scan_run_id']}, issues ${r['issues_recomputed']}, commit ${r['last_commit_sha'] ?? '—'}`;
        this.busy = false;
      },
      error: (e) => {
        this.lastResult = this.fmt(e);
        this.busy = false;
      },
    });
  }

  runRecompute() {
    const id = this.projectId;
    if (id == null) {
      return;
    }
    this.busy = true;
    this.api.recompute(id).subscribe({
      next: (r: { issues_created?: number }) => {
        this.lastResult = `Issues updated: ${r?.issues_created ?? 0}`;
        this.busy = false;
      },
      error: (e) => {
        this.lastResult = this.fmt(e);
        this.busy = false;
      },
    });
  }

  runAi() {
    const id = this.projectId;
    if (id == null) {
      return;
    }
    this.busy = true;
    this.api.generateAi(id).subscribe({
      next: (r) => {
        this.aiSummary = `${r.summary}\n\n${r.recommendation}`;
        this.lastResult = `Model: ${r.model}`;
        this.busy = false;
      },
      error: (e) => {
        this.lastResult = this.fmt(e);
        this.busy = false;
      },
    });
  }
}
