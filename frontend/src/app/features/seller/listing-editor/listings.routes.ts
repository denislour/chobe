import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';
import { editorLeaveGuard } from './editor-leave-guard';
export const sellerListingRoutes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    canActivate: [authGuard],
    loadComponent: () => import('@app/features/seller/listing-management/dashboard').then((m) => m.Dashboard),
  },
  {
    path: 'new',
    canActivate: [authGuard],
    canDeactivate: [editorLeaveGuard],
    loadComponent: () => import('@app/features/seller/listing-editor/editor').then((m) => m.Editor),
  },
  {
    path: ':id/edit',
    canActivate: [authGuard],
    canDeactivate: [editorLeaveGuard],
    loadComponent: () => import('@app/features/seller/listing-editor/editor').then((m) => m.Editor),
  },
];
