import {
  afterNextRender,
  Component,
  effect,
  ElementRef,
  OnDestroy,
  untracked,
  viewChild,
  input,
} from '@angular/core';
import { Chart, type ChartConfiguration, registerables } from 'chart.js';
import type { ChartPoint } from '../../../models/dashboard.model';
import { ThemeService } from '../../../services/theme.service';

Chart.register(...registerables);

@Component({
  selector: 'app-latency-chart',
  imports: [],
  templateUrl: './latency-chart.component.html',
  styleUrl: './latency-chart.component.css',
})
export class LatencyChartComponent implements OnDestroy {
  readonly loading = input(false);
  readonly series = input<ChartPoint[]>([]);
  private readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>('canvas');
  private chart: Chart | null = null;

  constructor(private readonly theme: ThemeService) {
    afterNextRender(() => {
      effect(() => {
        this.theme.theme();
        this.series();
        this.loading();
        this.sync();
      });
    });
  }

  ngOnDestroy(): void {
    this.chart?.destroy();
  }

  private sync(): void {
    if (this.loading()) {
      this.chart?.destroy();
      this.chart = null;
      return;
    }
    const points = this.series();
    if (!points.length) {
      this.chart?.destroy();
      this.chart = null;
      return;
    }
    const el = untracked(this.canvas)?.nativeElement;
    if (!el) return;
    const labels = points.map((p) => p.label);
    const data = points.map((p) => p.value);
    const accent = getCss('--is-accent', '#6366f1');
    const muted = getCss('--is-muted', '#9ca3af');
    const text = getCss('--is-text', '#e5e7eb');
    const border = getCss('--is-border', 'rgba(255,255,255,0.08)');

    const cfg: ChartConfiguration<'line'> = {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'ms',
            data,
            borderColor: accent,
            backgroundColor: (ctx) => {
              const c = ctx.chart.ctx;
              const h = ctx.chart.height;
              const g = c.createLinearGradient(0, 0, 0, h);
              g.addColorStop(0, 'rgba(99, 102, 241, 0.15)');
              g.addColorStop(1, 'rgba(99, 102, 241, 0)');
              return g;
            },
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointBackgroundColor: accent,
            pointBorderColor: text,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(9, 9, 11, 0.95)',
            titleColor: text,
            bodyColor: text,
            borderColor: border,
            borderWidth: 1,
            padding: 8,
            cornerRadius: 6,
            displayColors: false,
          },
        },
        scales: {
          x: {
            grid: { color: border, lineWidth: 0.5 },
            ticks: { color: muted, maxRotation: 0, font: { size: 10 } },
            border: { display: false },
          },
          y: {
            beginAtZero: true,
            grid: { color: border, lineWidth: 0.5 },
            ticks: { color: muted, font: { size: 10 } },
            border: { display: false },
          },
        },
      },
    };

    this.chart?.destroy();
    this.chart = new Chart(el, cfg);
  }
}

function getCss(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}
