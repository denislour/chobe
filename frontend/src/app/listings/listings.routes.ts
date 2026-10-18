import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';
import { editorLeaveGuard } from '@app/listings/editor/editor-leave-guard';
export const marketplaceRoutes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () => import('@app/features/marketplace/home/home').then((m) => m.Home),
  },
  {
    path: 'search',
    loadComponent: () => import('@app/features/marketplace/search/search').then((m) => m.Search),
  },
  {
    path: 'listings/:id',
    loadComponent: () => import('@app/features/marketplace/listing-detail/detail').then((m) => m.Detail),
  },
  {
    path: 'saved',
    canActivate: [authGuard],
    loadComponent: () => import('@app/listings/library/library').then((m) => m.Library),
  },
  {
    path: 'alerts',
    canActivate: [authGuard],
    loadComponent: () => import('@app/listings/alerts/alerts').then((m) => m.Alerts),
  },
  {
    path: 'compare',
    loadComponent: () => import('@app/features/marketplace/comparison/comparison').then((m) => m.Comparison),
  },
  {
    path: 'reports',
    canActivate: [authGuard],
    loadComponent: () => import('@app/listings/reports/reports').then((m) => m.Reports),
  },
];
export const sellerListingRoutes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    canActivate: [authGuard],
    loadComponent: () => import('@app/listings/dashboard/dashboard').then((m) => m.Dashboard),
  },
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
  {
    path: 'reports',
    canActivate: [authGuard],
    data: { admin: true },
    loadComponent: () => import('@app/listings/reports/reports').then((m) => m.Reports),
  },
];
