import { Component, effect, OnInit, untracked } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AccountNav } from '@app/accounts/account-nav/account-nav';
import { AuthStore } from '@app/auth/auth.store';
import { ShopData } from '@app/shops/shop-api';
import { ShopStore } from '@app/shops/shop.store';

@Component({
  selector: 'app-shop-management',
  imports: [ReactiveFormsModule, RouterLink, AccountNav],
  providers: [ShopStore],
  templateUrl: './shop-management.html',
  styleUrls: ['../../accounts/account.css', './shop-management.css'],
})
export class ShopManagement implements OnInit {
  protected readonly form;
  protected readonly statusLabels = {
    active: 'Active',
    paused: 'Paused',
    suspended: 'Suspended',
    closed: 'Closed',
  };

  constructor(
    protected readonly shop: ShopStore,
    protected readonly auth: AuthStore,
    formBuilder: FormBuilder,
    private readonly router: Router,
  ) {
    this.form = formBuilder.nonNullable.group({
      name: ['', [Validators.required, Validators.maxLength(80)]],
      slug: [
        '',
        [Validators.required, Validators.maxLength(80), Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)],
      ],
      area: ['', [Validators.required, Validators.maxLength(120)]],
      contact_hours: ['', Validators.maxLength(120)],
      description: ['', [Validators.required, Validators.maxLength(1000)]],
      website_url: ['', [Validators.maxLength(400), Validators.pattern(/^https?:\/\/[^\s]+$/)]],
      social_url: ['', [Validators.maxLength(400), Validators.pattern(/^https?:\/\/[^\s]+$/)]],
    });
    effect(() => {
      const shop = this.shop.shop();
      untracked(() => this.resetForm(shop));
    });
    effect(() => {
      if (!this.auth.user() && !this.auth.pending()) void this.router.navigateByUrl('/login');
    });
  }

  ngOnInit(): void {
    this.shop.load();
  }

  protected suggestSlug(): void {
    const slug = this.form.controls.name.value
      .normalize('NFKD')
      .toLowerCase()
      .replace(/đ/g, 'd')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 80)
      .replace(/-$/g, '');
    this.form.controls.slug.setValue(slug);
    this.form.controls.slug.markAsDirty();
  }

  protected submit(): void {
    this.form.markAllAsTouched();
    if (!this.canSubmit()) return;
    const current = this.shop.shop();
    const body = new FormData();
    for (const [key, value] of Object.entries(this.form.getRawValue()))
      body.set(key, String(value));
    if (current) body.set('version', String(current.version));
    this.shop.save({ id: current?.id ?? null, body });
  }

  private canSubmit(): boolean {
    return this.form.valid && this.shop.loaded() && !this.shop.loading() && !this.shop.pending()
      && this.shop.shop()?.status !== 'closed';
  }

  private resetForm(shop: ShopData | null): void {
    this.form.reset({
      name: shop?.name ?? '',
      slug: shop?.slug ?? '',
      area: shop?.area ?? '',
      contact_hours: shop?.contact_hours ?? '',
      description: shop?.description ?? '',
      website_url: shop?.website_url ?? '',
      social_url: shop?.social_url ?? '',
    });
  }
}
