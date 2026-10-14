import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DeletionReceiptStore } from '@app/accounts/privacy/deletion-receipt.store';

@Component({
  selector: 'app-deletion-receipt',
  imports: [RouterLink],
  providers: [DeletionReceiptStore],
  templateUrl: './deletion-receipt.html',
  styleUrl: '../../account.css',
})
export class DeletionReceipt implements OnInit {
  protected readonly receipt;

  constructor(
    protected readonly status: DeletionReceiptStore,
    route: ActivatedRoute,
  ) {
    this.receipt = route.snapshot.paramMap.get('receipt') ?? '';
  }

  ngOnInit(): void {
    this.status.load(this.receipt);
  }
}
