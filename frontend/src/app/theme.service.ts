import { DOCUMENT } from '@angular/common';
import { Inject, Injectable, signal } from '@angular/core';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'intellisys_theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  /** dark is default per product spec */
  theme = signal<Theme>(this.readInitial());

  constructor(@Inject(DOCUMENT) private document: Document) {
    this.apply(this.theme());
  }

  private readInitial(): Theme {
    if (typeof localStorage === 'undefined') {
      return 'dark';
    }
    const t = localStorage.getItem(STORAGE_KEY);
    if (t === 'light' || t === 'dark') {
      return t;
    }
    return 'dark';
  }

  setTheme(t: Theme): void {
    this.theme.set(t);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, t);
    }
    this.apply(t);
  }

  toggle(): void {
    this.setTheme(this.theme() === 'dark' ? 'light' : 'dark');
  }

  private apply(t: Theme): void {
    this.document.documentElement.setAttribute('data-theme', t);
  }
}
