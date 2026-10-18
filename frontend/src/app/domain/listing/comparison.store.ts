import { Injectable } from '@angular/core';
import { patchState, signalState } from '@ngrx/signals';
interface ComparisonState {
  ids: number[];
  error: string;
}
@Injectable({ providedIn: 'root' })
export class ComparisonStore {
  private readonly state = signalState<ComparisonState>({ ids: [], error: '' });
  readonly ids = this.state.ids;
  readonly error = this.state.error;
  toggle(id: number): void {
    const ids = this.ids();
    if (ids.includes(id))
      patchState(this.state, { ids: ids.filter((value) => value !== id), error: '' });
    else if (ids.length < 3) patchState(this.state, { ids: [...ids, id], error: '' });
    else
      patchState(this.state, {
        error: 'Compare up to three listings. Remove one before adding another.',
      });
  }
  clear(): void {
    patchState(this.state, { ids: [], error: '' });
  }
}
