import { TestBed } from '@angular/core/testing';
import { ComparisonStore } from './comparison.store';
describe('ComparisonStore', () => {
  it('limits the tray to three IDs and lets users remove and add another', () => {
    const store = TestBed.inject(ComparisonStore);
    for (const id of [1, 2, 3, 4]) store.toggle(id);
    expect(store.ids()).toEqual([1, 2, 3]);
    expect(store.error()).toContain('three');
    store.toggle(2);
    store.toggle(4);
    expect(store.ids()).toEqual([1, 3, 4]);
    expect(store.error()).toBe('');
    store.clear();
    expect(store.ids()).toEqual([]);
  });
});
