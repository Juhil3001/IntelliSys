import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.getToken();
  let out = req;
  if (token) {
    out = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  }
  return next(out).pipe(
    catchError((err: HttpErrorResponse) => {
      if (
        err.status === 401 &&
        token &&
        !req.url.includes('/auth/login') &&
        !req.url.includes('/auth/register')
      ) {
        auth.clearSession();
        router.navigateByUrl('/login');
      }
      return throwError(() => err);
    })
  );
};
