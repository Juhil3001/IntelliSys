import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService, AuthUser } from '../auth/auth.service';

@Component({
  selector: 'app-profile',
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.css',
})
export class ProfileComponent implements OnInit {
  auth = inject(AuthService);
  private fb = inject(FormBuilder);

  loading = false;
  saved = false;
  err = '';
  u: AuthUser | null = null;

  form = this.fb.nonNullable.group({
    displayName: ['', [Validators.required, Validators.maxLength(255)]],
  });

  ngOnInit() {
    this.auth.fetchMe().subscribe({
      next: (user) => {
        this.u = user;
        this.form.patchValue({ displayName: user.display_name || '' });
      },
      error: () => {
        this.u = this.auth.user();
        if (this.u) {
          this.form.patchValue({ displayName: this.u.display_name || '' });
        }
      },
    });
  }

  get emailDisplay(): string {
    return this.u?.email || this.auth.user()?.email || '—';
  }

  save() {
    this.err = '';
    this.saved = false;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading = true;
    this.auth.updateProfile(this.form.getRawValue().displayName.trim()).subscribe({
      next: (user) => {
        this.u = user;
        this.loading = false;
        this.saved = true;
      },
      error: (e: HttpErrorResponse) => {
        this.loading = false;
        this.err = (e.error?.detail as string) || e.message || 'Save failed';
      },
    });
  }
}
