import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';

export const accountsRoutes: Routes = [
  {
    path: 'followed-shops',
    canActivate: [authGuard],
    loadComponent: () =>
      import('@app/shops/followed-shops/followed-shops').then((m) => m.FollowedShops),
  },
  {
    path: 'profile',
    canActivate: [authGuard],
    loadComponent: () => import('@app/accounts/profile/profile').then((m) => m.Profile),
  },
  {
    path: 'privacy',
    canActivate: [authGuard],
    loadComponent: () => import('@app/accounts/privacy/privacy').then((m) => m.Privacy),
  },
  {
    path: 'deletion/:receipt',
    loadComponent: () =>
      import('@app/accounts/privacy/deletion-receipt/deletion-receipt').then(
        (m) => m.DeletionReceipt,
      ),
  },
];
