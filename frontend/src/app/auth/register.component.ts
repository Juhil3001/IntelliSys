import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from './auth.service';

const strongPassword: ValidatorFn = (c: AbstractControl): ValidationErrors | null => {
  const v = (c.value as string) || '';
  if (v.length < 8) {
    return { minLen: true };
  }
  if (!/[A-Za-z]/.test(v) || !/[0-9]/.test(v)) {
    return { weak: true };
  }
  return null;
};

const matchPassword: ValidatorFn = (g: AbstractControl): ValidationErrors | null => {
  const p = g.get('password')?.value;
  const c = g.get('confirm')?.value;
  if (p == null && c == null) {
    return null;
  }
  return p === c ? null : { match: true };
};

@Component({
  selector: 'app-register',
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrl: './register.component.css',
})
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);

  loading = false;
  error = '';

  form = this.fb.nonNullable.group(
    {
      displayName: ['', [Validators.required, Validators.maxLength(255)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, strongPassword]],
      confirm: ['', [Validators.required]],
    },
    { validators: [matchPassword] }
  );

  submit() {
    this.error = '';
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { displayName, email, password } = this.form.getRawValue();
    this.loading = true;
    this.auth.register(email.trim(), password, displayName.trim()).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigateByUrl('/dashboard');
      },
      error: (e: HttpErrorResponse) => {
        this.loading = false;
        this.error = (e.error?.detail as string) || e.message || 'Registration failed';
      },
    });
  }
}
