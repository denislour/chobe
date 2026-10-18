import { Routes } from '@angular/router';

export const shopsRoutes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: '/account/followed-shops' },
  {
    path: ':slug',
    loadComponent: () =>
      import('@app/features/marketplace/shop-storefront/shop-storefront').then((m) => m.ShopStorefront),
  },
];
