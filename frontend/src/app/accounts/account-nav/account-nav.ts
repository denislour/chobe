import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthStore } from '@app/auth/auth.store';

@Component({
  selector: 'app-account-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './account-nav.html',
  styles: `
    nav {
      display: flex;
      flex-direction: column;
      gap: 8px;
      border-right: 1px solid var(--line);
      padding-right: 20px;
    }
    a,
    button {
      padding: 10px 16px;
      min-height: 44px;
      border-radius: 7px;
      color: var(--ink);
      font-weight: 600;
    }
    a {
      text-decoration: none;
      border: 1px solid var(--line);
    }
    .active {
      background: var(--yellow);
      border-color: var(--yellow);
    }
    @media (max-width: 800px) {
      nav {
        flex-direction: row;
        flex-wrap: wrap;
        border-right: 0;
        border-bottom: 1px solid var(--line);
        padding: 0 0 16px;
      }
    }
    .error {
      color: var(--error);
    }
  `,
})
export class AccountNav {
  constructor(protected readonly auth: AuthStore) {}
}
