import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { IntellisysApiService, IssueListRow } from '../intellisys-api.service';

@Component({
  selector: 'app-issues',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './issues.component.html',
  styleUrl: './issues.component.css',
})
export class IssuesComponent implements OnInit {
  rows: IssueListRow[] = [];
  filterText = '';
  error = '';
  loading = false;

  constructor(readonly api: IntellisysApiService) {}

  ngOnInit() {
    this.load();
  }

  get filteredRows(): IssueListRow[] {
    const q = this.filterText.trim().toLowerCase();
    if (!q) {
      return this.rows;
    }
    return this.rows.filter(
      (r) =>
        r.description.toLowerCase().includes(q) ||
        (r.type || '').toLowerCase().includes(q) ||
        (r.severity || '').toLowerCase().includes(q) ||
        (r.source || '').toLowerCase().includes(q)
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
    this.api.listIssues(id).subscribe({
      next: (r) => {
        this.rows = (r as IssueListRow[]) || [];
        this.loading = false;
      },
      error: (e) => {
        this.error = String((e as { error?: { detail?: string } })?.error?.detail ?? e?.message ?? e);
        this.loading = false;
      },
    });
  }

  severityClass(sev: string | null): string {
    return 'sev-' + (sev || 'medium');
  }

  askAiPrompt(row: IssueListRow): string {
    const src = row.source || 'heuristic';
    const sev = row.severity || 'unknown';
    return (
      `Explain this issue and suggest concrete fixes. ` +
      `Type: ${row.type}, severity: ${sev}, source: ${src}. ` +
      `Description: ${row.description.slice(0, 1500)}`
    );
  }
}
