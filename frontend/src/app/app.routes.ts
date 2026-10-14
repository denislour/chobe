import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'account',
    loadChildren: () => import('@app/accounts/accounts.routes').then((m) => m.accountsRoutes),
  },
  { path: '', loadChildren: () => import('@app/auth/auth.routes').then((m) => m.authRoutes) },
];
