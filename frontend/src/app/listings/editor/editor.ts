import { DatePipe } from '@angular/common';
import {
  Component,
  Injector,
  OnInit,
  computed,
  effect,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { AttributeFields } from '@app/categories/attribute-fields/attribute-fields';
import { AttributeValues } from '@app/categories/category-types';
import { MarketplaceNav } from '@app/listings/marketplace-nav/marketplace-nav';
import { ListingValues, listingPrice } from '@app/listings/listing-types';
import { EditorStore } from './editor.store';
@Component({
  selector: 'app-editor',
  imports: [DatePipe, RouterLink, ReactiveFormsModule, AttributeFields, MarketplaceNav],
  providers: [EditorStore],
  templateUrl: './editor.html',
  styleUrl: './editor.css',
})
export class Editor implements OnInit {
  private readonly attributeForm = viewChild(AttributeFields);
  private id: number | null = null;
  protected readonly categoryId = signal('');
  protected readonly initialAttributes = signal<AttributeValues>({});
  protected readonly preview = signal(false);
  protected readonly confirmation = signal<'reload' | 'submit' | null>(null);
  protected readonly pendingCategory = signal<string | null>(null);
  protected readonly localError = signal('');
  protected readonly category = computed(() =>
    this.editor.categories().find((item) => item.id === this.categoryId()),
  );
  protected readonly fields = computed(() => this.category()?.attributes ?? []);
  protected readonly price = listingPrice;
  protected readonly form;
  protected readonly appeal;
  constructor(
    protected readonly editor: EditorStore,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly injector: Injector,
    fb: FormBuilder,
  ) {
    this.form = fb.group({
      title: fb.nonNullable.control('', Validators.maxLength(160)),
      description: fb.nonNullable.control('', Validators.maxLength(10000)),
      category: fb.nonNullable.control(''),
      condition: fb.nonNullable.control<'used' | 'new'>('used'),
      price_mode: fb.nonNullable.control<'fixed' | 'negotiable' | 'free'>('fixed'),
      price: fb.control<number | null>(null, Validators.min(0)),
      area: fb.nonNullable.control('', Validators.maxLength(120)),
      phone_consent: fb.nonNullable.control(false),
      rights_confirmed: fb.nonNullable.control(false),
    });
    this.appeal = fb.nonNullable.control('', [Validators.required, Validators.maxLength(2000)]);
    effect(() => {
      const listing = this.editor.listing();
      if (!listing) return;
      untracked(() => {
        this.id = listing.id;
        this.form.reset({
          title: listing.title,
          description: listing.description,
          category: listing.category ?? '',
          condition: listing.condition,
          price_mode: listing.price_mode,
          price: listing.price,
          area: listing.area,
          phone_consent: listing.phone_consent,
          rights_confirmed: listing.rights_confirmed,
        });
        this.categoryId.set(listing.category ?? '');
        this.initialAttributes.set(listing.attributes);
        if (!this.route.snapshot.paramMap.get('id'))
          void this.router.navigate(['/seller/listings', listing.id, 'edit'], { replaceUrl: true });
      });
    });
  }
  ngOnInit(): void {
    this.editor.load(
      this.route.paramMap.pipe(
        map((params) => {
          this.id = params.get('id') ? Number(params.get('id')) : null;
          return this.id;
        }),
      ),
      { injector: this.injector },
    );
  }
  hasUnsavedChanges(): boolean {
    return this.form.dirty || !!this.attributeForm()?.form.dirty;
  }
  protected previewDetails(): { key: string; label: string; value: string; unit: string }[] {
    const values = this.attributeForm()?.values() ?? {};
    return this.fields().map((field) => ({
      key: field.key,
      label: field.label,
      value:
        values[field.key] === null || values[field.key] === undefined
          ? 'Not provided'
          : String(values[field.key]),
      unit: values[field.key] === null || values[field.key] === undefined ? '' : field.unit,
    }));
  }

  protected save(): void {
    this.localError.set('');
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.localError.set('Check the highlighted fields.');
      return;
    }
    const values = this.form.getRawValue();
    const listing = this.editor.listing();
    const category = this.category();
    const payload: ListingValues & { version?: number } = {
      ...values,
      category: values.category || null,
      price: values.price_mode === 'free' ? 0 : values.price,
      attributes: this.attributeForm()?.values() ?? {},
      schema_version: category?.version ?? listing?.schema_version ?? 1,
      ...(listing ? { version: listing.version } : {}),
    };
    this.editor.mutate({ kind: 'save', id: this.id, values: payload });
    this.preview.set(false);
  }
  protected categoryChanged(): void {
    const next = this.form.controls.category.value;
    if (this.attributeForm()?.form.dirty) {
      this.pendingCategory.set(next);
      this.form.controls.category.setValue(this.categoryId(), { emitEvent: false });
      return;
    }
    this.setCategory(next);
  }
  protected setCategory(value: string): void {
    this.categoryId.set(value);
    this.form.controls.category.setValue(value);
    this.initialAttributes.set({});
    this.pendingCategory.set(null);
    this.form.markAsDirty();
  }
  protected upload(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    const listing = this.editor.listing();
    if (file && listing) {
      if (file.size > 5 * 1024 * 1024) {
        this.localError.set('Use an image smaller than 5 MiB.');
        return;
      }
      this.editor.mutate({ kind: 'upload', id: listing.id, version: listing.version, file });
    }
    input.value = '';
  }
  protected moveImage(id: string, offset: number): void {
    const listing = this.editor.listing();
    if (!listing) return;
    const ids = listing.images.map((image) => image.id);
    const index = ids.indexOf(id);
    const destination = index + offset;
    if (destination < 0 || destination >= ids.length) return;
    [ids[index], ids[destination]] = [ids[destination], ids[index]];
    this.editor.mutate({ kind: 'images', id: listing.id, version: listing.version, images: ids });
  }

  protected imageAction(id: string, remove: boolean): void {
    const listing = this.editor.listing();
    if (!listing) return;
    const ids = listing.images.map((image) => image.id).filter((value) => value !== id);
    if (!remove) ids.unshift(id);
    this.editor.mutate({ kind: 'images', id: listing.id, version: listing.version, images: ids });
  }
  protected confirm(): void {
    const kind = this.confirmation();
    this.confirmation.set(null);
    if (kind === 'reload') this.editor.load(this.id);
    if (kind === 'submit') {
      const listing = this.editor.listing();
      if (listing) this.editor.mutate({ kind: 'submit', id: listing.id, version: listing.version });
    }
  }
  protected reload(): void {
    if (this.hasUnsavedChanges()) this.confirmation.set('reload');
    else this.editor.load(this.id);
  }
  protected sendAppeal(): void {
    const listing = this.editor.listing();
    if (!listing || this.appeal.invalid) {
      this.appeal.markAsTouched();
      return;
    }
    this.editor.mutate({
      kind: 'appeal',
      id: listing.id,
      version: listing.version,
      reason: this.appeal.value,
    });
  }
}
