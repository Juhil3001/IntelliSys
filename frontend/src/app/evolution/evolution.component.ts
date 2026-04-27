import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { IntellisysApiService } from '../intellisys-api.service';

@Component({
  selector: 'app-evolution',
  imports: [CommonModule],
  templateUrl: './evolution.component.html',
  styleUrl: './evolution.component.css',
})
export class EvolutionComponent implements OnInit {
  loading = true;
  error = '';
  snapshots: {
    snapshot_id: number;
    created_at: string | null;
    scan_run_id: number;
    file_count: number;
    api_count: number;
  }[] = [];
  patterns: {
    issue_type: string;
    fingerprint: string;
    hit_count: number;
    last_seen_at: string | null;
  }[] = [];

  constructor(readonly api: IntellisysApiService) {}

  ngOnInit() {
    this.load();
  }

  load() {
    const id = this.api.projectId();
    this.loading = true;
    this.error = '';
    if (id == null) {
      this.loading = false;
      return;
    }
    this.api.getTimeline(id).subscribe({
      next: (r) => {
        this.snapshots = r.snapshots || [];
        this.patterns = r.recurring_patterns || [];
        this.loading = false;
      },
      error: (e) => {
        this.error = String((e as { message?: string })?.message ?? e);
        this.loading = false;
      },
    });
  }
}
