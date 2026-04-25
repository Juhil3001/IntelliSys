import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { IntellisysApiService } from '../intellisys-api.service';

@Component({
  selector: 'app-apis',
  imports: [CommonModule],
  templateUrl: './apis.component.html',
  styleUrl: './apis.component.css',
})
export class ApisComponent implements OnInit {
  rows: { method: string; endpoint: string; name: string; id: number }[] = [];
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
    this.api.listApis(id).subscribe({
      next: (r) => {
        this.rows = (r as { method: string; endpoint: string; name: string; id: number }[]) || [];
      },
      error: (e) => (this.error = String(e?.message ?? e)),
    });
  }
}
