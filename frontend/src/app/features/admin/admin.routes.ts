import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';
export const adminRoutes: Routes = [
  {
    path: 'categories',
    canActivate: [authGuard],
    loadComponent: () => import('@app/features/admin/categories/category-management').then((m) => m.CategoryManagement),
  },
  {
    path: 'moderation',
    canActivate: [authGuard],
    loadComponent: () => import('@app/features/admin/moderation/moderation').then((m) => m.Moderation),
  },
  {
    path: 'reports',
    canActivate: [authGuard],
    data: { admin: true },
    loadComponent: () => import('@app/features/moderation/reports/reports').then((m) => m.Reports),
  },
];
