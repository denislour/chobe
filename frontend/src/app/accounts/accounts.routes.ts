import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';

export const accountsRoutes: Routes = [
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
];
