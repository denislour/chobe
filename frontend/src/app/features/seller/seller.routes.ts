import { Routes } from '@angular/router';

export const sellerRoutes: Routes = [
  {
    path: 'listings',
    loadChildren: () => import('./listing-editor/listings.routes').then((m) => m.sellerListingRoutes),
  },
  {
    path: '',
    loadChildren: () => import('./shop-settings/shops.routes').then((m) => m.sellerShopRoutes),
  },
];
