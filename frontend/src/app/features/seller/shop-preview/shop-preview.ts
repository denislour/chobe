import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map, tap } from 'rxjs';
import { ShopCard } from '@app/domain/shop/shop-card/shop-card';
import { ShopPreviewStore } from './shop-preview.store';

@Component({
  selector: 'app-shop-preview',
  imports: [RouterLink, ShopCard],
  providers: [ShopPreviewStore],
  templateUrl: './shop-preview.html',
  styleUrls: ['../../../accounts/account.css', './shop-preview.css'],
})
export class ShopPreview implements OnInit {
  protected readonly slug = signal('');

  constructor(
    protected readonly preview: ShopPreviewStore,
    private readonly route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    this.preview.load(
      this.route.paramMap.pipe(
        map((params) => params.get('slug') ?? ''),
        tap((slug) => this.slug.set(slug)),
      ),
    );
  }
}
