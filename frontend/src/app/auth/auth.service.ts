import { HttpClient } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';
import { tap } from 'rxjs';

export interface AuthUser {
  id: number;
  email: string;
  display_name: string;
}

const TOKEN = 'intellisys_access_token';
const USER = 'intellisys_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly _base = environment.apiBaseUrl;
  /** Current user (null if logged out) */
  user = signal<AuthUser | null>(this.readUser());

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  getToken(): string | null {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    return localStorage.getItem(TOKEN);
  }

  private readUser(): AuthUser | null {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    const s = localStorage.getItem(USER);
    if (!s) {
      return null;
    }
    try {
      return JSON.parse(s) as AuthUser;
    } catch {
      return null;
    }
  }

  private persistSession(token: string, user: AuthUser): void {
    localStorage.setItem(TOKEN, token);
    localStorage.setItem(USER, JSON.stringify(user));
    this.user.set(user);
  }

  clearSession(): void {
    localStorage.removeItem(TOKEN);
    localStorage.removeItem(USER);
    this.user.set(null);
  }

  login(email: string, password: string) {
    return this.http
      .post<{ access_token: string; token_type: string; user: AuthUser }>(`${this._base}/auth/login`, { email, password })
      .pipe(
        tap((r) => {
          this.persistSession(r.access_token, r.user);
        })
      );
  }

  register(email: string, password: string, displayName: string) {
    return this.http
      .post<{ access_token: string; token_type: string; user: AuthUser }>(`${this._base}/auth/register`, {
        email,
        password,
        display_name: displayName,
      })
      .pipe(
        tap((r) => {
          this.persistSession(r.access_token, r.user);
        })
      );
  }

  fetchMe() {
    return this.http.get<AuthUser>(`${this._base}/auth/me`).pipe(
      tap((u) => {
        localStorage.setItem(USER, JSON.stringify(u));
        this.user.set(u);
      })
    );
  }

  updateProfile(displayName: string) {
    return this.http.patch<AuthUser>(`${this._base}/auth/me`, { display_name: displayName }).pipe(
      tap((u) => {
        localStorage.setItem(USER, JSON.stringify(u));
        this.user.set(u);
      })
    );
  }

  logout(): void {
    this.clearSession();
    this.router.navigateByUrl('/login');
  }
}
