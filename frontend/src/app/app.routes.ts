import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', loadChildren: () => import('@app/auth/auth.routes').then((m) => m.authRoutes) },
];
