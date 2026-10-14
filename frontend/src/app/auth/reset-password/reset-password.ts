import { Component, effect, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthStore } from '@app/auth/auth.store';
import { PasswordResetStore } from '@app/auth/password-reset.store';

@Component({
  selector: 'app-reset-password',
  imports: [ReactiveFormsModule, RouterLink],
  providers: [PasswordResetStore],
  templateUrl: './reset-password.html',
  styleUrl: '../auth.css',
})
export class ResetPassword {
  protected readonly showPassword = signal(false);
  protected readonly form;
  protected readonly uid: string;
  protected readonly token: string;

  constructor(
    protected readonly passwordReset: PasswordResetStore,
    protected readonly auth: AuthStore,
    formBuilder: FormBuilder,
    route: ActivatedRoute,
  ) {
    this.uid = route.snapshot.paramMap.get('uid') ?? '';
    this.token = route.snapshot.paramMap.get('token') ?? '';
    this.form = formBuilder.nonNullable.group(
      {
        password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(128)]],
        password_confirm: ['', [Validators.required, Validators.maxLength(128)]],
      },
      {
        validators: (form: AbstractControl) =>
          form.get('password')?.value === form.get('password_confirm')?.value
            ? null
            : { mismatch: true },
      },
    );
    effect(() => {
      if (this.passwordReset.completed()) {
        this.resetForm();
      }
    });
  }

  protected submit(): void {
    if (this.passwordReset.pending() || this.auth.pending() || !this.uid || !this.token) return;
    this.form.markAllAsTouched();
    const values = this.form.getRawValue();
    if (this.form.valid)
      this.passwordReset.resetPassword({ uid: this.uid, token: this.token, ...values });
  }

  private resetForm(): void {
    this.form.reset();
    this.showPassword.set(false);
  }
}
