import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: 'login', loadComponent: () => import('./accounts/login/login').then((m) => m.Login) },
  {
    path: 'register',
    loadComponent: () => import('./accounts/register/register').then((m) => m.Register),
  },
];
