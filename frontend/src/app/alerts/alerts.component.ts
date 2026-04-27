import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { IntellisysApiService } from '../intellisys-api.service';

export interface AlertSummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
}

export interface AlertItem {
  id: number;
  type: string;
  description: string;
  severity: string;
  api_id: number | null;
  created_at: string | null;
  source?: string;
}

@Component({
  selector: 'app-alerts',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './alerts.component.html',
  styleUrl: './alerts.component.css',
})
export class AlertsComponent implements OnInit {
  summary: AlertSummary | null = null;
  items: AlertItem[] = [];
  filterText = '';
  error = '';
  loading = false;
  resolveBusy: Record<number, boolean> = {};

  constructor(readonly api: IntellisysApiService) {}

  ngOnInit() {
    this.load();
  }

  get filteredItems(): AlertItem[] {
    const q = this.filterText.trim().toLowerCase();
    if (!q) {
      return this.items;
    }
    return this.items.filter(
      (a) =>
        a.description.toLowerCase().includes(q) ||
        (a.type || '').toLowerCase().includes(q) ||
        (a.severity || '').toLowerCase().includes(q)
    );
  }

  load() {
    const id = this.api.projectId();
    if (id == null) {
      this.error = '';
      this.summary = null;
      this.items = [];
      return;
    }
    this.error = '';
    this.loading = true;
    this.api.getAlerts(id).subscribe({
      next: (res) => {
        this.summary = res.summary as AlertSummary;
        this.items = (res.items as AlertItem[]) ?? [];
        this.loading = false;
      },
      error: (e) => {
        this.error = String(e?.error?.detail ?? e?.message ?? e);
        this.loading = false;
      },
    });
  }

  resolveAlert(item: AlertItem) {
    this.resolveBusy[item.id] = true;
    this.api.patchIssue(item.id, { resolved: true }).subscribe({
      next: () => {
        this.resolveBusy[item.id] = false;
        this.load();
      },
      error: (e) => {
        this.resolveBusy[item.id] = false;
        this.error = String((e as { error?: { detail?: string } })?.error?.detail ?? e);
      },
    });
  }

  severityClass(sev: string): string {
    return 'sev-' + (sev || 'medium');
  }

  typeLabel(t: string): string {
    if (t === 'dead_api') return 'Dead API';
    if (t === 'slow_api') return 'Slow API';
    return t || 'Issue';
  }
}
