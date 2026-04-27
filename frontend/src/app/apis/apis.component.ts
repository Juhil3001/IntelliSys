import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { IntellisysApiService, ApiListRow } from '../intellisys-api.service';

@Component({
  selector: 'app-apis',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './apis.component.html',
  styleUrl: './apis.component.css',
})
export class ApisComponent implements OnInit {
  rows: ApiListRow[] = [];
  filterText = '';
  error = '';
  loading = false;

  constructor(readonly api: IntellisysApiService) {}

  ngOnInit() {
    this.load();
  }

  get filteredRows(): ApiListRow[] {
    const q = this.filterText.trim().toLowerCase();
    if (!q) {
      return this.rows;
    }
    return this.rows.filter(
      (r) =>
        r.endpoint.toLowerCase().includes(q) ||
        (r.method || '').toLowerCase().includes(q) ||
        String(r.id).includes(q)
    );
  }

  load() {
    const id = this.api.projectId();
    if (id == null) {
      this.error = '';
      this.rows = [];
      return;
    }
    this.error = '';
    this.loading = true;
    this.api.listApis(id).subscribe({
      next: (r) => {
        this.rows = (r as ApiListRow[]) || [];
        this.loading = false;
      },
      error: (e) => {
        this.error = String((e as { error?: { detail?: string } })?.error?.detail ?? e?.message ?? e);
        this.loading = false;
      },
    });
  }

  methodBadgeClass(m: string): string {
    const k = (m || '').toLowerCase();
    if (k === 'get') return 'm-get';
    if (k === 'post') return 'm-post';
    if (k === 'put' || k === 'patch') return 'm-put';
    if (k === 'delete') return 'm-delete';
    return 'm-default';
  }

  askAiPrompt(row: ApiListRow): string {
    return (
      `Explain this API route and what to verify in production. ` +
      `Method: ${row.method}, path: ${row.endpoint}` +
      (row.name ? `, name: ${row.name}` : '') +
      '.'
    );
  }
}
