import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'seller',
    loadChildren: () => import('@app/shops/shops.routes').then((m) => m.sellerShopRoutes),
  },
  {
    path: 'shops',
    loadChildren: () => import('@app/shops/shops.routes').then((m) => m.shopsRoutes),
  },
  {
    path: 'account',
    loadChildren: () => import('@app/accounts/accounts.routes').then((m) => m.accountsRoutes),
  },
  { path: '', loadChildren: () => import('@app/auth/auth.routes').then((m) => m.authRoutes) },
];
