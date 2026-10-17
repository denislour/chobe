import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';
import { editorLeaveGuard } from '@app/listings/editor/editor-leave-guard';
export const sellerListingRoutes: Routes = [
  {
    path: 'new',
    canActivate: [authGuard],
    canDeactivate: [editorLeaveGuard],
    loadComponent: () => import('@app/listings/editor/editor').then((m) => m.Editor),
  },
  {
    path: ':id/edit',
    canActivate: [authGuard],
    canDeactivate: [editorLeaveGuard],
    loadComponent: () => import('@app/listings/editor/editor').then((m) => m.Editor),
  },
];
export const reviewRoutes: Routes = [
  {
    path: 'moderation',
    canActivate: [authGuard],
    loadComponent: () => import('@app/listings/moderation/moderation').then((m) => m.Moderation),
  },
];
export const marketplaceRoutes: Routes = [
];
