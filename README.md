# Order Cancellation (Frappe / ERPNext App)

A Frappe & ERPNext app that automatically handles the cancellation of linked transactions and reactivates Serial Numbers whenever a return invoice (Credit Note) is submitted.

## Key Features

1. **Automatic Payment Entry Cancellation**:
   - When a Return Sales Invoice is submitted, all linked submitted `Payment Entry` documents are automatically cancelled.
   - Draft and already cancelled Payment Entries are ignored safely.

2. **Automatic Sales Order & Delivery Note Cancellation**:
   - Linked submitted `Sales Order`(s) and `Delivery Note`(s) associated with the invoice/order are automatically cancelled.
   - Draft or already cancelled Sales Orders and Delivery Notes are safely ignored without raising errors.
   - Clears return invoice item link references to bypass ERPNext's return validation constraints (`"Delivery Note is not submitted"` or `"Sales Order must be deleted"`).

3. **Automatic Serial Number Reactivation**:
   - Collects all Serial Numbers involved in the returned invoice, sales order, or delivery note.
   - Sets their status back to `"Active"` so they can immediately be re-used/re-sold.

4. **Robust Multi-Status Handling**:
   - Acts appropriately across all states: Draft, Submitted, or Cancelled for SO, SI, DN, and Payment Entry.

---

## Installation

```bash
cd ~/frappe/frappe-bench-v14
bench get-app https://github.com/Marwan-badr543/order-cancellation-frappe-app
bench --site <your-site-name> install-app order_cancellation
bench --site <your-site-name> clear-cache
bench build --app order_cancellation
```

---

## Running Tests

```bash
bench --site <your-site-name> run-tests --app order_cancellation
```

---

## License

MIT