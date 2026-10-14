import { Component } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthStore } from '@app/auth/auth.store';
import { PasswordResetStore } from '@app/auth/password-reset.store';
import { safeReturnUrl } from '@app/auth/return-url';

@Component({
  selector: 'app-forgot-password',
  imports: [ReactiveFormsModule, RouterLink],
  providers: [PasswordResetStore],
  templateUrl: './forgot-password.html',
  styleUrl: '../auth.css',
})
export class ForgotPassword {
  protected readonly form;
  protected readonly returnUrl;

  constructor(
    protected readonly passwordReset: PasswordResetStore,
    protected readonly auth: AuthStore,
    formBuilder: FormBuilder,
    route: ActivatedRoute,
  ) {
    this.returnUrl = safeReturnUrl(route.snapshot.queryParamMap.get('returnUrl'));
    this.form = formBuilder.nonNullable.group({
      email: ['', [Validators.required, Validators.email, Validators.maxLength(254)]],
    });
  }

  protected submit(): void {
    if (this.passwordReset.pending() || this.auth.pending()) return;
    this.form.markAllAsTouched();
    if (this.form.valid) this.passwordReset.forgotPassword(this.form.getRawValue().email);
  }
}
