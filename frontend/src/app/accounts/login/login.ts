import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { LoginApi, LoginUser } from '../login-api';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  private readonly api = inject(LoginApi);
  private readonly destroyRef = inject(DestroyRef);
  readonly pending = signal(false);
  readonly error = signal('');
  readonly user = signal<LoginUser | null>(null);
  readonly showPassword = signal(false);
  readonly form = inject(FormBuilder).nonNullable.group({
    username: ['', [Validators.required, Validators.maxLength(254)]],
    password: ['', [Validators.required, Validators.maxLength(128)]],
  });

  submit() {
    if (this.pending() || this.user()) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    this.pending.set(true);
    this.error.set('');
    this.api
      .login(this.form.getRawValue())
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.pending.set(false)),
      )
      .subscribe({
        next: (user) => {
          this.user.set(user);
          this.form.controls.password.reset();
        },
        error: (error: HttpErrorResponse) => {
          const messages: Record<number, string> = {
            400: 'Invalid username or password.',
            403: 'Your security check expired. Please try again.',
            429: 'Too many login attempts. Wait a minute and try again.',
          };
          this.error.set(messages[error.status] ?? 'Unable to connect. Please try again.');
        },
      });
  }
}
