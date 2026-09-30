# Demo script

1. Start the app (`npm start` from the portfolio root, then open Stockroom) and show the empty catalog.
2. Click **Add sample inventory**. Point out the low-stock and out-of-stock counts.
3. Add an item with an opening quantity of 10 and open the ledger to show the `Opening stock` entry.
4. Receive 4 units, then dispatch 10. Show the item flagged **Reorder needed** and the before and after balances in the ledger.
5. Try to dispatch 5 more. The app refuses with "Only 4 units are available" and the ledger is unchanged.
6. Open the item editor and show that SKU and unit are locked while name, location, and reorder level are editable.
7. Restart the server, reload, and show the balance and ledger are intact.
