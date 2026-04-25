import { CommonModule } from '@angular/common';
import { Component, DestroyRef, HostListener, OnInit, inject } from '@angular/core';
import { toObservable, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { catchError, distinctUntilChanged, map, of, switchMap } from 'rxjs';
import { IntellisysApiService } from '../intellisys-api.service';
import { ThemeService } from '../theme.service';
import { AuthService } from '../auth/auth.service';

@Component({
  selector: 'app-main-layout',
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './main-layout.component.html',
  styleUrl: './main-layout.component.css',
})
export class MainLayoutComponent implements OnInit {
  readonly api = inject(IntellisysApiService);
  readonly auth = inject(AuthService);
  readonly theme = inject(ThemeService);

  alertCount = 0;
  navOpen = false;
  /** Desktop: show icon + labels in the rail */
  sidebarExpanded = false;

  constructor() {
    const destroyRef = inject(DestroyRef);
    toObservable(this.api.projectId)
      .pipe(
        distinctUntilChanged(),
        switchMap((id) =>
          id == null
            ? of(0)
            : this.api.getAlerts(id).pipe(
                map((r) => r.summary?.total ?? 0),
                catchError(() => of(0))
              )
        ),
        takeUntilDestroyed(destroyRef)
      )
      .subscribe((n) => (this.alertCount = n));
  }

  ngOnInit() {
    if (this.auth.getToken()) {
      this.auth.fetchMe().subscribe({ error: () => undefined });
    }
    this.api.health().subscribe({ error: () => undefined });
  }

  toggleNav() {
    this.navOpen = !this.navOpen;
  }

  closeNav() {
    this.navOpen = false;
  }

  toggleSidebarExpand() {
    this.sidebarExpanded = !this.sidebarExpanded;
  }

  userInitials(): string {
    const u = this.auth.user();
    if (!u) {
      return 'IS';
    }
    const d = (u.display_name || u.email).trim();
    if (d.includes(' ')) {
      const p = d.split(/\s+/).filter(Boolean);
      if (p.length >= 2) {
        return (p[0][0] + p[1][0]).toUpperCase().slice(0, 2);
      }
    }
    return d.slice(0, 2).toUpperCase() || 'U';
  }

  @HostListener('window:resize')
  onResize() {
    if (window.innerWidth >= 768) {
      this.navOpen = false;
    }
  }
}
