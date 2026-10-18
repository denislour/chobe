import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthStore } from '@app/auth/auth.store';

@Component({
  selector: 'app-shop-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './shop-nav.html',
  styleUrl: './shop-nav.css',
})
export class ShopNav {
  constructor(protected readonly auth: AuthStore) {}
}
