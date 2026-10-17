import { Routes } from '@angular/router';

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

