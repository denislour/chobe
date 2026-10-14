import { DatePipe } from '@angular/common';
import { Component, effect, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AccountNav } from '@app/accounts/account-nav/account-nav';
import { AuthStore } from '@app/auth/auth.store';
import { PrivacyStore } from './privacy.store';
import { AccountDataStore } from './account-data.store';

@Component({
  selector: 'app-privacy',
  imports: [ReactiveFormsModule, AccountNav, DatePipe, RouterLink],
  providers: [PrivacyStore, AccountDataStore],
  templateUrl: './privacy.html',
  styleUrl: '../account.css',
})
export class Privacy implements OnInit {
  protected readonly form;
  protected readonly deletionForm;

  constructor(
    protected readonly privacy: PrivacyStore,
    protected readonly accountData: AccountDataStore,
    protected readonly auth: AuthStore,
    formBuilder: FormBuilder,
    private readonly router: Router,
  ) {
    this.form = formBuilder.nonNullable.group({ share_phone: [false], record_history: [true] });
    this.deletionForm = formBuilder.nonNullable.group({
      password: ['', [Validators.required, Validators.maxLength(128)]],
      confirmation: ['', [Validators.required, Validators.pattern(/^DELETE$/)]],
    });
    effect(() => {
      const values = this.privacy.privacy();
      if (values) this.form.reset(values);
    });
    effect(() => this.finishAccountChange());
  }

  ngOnInit(): void {
    this.privacy.load();
    this.accountData.load();
  }

  protected save(): void {
    const version = this.privacy.privacy()?.version;
    if (version && !this.privacy.pending() && !this.privacy.loading())
      this.privacy.save({ ...this.form.getRawValue(), version });
  }

  protected deleteAccount(): void {
    this.deletionForm.markAllAsTouched();
    if (this.deletionForm.valid && !this.accountData.deleting() && !this.accountData.pending())
      this.accountData.deleteAccount(this.deletionForm.getRawValue());
  }

  private finishAccountChange(): void {
    const receipt = this.accountData.receipt();
    if (receipt) {
      this.deletionForm.reset();
      void this.router.navigate(['/account/deletion', receipt]);
    } else if (!this.auth.user() && !this.auth.pending()) {
      void this.router.navigateByUrl('/login');
    }
  }
}
