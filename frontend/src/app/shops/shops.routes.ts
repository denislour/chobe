import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';

export const shopsRoutes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'shop' },
  {
    path: 'shop',
    canActivate: [authGuard],
    loadComponent: () =>
      import('@app/shops/shop-management/shop-management').then((m) => m.ShopManagement),
  },
];
