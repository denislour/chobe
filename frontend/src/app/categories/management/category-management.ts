import { DatePipe } from '@angular/common';
import { Component, computed, effect, OnInit, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormArray, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AttributeFields } from '@app/domain/category/attribute-fields/attribute-fields';
import { CategoryNav } from '@app/categories/category-nav/category-nav';
import { AttributeDefinition, AttributeType, CategoryData } from '@app/domain/category/category-types';
import { CategoryDraft, CategoryDraftValues, CategoryRevision } from '@app/data-access/categories/category-management-api';
import { CategoryManagementStore } from './category-management.store';

interface AttributeControls {
  key: FormControl<string>;
  label: FormControl<string>;
  type: FormControl<AttributeType>;
  required: FormControl<boolean>;
  filterable: FormControl<boolean>;
  unit: FormControl<string>;
  choices: FormControl<string>;
  min_value: FormControl<number | null>;
  max_value: FormControl<number | null>;
  max_length: FormControl<number>;
}

@Component({
  selector: 'app-category-management',
  imports: [DatePipe, RouterLink, ReactiveFormsModule, AttributeFields, CategoryNav],
  providers: [CategoryManagementStore],
  templateUrl: './category-management.html',
  styleUrls: ['../../shared/styles/categories.css', './category-management.css'],
})
export class CategoryManagement implements OnInit {
  protected readonly form = new FormGroup({
    name: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.maxLength(80)],
    }),
    slug: new FormControl('', {
      nonNullable: true,
      validators: [
        Validators.required,
        Validators.maxLength(80),
        Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
      ],
    }),
    description: new FormControl('', {
      nonNullable: true,
      validators: [Validators.maxLength(1000)],
    }),
    parent: new FormControl<string | null>(null),
    sort_order: new FormControl(0, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(0)],
    }),
    restricted: new FormControl(false, { nonNullable: true }),
    attributes: new FormArray<FormGroup<AttributeControls>>([], {
      validators: (control) => {
        const fields = control.value as { key: string }[];
        const keys = fields.map((field) => field.key);
        return new Set(keys).size === keys.length ? null : { duplicateKeys: true };
      },
    }),
  });
  private readonly formValues = toSignal(this.form.valueChanges);
  protected readonly previewFields = signal<AttributeDefinition[] | null>(null);
  protected readonly pendingSelection = signal<{ id: string | null } | null>(null);
  protected readonly confirmation = signal<'publish' | 'retire' | null>(null);
  protected readonly restoring = signal(false);
  protected readonly fieldErrorText;

  constructor(protected readonly taxonomy: CategoryManagementStore) {
    this.fieldErrorText = computed(() => this.formatErrors(taxonomy.fieldErrors()));
    effect(() => {
      this.formValues();
      this.previewFields.set(null);
      this.confirmation.set(null);
    });
    effect(() => {
      const draft = taxonomy.draft();
      if (draft) this.fill(draft);
    });
  }

  ngOnInit(): void {
    this.taxonomy.load();
  }

  protected chooseCategory(id: string | null): void {
    if (this.taxonomy.pending() || this.taxonomy.selecting()) return;
    if (this.form.dirty) this.pendingSelection.set({ id });
    else this.select(id);
  }

  protected confirmSelection(): void {
    const selection = this.pendingSelection();
    this.pendingSelection.set(null);
    if (selection) this.select(selection.id);
  }

  protected addAttribute(): void {
    if (this.form.controls.attributes.length >= 30) return;
    this.form.controls.attributes.push(this.attributeGroup());
    this.form.markAsDirty();
    this.previewFields.set(null);
  }

  protected removeAttribute(index: number): void {
    this.form.controls.attributes.removeAt(index);
    this.form.markAsDirty();
    this.previewFields.set(null);
  }

  protected preview(): void {
    this.form.markAllAsTouched();
    if (this.form.valid) this.previewFields.set(this.values().attributes);
  }

  protected save(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    const draft = this.taxonomy.draft();
    this.taxonomy.save({
      id: draft?.id ?? null,
      values: {
        ...this.values(),
        ...(draft ? { version: draft.version } : {}),
      },
    });
  }

  protected transition(): void {
    const draft = this.taxonomy.draft();
    const action = this.confirmation();
    this.confirmation.set(null);
    if (!draft || !action || this.form.dirty) return;
    this.taxonomy.transition({ id: draft.id, version: draft.version, action });
  }

  protected restore(revision: CategoryRevision): void {
    this.fill({ ...revision.snapshot, restricted: this.taxonomy.draft()?.restricted ?? false });
    this.form.markAsDirty();
    this.restoring.set(true);
  }

  protected canEdit(): boolean {
    const permissions = this.taxonomy.capabilities();
    return !!(this.taxonomy.draft() ? permissions?.edit : permissions?.create);
  }

  protected parentOptions(): CategoryDraft[] {
    return this.taxonomy
      .categories()
      .filter((category) => category.id !== this.taxonomy.draft()?.id);
  }

  protected publishedVersion(): number | null {
    const published = this.taxonomy.draft()?.published;
    return published && 'version' in published ? published['version'] : null;
  }

  private select(id: string | null): void {
    this.confirmation.set(null);
    if (id) this.taxonomy.select(id);
    else {
      this.taxonomy.newDraft();
      this.fill({
        name: '',
        slug: '',
        description: '',
        parent: null,
        sort_order: 0,
        restricted: false,
        attributes: [],
      });
    }
  }

  private values(): CategoryDraftValues {
    const values = this.form.getRawValue();
    const numeric = new Set(['integer', 'number']);
    return {
      ...values,
      attributes: values.attributes.map((field) => ({
        ...field,
        unit: numeric.has(field.type) ? field.unit : '',
        min_value: numeric.has(field.type) ? field.min_value : null,
        max_value: numeric.has(field.type) ? field.max_value : null,
        choices:
          field.type === 'select'
            ? field.choices
                .split('\n')
                .filter((line) => line.trim())
                .map((line) => {
                  const [value, ...label] = line.split('|');
                  return { value: value.trim(), label: label.join('|').trim() || value.trim() };
                })
            : [],
      })),
    };
  }

  private fill(values: CategoryDraftValues | (CategoryData & { restricted: boolean })): void {
    this.form.controls.attributes.clear();
    for (const field of values.attributes)
      this.form.controls.attributes.push(this.attributeGroup(field));
    this.form.patchValue({
      name: values.name,
      slug: values.slug,
      description: values.description,
      parent: values.parent,
      sort_order: values.sort_order,
      restricted: values.restricted,
    });
    this.form.markAsPristine();
    this.form.markAsUntouched();
    this.previewFields.set(null);
    this.restoring.set(false);
  }

  private attributeGroup(field?: AttributeDefinition): FormGroup<AttributeControls> {
    return new FormGroup<AttributeControls>({
      key: new FormControl(field?.key ?? '', {
        nonNullable: true,
        validators: [
          Validators.required,
          Validators.pattern(/^(?!(?:constructor|prototype)$)[a-z][a-z0-9_]{0,39}$/),
        ],
      }),
      label: new FormControl(field?.label ?? '', {
        nonNullable: true,
        validators: [Validators.required, Validators.maxLength(80)],
      }),
      type: new FormControl<AttributeType>(field?.type ?? 'text', { nonNullable: true }),
      required: new FormControl(field?.required ?? false, { nonNullable: true }),
      filterable: new FormControl(field?.filterable ?? false, { nonNullable: true }),
      unit: new FormControl(field?.unit ?? '', {
        nonNullable: true,
        validators: [Validators.maxLength(16)],
      }),
      choices: new FormControl(
        field?.choices.map((choice) => `${choice.value}|${choice.label}`).join('\n') ?? '',
        { nonNullable: true },
      ),
      min_value: new FormControl<number | null>(field?.min_value ?? null),
      max_value: new FormControl<number | null>(field?.max_value ?? null),
      max_length: new FormControl(field?.max_length ?? 200, {
        nonNullable: true,
        validators: [Validators.required, Validators.min(1), Validators.max(1000)],
      }),
    });
  }

  private formatErrors(value: unknown, path = ''): string[] {
    if (typeof value === 'string') return [`${path ? path + ': ' : ''}${value}`];
    if (Array.isArray(value))
      return value.flatMap((item, index) =>
        this.formatErrors(item, typeof item === 'string' ? path : `${path} ${index + 1}`),
      );
    if (value && typeof value === 'object')
      return Object.entries(value).flatMap(([key, item]) =>
        this.formatErrors(item, `${path} ${key.replaceAll('_', ' ')}`.trim()),
      );
    return [];
  }
}
