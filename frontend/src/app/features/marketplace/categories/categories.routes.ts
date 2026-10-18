import { Routes } from '@angular/router';

export const categoriesRoutes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('@app/features/marketplace/categories/category-browser').then((m) => m.CategoryBrowser),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('@app/features/marketplace/categories/category-browser').then((m) => m.CategoryBrowser),
  },
];
