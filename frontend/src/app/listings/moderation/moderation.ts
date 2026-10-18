import { DatePipe, KeyValuePipe } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MarketplaceNav } from '@app/listings/marketplace-nav/marketplace-nav';
import { listingPrice } from '@app/domain/listing/listing-types';
import { ModerationStore } from './moderation.store';
@Component({
  selector: 'app-moderation',
  imports: [DatePipe, KeyValuePipe, ReactiveFormsModule, RouterLink, MarketplaceNav],
  providers: [ModerationStore],
  templateUrl: './moderation.html',
  styleUrl: './moderation.css',
})
export class Moderation implements OnInit {
  protected readonly form;
  protected readonly reason;
  protected readonly page = signal(1);
  protected readonly confirmation = signal<'approve' | 'reject' | null>(null);
  protected readonly price = listingPrice;
  constructor(
    protected readonly moderation: ModerationStore,
    fb: FormBuilder,
  ) {
    this.form = fb.nonNullable.group({ status: ['pending'], appeals: [false] });
    this.reason = fb.nonNullable.control('', [Validators.required, Validators.maxLength(2000)]);
  }
  ngOnInit(): void {
    this.load();
  }
  protected load(): void {
    this.moderation.load({ ...this.form.getRawValue(), page: this.page() });
  }
  protected changePage(delta: number): void {
    this.page.update((value) => value + delta);
    this.load();
  }
  protected choose(id: number): void {
    this.confirmation.set(null);
    this.reason.reset();
    this.moderation.select(id);
  }
  protected ask(decision: 'approve' | 'reject'): void {
    if (this.reason.invalid) {
      this.reason.markAsTouched();
      return;
    }
    this.confirmation.set(decision);
  }
  protected decide(): void {
    const decision = this.confirmation();
    this.confirmation.set(null);
    if (decision) this.moderation.decide({ decision, reason: this.reason.value });
  }
}
