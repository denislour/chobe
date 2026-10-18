import { Component, input } from '@angular/core';
import { ShopDisplayData } from '@app/data-access/shops/shop-api';

@Component({
  selector: 'app-shop-card',
  imports: [],
  templateUrl: './shop-card.html',
  styleUrl: './shop-card.css',
})
export class ShopCard {
  readonly shop = input.required<ShopDisplayData>();
}
