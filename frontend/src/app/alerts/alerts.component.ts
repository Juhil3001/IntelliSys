import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
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
}

@Component({
  selector: 'app-alerts',
  imports: [CommonModule],
  templateUrl: './alerts.component.html',
  styleUrl: './alerts.component.css',
})
export class AlertsComponent implements OnInit {
  summary: AlertSummary | null = null;
  items: AlertItem[] = [];
  error = '';
  loading = false;

  constructor(readonly api: IntellisysApiService) {}

  ngOnInit() {
    this.load();
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

  severityClass(sev: string): string {
    return 'sev-' + (sev || 'medium');
  }

  typeLabel(t: string): string {
    if (t === 'dead_api') return 'Dead API';
    if (t === 'slow_api') return 'Slow API';
    return t || 'Issue';
  }
}
