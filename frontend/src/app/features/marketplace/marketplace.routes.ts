import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';
export const marketplaceRoutes: Routes = [
  {
    path: 'categories',
    loadChildren: () => import('@app/features/marketplace/categories/categories.routes').then((m) => m.categoriesRoutes),
  },
  {
    path: 'shops',
    loadChildren: () => import('@app/features/marketplace/shop-storefront/shops.routes').then((m) => m.shopsRoutes),
  },
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
    loadComponent: () => import('@app/features/engagement/library/library').then((m) => m.Library),
  },
  {
    path: 'alerts',
    canActivate: [authGuard],
    loadComponent: () => import('@app/features/engagement/alerts/alerts').then((m) => m.Alerts),
  },
  {
    path: 'compare',
    loadComponent: () => import('@app/features/marketplace/comparison/comparison').then((m) => m.Comparison),
  },
  {
    path: 'reports',
    canActivate: [authGuard],
    loadComponent: () => import('@app/features/moderation/reports/reports').then((m) => m.Reports),
  },
];
