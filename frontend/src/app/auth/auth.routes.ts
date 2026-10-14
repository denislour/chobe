import { Routes } from '@angular/router';

export const authRoutes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: 'login', loadComponent: () => import('@app/auth/login/login').then((m) => m.Login) },
  {
    path: 'register',
    loadComponent: () => import('@app/auth/register/register').then((m) => m.Register),
  },
  {
    path: 'forgot-password',
    loadComponent: () =>
      import('@app/auth/forgot-password/forgot-password').then((m) => m.ForgotPassword),
  },
  {
    path: 'reset-password/:uid/:token',
    loadComponent: () =>
      import('@app/auth/reset-password/reset-password').then((m) => m.ResetPassword),
  },
  {
    path: 'reset-password',
    loadComponent: () =>
      import('@app/auth/reset-password/reset-password').then((m) => m.ResetPassword),
  },
];
