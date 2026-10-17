import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'seller/listings',
    loadChildren: () => import('@app/listings/listings.routes').then((m) => m.sellerListingRoutes),
  },
  {
    path: 'admin',
    loadChildren: () => import('@app/listings/listings.routes').then((m) => m.reviewRoutes),
  },
  {
    path: '',
    loadChildren: () => import('@app/listings/listings.routes').then((m) => m.marketplaceRoutes),
  },
  {
    path: 'categories',
    loadChildren: () => import('@app/categories/categories.routes').then((m) => m.categoriesRoutes),
  },
  {
    path: 'admin/categories',
    loadChildren: () =>
      import('@app/categories/categories.routes').then((m) => m.categoryManagementRoutes),
  },
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
