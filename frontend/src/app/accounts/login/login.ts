import { Component, effect, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthStore } from '../auth.store';
import { LoginUser } from '../login-api';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: '../auth.css',
})
export class Login {
  protected readonly showPassword = signal(false);
  protected readonly form;

  constructor(
    protected readonly auth: AuthStore,
    formBuilder: FormBuilder,
  ) {
    this.auth.clearErrors();
    this.form = formBuilder.nonNullable.group({
      username: ['', [Validators.required, Validators.maxLength(254)]],
      password: ['', [Validators.required, Validators.maxLength(128)]],
    });
    effect(() => this.resetForm(this.auth.user()));
  }

  protected submit(): void {
    if (this.auth.pending() || this.auth.user()) return;
    this.form.markAllAsTouched();
    if (this.form.valid) this.auth.login(this.form.getRawValue());
  }

  private resetForm(user: LoginUser | null): void {
    this.form.controls.password.reset();
    this.showPassword.set(false);
    if (!user) this.form.controls.username.reset();
  }
}
