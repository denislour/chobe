import { Component, effect, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ProfileData } from './profile-api';
import { AccountNav } from '@app/accounts/account-nav/account-nav';
import { AuthStore } from '@app/auth/auth.store';
import { ProfileStore } from './profile.store';

@Component({
  selector: 'app-profile',
  imports: [ReactiveFormsModule, AccountNav],
  providers: [ProfileStore],
  templateUrl: './profile.html',
  styleUrl: '../account.css',
})
export class Profile implements OnInit {
  protected readonly form;

  constructor(
    protected readonly profile: ProfileStore,
    protected readonly auth: AuthStore,
    formBuilder: FormBuilder,
    private readonly router: Router,
  ) {
    this.form = formBuilder.nonNullable.group({
      display_name: ['', [Validators.required, Validators.maxLength(80)]],
      area: ['', Validators.maxLength(120)],
      bio: ['', Validators.maxLength(200)],
      phone: ['', Validators.pattern(/^\+[1-9]\d{7,14}$/)],
    });
    effect(() => this.resetForm(this.profile.profile()));
    effect(() => this.redirectAfterLogout());
  }

  ngOnInit(): void {
    this.profile.load();
  }

  protected submit(): void {
    if (this.profile.pending() || this.profile.loading()) return;
    this.form.markAllAsTouched();
    const version = this.profile.profile()?.version;
    if (!this.form.valid || !version) return;
    const body = new FormData();
    for (const [key, value] of Object.entries(this.form.getRawValue()))
      body.set(key, String(value));
    body.set('version', String(version));
    this.profile.save(body);
  }

  private resetForm(values: ProfileData | null): void {
    if (!values) return;
    this.form.reset(values);
  }

  private redirectAfterLogout(): void {
    if (!this.auth.user() && !this.auth.pending()) void this.router.navigateByUrl('/login');
  }
}
