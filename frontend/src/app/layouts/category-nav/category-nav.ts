import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-category-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './category-nav.html',
  styleUrl: './category-nav.css',
})
export class CategoryNav {}
