import { Component, effect, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthStore } from '@app/auth/auth.store';
import { safeReturnUrl } from '@app/auth/return-url';

@Component({
  selector: 'app-register',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './register.html',
  styleUrls: ['../auth.css', './register.css'],
})
export class Register {
  protected readonly showPassword = signal(false);
  protected readonly form;
  protected readonly returnUrl;

  constructor(
    protected readonly auth: AuthStore,
    private readonly router: Router,
    formBuilder: FormBuilder,
    route: ActivatedRoute,
  ) {
    this.returnUrl = safeReturnUrl(route.snapshot.queryParamMap.get('returnUrl'));
    this.auth.clearErrors();
    this.form = formBuilder.nonNullable.group({
      username: [
        '',
        [
          Validators.required,
          Validators.maxLength(150),
          Validators.pattern(/^[\p{L}\p{N}_.+-]+$/u),
        ],
      ],
      email: ['', [Validators.required, Validators.email, Validators.maxLength(254)]],
      password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(128)]],
      accept_terms: [false, Validators.requiredTrue],
    });
    effect(() => {
      if (this.auth.user()) this.finishRegistration();
    });
  }

  protected submit(): void {
    if (this.auth.pending() || this.auth.user()) return;
    this.form.markAllAsTouched();
    if (this.form.valid) this.auth.register(this.form.getRawValue());
  }

  private finishRegistration(): void {
    this.form.controls.password.reset();
    this.showPassword.set(false);
    void this.router.navigateByUrl(this.returnUrl ?? '/login');
  }
}
