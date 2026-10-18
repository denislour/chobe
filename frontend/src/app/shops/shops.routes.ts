import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';

export const sellerShopRoutes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'shop' },
  {
    path: 'shop',
    canActivate: [authGuard],
    loadComponent: () =>
      import('@app/shops/shop-management/shop-management').then((m) => m.ShopManagement),
  },
  {
    path: 'shop/preview/:slug',
    canActivate: [authGuard],
    loadComponent: () =>
      import('@app/shops/shop-preview/shop-preview').then((m) => m.ShopPreview),
  },
];

export const shopsRoutes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: '/account/followed-shops' },
  {
    path: ':slug',
    loadComponent: () =>
      import('@app/features/marketplace/shop-storefront/shop-storefront').then((m) => m.ShopStorefront),
  },
];
