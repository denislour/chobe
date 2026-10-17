import { Component, input } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthStore } from '@app/auth/auth.store';
import { ReportFormStore } from './report-form.store';
@Component({
  selector: 'app-report-form',
  imports: [ReactiveFormsModule, RouterLink],
  providers: [ReportFormStore],
  templateUrl: './report-form.html',
  styleUrl: './report-form.css',
})
export class ReportForm {
  readonly listingId = input<number | null>(null);
  readonly shopId = input<string | null>(null);
  protected readonly form;
  constructor(
    protected readonly report: ReportFormStore,
    private readonly auth: AuthStore,
    private readonly router: Router,
    fb: FormBuilder,
  ) {
    this.form = fb.nonNullable.group({
      reason: ['incorrect', Validators.required],
      description: ['', [Validators.required, Validators.maxLength(2000)]],
    });
  }
  protected submit(): void {
    if (!this.auth.user()) {
      void this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.report.submit({
      ...this.form.getRawValue(),
      ...(this.listingId() ? { listing: this.listingId()! } : { shop: this.shopId()! }),
    });
  }
}
