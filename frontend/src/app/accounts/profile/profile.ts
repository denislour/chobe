import { Component, effect, ElementRef, OnInit, signal, viewChild } from '@angular/core';
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
  protected readonly selectedAvatar = signal<File | null>(null);
  protected readonly uploadError = signal('');
  private readonly avatarInput = viewChild<ElementRef<HTMLInputElement>>('avatarInput');

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
      remove_avatar: [false],
    });
    effect(() => this.resetForm(this.profile.profile()));
    effect(() => this.redirectAfterLogout());
  }

  ngOnInit(): void {
    this.profile.load();
  }

  protected chooseAvatar(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.uploadError.set(
      file && file.size > 2 * 1024 * 1024 ? 'Use an image smaller than 2 MiB.' : '',
    );
    this.selectedAvatar.set(this.uploadError() ? null : file);
    if (file) this.form.controls.remove_avatar.setValue(false);
  }

  protected submit(): void {
    if (this.profile.pending() || this.profile.loading() || this.uploadError()) return;
    this.form.markAllAsTouched();
    const version = this.profile.profile()?.version;
    if (!this.form.valid || !version) return;
    const body = new FormData();
    for (const [key, value] of Object.entries(this.form.getRawValue()))
      body.set(key, String(value));
    body.set('version', String(version));
    const avatar = this.selectedAvatar();
    if (avatar && !this.form.controls.remove_avatar.value) body.set('avatar', avatar);
    this.profile.save(body);
  }

  private resetForm(values: ProfileData | null): void {
    if (!values) return;
    this.form.reset({ ...values, remove_avatar: false });
    this.selectedAvatar.set(null);
    this.uploadError.set('');
    const input = this.avatarInput();
    if (input) input.nativeElement.value = '';
  }

  private redirectAfterLogout(): void {
    if (!this.auth.user() && !this.auth.pending()) void this.router.navigateByUrl('/login');
  }
}
