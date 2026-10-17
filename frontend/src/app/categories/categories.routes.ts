import { Routes } from '@angular/router';
import { authGuard } from '@app/auth/auth-guard';

export const categoriesRoutes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('@app/categories/browse/category-browser').then((m) => m.CategoryBrowser),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('@app/categories/browse/category-browser').then((m) => m.CategoryBrowser),
  },
];

export const categoryManagementRoutes: Routes = [
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () =>
      import('@app/categories/management/category-management').then((m) => m.CategoryManagement),
  },
];
