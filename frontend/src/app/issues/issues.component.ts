import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { IntellisysApiService } from '../intellisys-api.service';

@Component({
  selector: 'app-issues',
  imports: [CommonModule],
  templateUrl: './issues.component.html',
  styleUrl: './issues.component.css',
})
export class IssuesComponent implements OnInit {
  rows: {
    id: number;
    type: string;
    description: string;
    severity: string | null;
  }[] = [];
  error = '';

  constructor(private api: IntellisysApiService) {}

  ngOnInit() {
    this.load();
  }

  load() {
    const id = this.api.projectId();
    if (id == null) {
      this.error = 'Set an active project from the dashboard.';
      return;
    }
    this.error = '';
    this.api.listIssues(id).subscribe({
      next: (r) => {
        this.rows =
          (r as {
            id: number;
            type: string;
            description: string;
            severity: string | null;
          }[]) || [];
      },
      error: (e) => (this.error = String(e?.message ?? e)),
    });
  }
}
