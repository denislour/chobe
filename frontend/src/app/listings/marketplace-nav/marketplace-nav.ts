import { Component } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { ComparisonStore } from '@app/listings/comparison/comparison.store';
@Component({
  selector: 'app-marketplace-nav',
  imports: [RouterLink, RouterLinkActive, ReactiveFormsModule],
  templateUrl: './marketplace-nav.html',
  styleUrl: './marketplace-nav.css',
})
export class MarketplaceNav {
  protected readonly query = new FormControl('', { nonNullable: true });
  constructor(
    protected readonly comparison: ComparisonStore,
    private readonly router: Router,
  ) {}
  protected search(event: Event): void {
    event.preventDefault();
    void this.router.navigate(['/search'], { queryParams: { q: this.query.value.trim() || null } });
  }
}
