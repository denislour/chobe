import { CanDeactivateFn } from '@angular/router';
import type { Editor } from './editor';
export const editorLeaveGuard: CanDeactivateFn<Editor> = (component) =>
  !component.hasUnsavedChanges() || window.confirm('Leave this page and discard unsaved changes?');
