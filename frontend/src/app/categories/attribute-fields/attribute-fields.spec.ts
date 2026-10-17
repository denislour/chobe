import { TestBed } from '@angular/core/testing';
import { categoryFixture } from '@app/categories/category-fixtures';
import { AttributeFields } from './attribute-fields';

describe('AttributeFields', () => {
  it('collects a number and an explicit false value from the dynamic controls', async () => {
    await TestBed.configureTestingModule({ imports: [AttributeFields] }).compileComponents();
    const fixture = TestBed.createComponent(AttributeFields);
    fixture.componentRef.setInput('fields', categoryFixture.attributes);
    fixture.detectChanges();
    const input: HTMLInputElement = fixture.nativeElement.querySelector('input');
    input.value = '128';
    input.dispatchEvent(new Event('input'));
    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    select.value = select.options[2].value;
    select.dispatchEvent(new Event('change'));
    expect(fixture.componentInstance.values()).toEqual({ storage_gb: 128, tested: false });
    expect(fixture.componentInstance.form.valid).toBe(true);
    expect(fixture.nativeElement.textContent).toContain('Storage (GB)');
  });

  it('drops controls from the previous schema and shows server field errors', () => {
    const fixture = TestBed.createComponent(AttributeFields);
    fixture.componentRef.setInput('fields', categoryFixture.attributes);
    fixture.componentRef.setInput('errors', { storage_gb: ['Use a supported capacity.'] });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Use a supported capacity.');
    fixture.componentRef.setInput('fields', []);
    fixture.detectChanges();
    expect(fixture.componentInstance.values()).toEqual({});
    expect(fixture.nativeElement.querySelector('input')).toBeNull();
  });
});
