import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: 'login', loadComponent: () => import('./accounts/login/login').then((m) => m.Login) },
  {
    path: 'register',
    loadComponent: () => import('./accounts/register/register').then((m) => m.Register),
  },
  {
    path: 'forgot-password',
    loadComponent: () =>
      import('./accounts/forgot-password/forgot-password').then((m) => m.ForgotPassword),
  },
  {
    path: 'reset-password/:uid/:token',
    loadComponent: () =>
      import('./accounts/reset-password/reset-password').then((m) => m.ResetPassword),
  },
  {
    path: 'reset-password',
    loadComponent: () =>
      import('./accounts/reset-password/reset-password').then((m) => m.ResetPassword),
  },
];
