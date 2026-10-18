import { DatePipe } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MarketplaceNav } from '@app/layouts/marketplace-nav/marketplace-nav';
import { ReportDecisionValues } from '@app/data-access/moderation/reports-api';
import { ReportsStore } from './reports.store';
@Component({
  selector: 'app-reports',
  imports: [DatePipe, RouterLink, ReactiveFormsModule, MarketplaceNav],
  providers: [ReportsStore],
  templateUrl: './reports.html',
  styleUrl: './reports.css',
})
export class Reports implements OnInit {
  protected readonly admin: boolean;
  protected readonly filter;
  protected readonly decision;
  protected readonly page = signal(1);
  protected readonly confirmation = signal(false);
  constructor(
    protected readonly reports: ReportsStore,
    route: ActivatedRoute,
    fb: FormBuilder,
  ) {
    this.admin = route.snapshot.data['admin'] === true;
    this.filter = fb.nonNullable.control('');
    this.decision = fb.nonNullable.group({
      action: ['review'],
      reason: ['', [Validators.required, Validators.maxLength(2000)]],
      response: ['', [Validators.required, Validators.maxLength(500)]],
    });
  }
  ngOnInit(): void {
    this.load();
  }
  protected load(): void {
    this.reports.load({ admin: this.admin, status: this.filter.value, page: this.page() });
  }
  protected changePage(delta: number): void {
    this.page.update((value) => value + delta);
    this.load();
  }
  protected ask(): void {
    if (this.decision.invalid) {
      this.decision.markAllAsTouched();
      return;
    }
    this.confirmation.set(true);
  }
  protected decide(): void {
    const selected = this.reports.selected();
    if (!selected) return;
    this.confirmation.set(false);
    this.reports.decide({
      id: selected.id,
      values: { ...this.decision.getRawValue(), version: selected.version } as ReportDecisionValues,
    });
  }
}
