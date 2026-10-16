import { Component, computed, DestroyRef, effect, ElementRef, OnInit, signal, untracked, viewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AccountNav } from '@app/accounts/account-nav/account-nav';
import { AuthStore } from '@app/auth/auth.store';
import { ShopData, ShopDisplayData } from '@app/shops/shop-api';
import { ShopCard } from '@app/shops/shop-card/shop-card';
import { ShopStore } from '@app/shops/shop.store';

@Component({
  selector: 'app-shop-management',
  imports: [ReactiveFormsModule, RouterLink, AccountNav, ShopCard],
  providers: [ShopStore],
  templateUrl: './shop-management.html',
  styleUrls: ['../../accounts/account.css', './shop-management.css'],
})
export class ShopManagement implements OnInit {
  protected readonly form;
  protected readonly previewData;
  protected readonly previewing = signal(false);
  protected readonly selectedLogo = signal<File | null>(null);
  protected readonly selectedBanner = signal<File | null>(null);
  protected readonly logoPreview = signal<string | null>(null);
  protected readonly bannerPreview = signal<string | null>(null);
  protected readonly uploadErrors = signal({ logo: '', banner: '' });
  private readonly logoInput = viewChild<ElementRef<HTMLInputElement>>('logoInput');
  private readonly bannerInput = viewChild<ElementRef<HTMLInputElement>>('bannerInput');
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
    destroyRef: DestroyRef,
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
      remove_logo: [false],
      remove_banner: [false],
    });
    const values = toSignal(this.form.valueChanges, { initialValue: this.form.getRawValue() });
    this.previewData = computed<ShopDisplayData>(() => {
      const draft = values();
      const saved = this.shop.shop();
      return {
        name: draft.name ?? '',
        slug: draft.slug ?? '',
        area: draft.area ?? '',
        contact_hours: draft.contact_hours ?? '',
        description: draft.description ?? '',
        website_url: draft.website_url ?? '',
        social_url: draft.social_url ?? '',
        logo_url: draft.remove_logo ? null : this.logoPreview() ?? saved?.logo_url ?? null,
        banner_url: draft.remove_banner ? null : this.bannerPreview() ?? saved?.banner_url ?? null,
        status: saved?.status ?? 'active',
      };
    });
    effect(() => {
      const shop = this.shop.shop();
      untracked(() => this.resetForm(shop));
    });
    effect(() => {
      if (!this.auth.user() && !this.auth.pending()) void this.router.navigateByUrl('/login');
    });
    destroyRef.onDestroy(() => this.releaseImagePreviews());
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

  protected chooseImage(kind: 'logo' | 'banner', event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    const invalid = file && (
      file.size > 2 * 1024 * 1024 || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)
    );
    const error = invalid ? 'Choose a JPEG, PNG, or WebP image up to 2 MiB.' : '';
    this.uploadErrors.update((errors) => ({ ...errors, [kind]: error }));
    if (error) input.value = '';
    const preview = kind === 'logo' ? this.logoPreview : this.bannerPreview;
    const selected = kind === 'logo' ? this.selectedLogo : this.selectedBanner;
    const previous = preview();
    if (previous) URL.revokeObjectURL(previous);
    selected.set(error ? null : file);
    preview.set(file && !error ? URL.createObjectURL(file) : null);
    if (file && !error) {
      const removal = kind === 'logo' ? this.form.controls.remove_logo : this.form.controls.remove_banner;
      removal.setValue(false);
      this.form.markAsDirty();
    }
  }

  protected submit(): void {
    this.form.markAllAsTouched();
    if (!this.canSubmit()) return;
    const current = this.shop.shop();
    const body = new FormData();
    for (const [key, value] of Object.entries(this.form.getRawValue()))
      body.set(key, String(value));
    if (current) body.set('version', String(current.version));
    const logo = this.selectedLogo();
    const banner = this.selectedBanner();
    if (logo && !this.form.controls.remove_logo.value) body.set('logo', logo);
    if (banner && !this.form.controls.remove_banner.value) body.set('banner', banner);
    this.shop.save({ id: current?.id ?? null, body });
  }

  protected preview(): void {
    this.form.markAllAsTouched();
    if (this.form.valid && !this.uploadErrors().logo && !this.uploadErrors().banner)
      this.previewing.set(true);
  }

  private canSubmit(): boolean {
    return this.form.valid && this.shop.loaded() && !this.shop.loading() && !this.shop.pending()
      && this.shop.shop()?.status !== 'closed'
      && !this.uploadErrors().logo && !this.uploadErrors().banner;
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
      remove_logo: false,
      remove_banner: false,
    });
    this.selectedLogo.set(null);
    this.selectedBanner.set(null);
    this.uploadErrors.set({ logo: '', banner: '' });
    this.releaseImagePreviews();
    this.previewing.set(false);
    for (const input of [this.logoInput(), this.bannerInput()]) {
      if (input) input.nativeElement.value = '';
    }
  }

  private releaseImagePreviews(): void {
    for (const url of [this.logoPreview(), this.bannerPreview()]) {
      if (url) URL.revokeObjectURL(url);
    }
    this.logoPreview.set(null);
    this.bannerPreview.set(null);
  }
}
