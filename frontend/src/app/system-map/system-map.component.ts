import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { IntellisysApiService } from '../intellisys-api.service';

interface ImportEdgeRow {
  from_file: string;
  /** Top-level module segment from Python import */
  ['import']: string;
}

interface GraphNode {
  id?: string;
  label?: string;
  kind?: string;
}

interface GraphSummary {
  file_count?: number;
  api_count?: number;
  package_nodes?: number;
}

@Component({
  selector: 'app-system-map',
  imports: [CommonModule, RouterLink],
  templateUrl: './system-map.component.html',
  styleUrl: './system-map.component.css',
})
export class SystemMapComponent implements OnInit {
  loading = true;
  error = '';
  projectIdNum: number | null = null;
  scanRunId: number | null = null;
  summary: GraphSummary | null = null;
  nodes: GraphNode[] = [];
  importSample: ImportEdgeRow[] = [];
  hasArtifacts = false;

  constructor(readonly api: IntellisysApiService) {}

  ngOnInit() {
    this.load();
  }

  load() {
    const id = this.api.projectId();
    this.projectIdNum = id;
    this.loading = true;
    this.error = '';
    this.summary = null;
    this.nodes = [];
    this.importSample = [];
    this.hasArtifacts = false;
    this.scanRunId = null;
    if (id == null) {
      this.loading = false;
      return;
    }
    this.api.getProjectGraph(id).subscribe({
      next: (r) => {
        this.scanRunId = typeof r['scan_run_id'] === 'number' ? (r['scan_run_id'] as number) : null;
        const rawSummary = r['summary'] as GraphSummary | null | undefined;
        this.summary = rawSummary && typeof rawSummary === 'object' ? rawSummary : null;
        const n = r['nodes'];
        this.nodes = Array.isArray(n) ? (n as GraphNode[]) : [];
        const imp = r['import_sample'] as ImportEdgeRow[] | undefined;
        this.importSample = Array.isArray(imp) ? imp : [];
        this.hasArtifacts = this.nodes.length > 0 || this.importSample.length > 0 || !!this.summary;
        this.loading = false;
      },
      error: (e) => {
        this.error = this.fmtErr(e);
        this.loading = false;
      },
    });
  }

  packageNodes(): GraphNode[] {
    return this.nodes.filter((n) => n.kind === 'package');
  }

  fileNodes(): GraphNode[] {
    return this.nodes.filter((n) => n.kind === 'file');
  }

  importModule(edge: ImportEdgeRow): string {
    return edge['import'] ?? '';
  }

  private fmtErr(e: unknown): string {
    if (e instanceof HttpErrorResponse) {
      return String(e.error?.detail ?? e.message ?? 'Request failed');
    }
    return String((e as { message?: string })?.message ?? e);
  }
}
