import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: 'seller/listings', loadChildren: () => import('@app/listings/listings.routes').then((m) => m.sellerListingRoutes) },
  { path: 'seller', loadChildren: () => import('@app/shops/shops.routes').then((m) => m.sellerShopRoutes) },
  { path: 'admin', loadChildren: () => import('@app/listings/listings.routes').then((m) => m.reviewRoutes) },
  { path: 'admin/categories', loadChildren: () => import('@app/categories/categories.routes').then((m) => m.categoryManagementRoutes) },
  { path: 'account', loadChildren: () => import('@app/accounts/accounts.routes').then((m) => m.accountsRoutes) },
  { path: '', loadChildren: () => import('@app/features/marketplace/marketplace.routes').then((m) => m.marketplaceRoutes) },
  { path: '', loadChildren: () => import('@app/auth/auth.routes').then((m) => m.authRoutes) },
];
