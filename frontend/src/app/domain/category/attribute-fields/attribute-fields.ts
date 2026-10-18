import { Component, effect, input, untracked } from '@angular/core';
import { outputFromObservable } from '@angular/core/rxjs-interop';
import {
  FormControl,
  FormRecord,
  ReactiveFormsModule,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import {
  AttributeDefinition,
  AttributeValue,
  AttributeValues,
} from '@app/domain/category/category-types';

@Component({
  selector: 'app-attribute-fields',
  imports: [ReactiveFormsModule],
  templateUrl: './attribute-fields.html',
  styleUrl: './attribute-fields.css',
})
export class AttributeFields {
  readonly fields = input.required<AttributeDefinition[]>();
  readonly initialValues = input<AttributeValues>({});
  readonly prefix = input('attribute');
  readonly errors = input<Record<string, string[]>>({});
  readonly disabled = input(false);
  readonly form = new FormRecord<FormControl<AttributeValue>>({});
  readonly changed = outputFromObservable(this.form.valueChanges);

  constructor() {
    effect(() => {
      const fields = this.fields();
      const initialValues = this.initialValues();
      for (const key of Object.keys(this.form.controls)) this.form.removeControl(key);
      for (const field of fields) {
        const validators: ValidatorFn[] = [];
        if (field.required)
          validators.push(
            field.type === 'boolean'
              ? (control) =>
                  control.value === null || control.value === undefined ? { required: true } : null
              : Validators.required,
          );
        if (field.type === 'text') validators.push(Validators.maxLength(field.max_length));
        if (field.min_value !== null) validators.push(Validators.min(field.min_value));
        if (field.max_value !== null) validators.push(Validators.max(field.max_value));
        this.form.addControl(
          field.key,
          new FormControl<AttributeValue>(initialValues[field.key] ?? null, validators),
        );
      }
      this.form.markAsPristine();
      if (untracked(this.disabled)) this.form.disable({ emitEvent: false });
    });
    effect(() => {
      if (this.disabled()) this.form.disable({ emitEvent: false });
      else this.form.enable({ emitEvent: false });
    });
  }

  values(): AttributeValues {
    return this.form.getRawValue();
  }
}
