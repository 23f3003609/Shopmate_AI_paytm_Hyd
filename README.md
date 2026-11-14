# ShopMate AI — Hackathon Prototype

ShopMate AI is a synthetic-data prototype for the Paytm Build for India AI Hackathon (Hyderabad). It demonstrates six merchant-growth workflows: voice billing, personalized offers, restock recommendations, cash-leak signals, daily briefing, and campaign impact tracking.

> **Demo safety:** All merchants, customer histories, stock counts, sales and campaign results are synthetic. The QR is a demo payload, no UPI payment is initiated, no supplier order is transmitted, and no customer message is sent. Cash Leak Check is an anomaly signal, not proof of wrongdoing.

## Run locally

Requires Python 3.10+.

```bash
cd shopmate-ai
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
# Edit .env and set SARVAM_API_KEY
uvicorn main:app --reload
```

Open http://127.0.0.1:8000.

## Sarvam AI integration

- **Chat completion:** `POST https://api.sarvam.ai/v1/chat/completions`, model `sarvam-105b`, used for structured bill extraction and offer/briefing language.
- **Speech to text:** `POST https://api.sarvam.ai/speech-to-text`, Saaras v4, English/Telugu.
- **Text to speech:** `POST https://api.sarvam.ai/text-to-speech`, Bulbul v3.

The API key stays on the backend in `.env`; it is never sent to the browser. If no key is configured, dashboard, synthetic data, inventory logic and typed billing fallback still work. Voice features and live LLM wording require a valid key and available Sarvam credits.

## Demo walkthrough

1. Overview: show synthetic sales and stock alerts.
2. Voice Billing: type `2 milk, 1 bread, 1 atta` or record a short order in English/Telugu. Review the itemized bill, optionally select the customer to apply one eligible offer, then click **Confirm purchase & record payment (demo)**. Generating a bill is only a draft; sales and stock change only after merchant confirmation.
3. Smart Offers: generate offers; non-opted-in customer Kiran is excluded.
4. Restock Assist: create a demo purchase order, then scroll to Supplier Order History to view its PO ID, supplier, product, quantity, amount, timestamp and status. Use the status dropdown to demonstrate Created → Confirmed → Dispatched → Delivered. These are manual demo statuses, not supplier acknowledgements.
5. Cash Leak Check: explain the afternoon shift's 72% collection ratio and review checklist.
6. Daily Briefing: generate English/Telugu briefing, listen via Sarvam TTS, and approve the simulated action.
7. Impact Tracker: compare offer/control repeat rates and incremental sales minus cashback cost.

## Edge cases included

- Empty or unrecognized bill input returns a clarification rather than a zero-value bill.
- Unknown catalog products are not priced or silently added.
- Quantities are clamped to 1–50; manual supplier orders are validated to 1–500.
- Sarvam calls have timeouts and readable API errors; the API key is optional for offline demo paths.
- Customers without opt-in are skipped for offers.
- No-stock-alert case returns a healthy-state message. Supplier purchase-order records are saved locally in `data/supplier_orders.json`; lifecycle status changes are simulated and do not prove supplier receipt or shipment. No real payment, supplier order or customer message is sent.

## Important prototype limitation

Most server demo state is in memory and resets on restart. Supplier order history is the exception: it is persisted locally in `data/supplier_orders.json` so created demo POs remain visible after a restart. This is intentionally not a full model-training or production integration. Replace synthetic records and in-memory state with approved Paytm merchant APIs and a persistent database only after authorization and security review.


## Merchant and customer demo flow (inspired by Munshi AI)

Open the app and choose a role at the login screen. Demo credentials:

- Merchant: `merchant` / `1111`
- Anita: `anita` / `2222`
- Rahul: `rahul` / `3333`
- Sana: `sana` / `4444`
- Kiran (not opted in): `kiran` / `5555`

As merchant, open Smart Offers, select an opted-in customer, product and cashback, then Send offer. Log out and sign in as that customer to see the offer in the notification center and manage promotional consent. Customers do not build carts or check out in this prototype. The merchant handles the purchase at the counter: open Voice Billing, record/type the customer's order, select the registered customer, review the bill and generate a pending payment request. Confirmation updates inventory, sales, transaction count and recent payments; any eligible offer for that customer and a matching product is redeemed once. The merchant Soundbox receives the payment event and announces it (click Enable sound before confirming; Sarvam TTS is used when configured, with browser speech as fallback).

All purchases and offers are simulated. No real UPI/Paytm transaction, SMS/WhatsApp delivery, or external payment settlement occurs. Merchant/customer demo activity is stored in `data/merchant_customer_demo.json`. The Soundbox event feed uses browser polling, not a live Paytm/WebSocket integration. Demo PINs are not production authentication.

## Customer-confirmed payment flow (updated)
1. Merchant creates a bill through Voice Billing and selects a known customer when possible.
2. Clicking **Generate bill & wait for customer payment** creates a pending bill. The merchant dashboard shows `WAITING`; stock and sales do not change yet.
3. The customer signs in, sees the assigned pending bill, enters the bill amount and clicks Pay (demo). The server requires the amount to match exactly.
4. Only after successful payment does ShopMate mark the bill paid, redeem one eligible offer, decrement stock, update sales/transactions and emit the Soundbox event.
5. The merchant browser polls events every 2.5 seconds and announces the payment when Soundbox sound is enabled.

New customers can create an account from the login screen. Their customer record and demo credentials are persisted locally and automatically appear in merchant customer dropdowns after refresh/polling. For a new buyer, register them first and select their customer record before generating the bill. Customer-payment requests require a registered customer selection. Unassigned walk-in bills are not exposed in customer dashboards, because they cannot safely be associated with a customer wallet or cashback offer.

All payment processing remains simulated. The amount field is a demo confirmation, not a live UPI transfer or Paytm gateway transaction.

### Microphone recording compatibility fix
Chrome records microphone audio as `audio/webm;codecs=opus`, which Saaras v4 rejects. The Voice Billing screen now decodes that browser recording and converts it in the browser to mono 16 kHz PCM WAV before uploading it to `/api/voice/transcribe`. The backend validates the WAV content type and forwards the supported format to Sarvam. No FFmpeg installation is required.

## Cashback-aware pending bill flow
- When a merchant generates a customer-payment bill, selecting a registered customer is mandatory. ShopMate checks for one unused offer belonging to that customer that matches an item in the bill.
- The matching cashback is reserved for that bill and the customer sees subtotal, cashback deduction, and the recalculated amount to pay before paying.
- The customer must pay the discounted payable amount. The offer is marked redeemed only after successful payment; the payment ledger stores subtotal, cashback, and net amount paid.
- The customer dashboard shows available cashback, cashback used, and past payments with the cashback deduction.
- The merchant bill feed and payment feed show subtotal, cashback reserved/used, and net amount received. Merchant sales and cashback-spent totals are updated using the net payment and redeemed cashback.
- Cashback is applied to at most one matching offer per bill. This remains a local simulated demo ledger, not a real Paytm/UPI cashback or payment settlement.


### Cashback/customer association safeguard
- The merchant must select the customer who will log in to pay before generating a customer-payment bill. The API rejects unassigned customer-payment requests.
- Unassigned legacy walk-in bills are no longer shown to every customer account. This prevents one customer from seeing or paying another person’s bill and prevents cashback from being attributed to the wrong wallet.
- A payment completed earlier as a walk-in sale has no customer ID and cannot be retroactively counted as that customer’s cashback redemption. Generate a new bill with the correct customer selected to apply the offer.

## Latest voice billing and cashback fixes
- Voice Billing now defaults to English speech recognition and includes an English/Telugu language selector.
- The catalog parser also recognizes common Telugu product names (including milk, bread, and atta) and merges deterministic catalog matches with AI extraction so a partial LLM response does not silently drop line items.
- Merchant customer selectors preserve the selected customer during periodic dashboard refreshes; they no longer reset to Walk-in every few seconds.
- Customer offer notifications now show Reserved/Redeemed status and identify the bill where cashback was used.
- Merchant Smart Offers and bill feed use the live demo offer/payment ledger and show cashback reserved/used plus the final amount due/received.

## SQLite-backed dashboard synchronization (November 2026)

ShopMate now maintains a local SQLite ledger at `data/shopmate.db` (`entity_records` plus an append-only `activity_log`). It records product/inventory snapshots, customers, demo users, consent, offers, pending bills, payments, notifications, supplier orders, merchant dashboard state and business events. The existing JSON demo file is retained as a compatibility backup/import source; SQLite snapshots are restored on startup after the database has been initialized. No external database service is required.

The merchant Overview, Smart Offers, Impact Tracker, Restock Assist, customer inbox/wallet and payment feeds are refreshed from the shared server-side demo state and persisted SQLite ledger. Smart Offer counts are derived from sent and redeemed offer records, not fixed display constants.

### Daily Briefing actions
- **Listen** requests Sarvam text-to-speech when configured and falls back to browser speech synthesis when Sarvam is unavailable.
- **Yes, take action** creates local demo purchase orders for low-stock products and sends ShopMate inbox cashback offers to opted-in at-risk customers. It avoids creating a duplicate open restock order or duplicate active Daily Briefing offer for the same customer.
- These are recorded demo actions only: no real supplier order, SMS, WhatsApp or Paytm message is sent.

### Cash Leak Check verification checklist
The checklist is a manual investigation aid for a shift collection variance, not an automated finding of theft. It asks the merchant to verify QR ownership, compare payment settlement with the cash book, check missed payment confirmations and discuss the variance with shift staff. Checked steps are saved in the SQLite activity log. A shortcut is also available from the Overview dashboard.

### Run
```powershell
cd .\shopmate-ai
pip install -r requirements.txt
uvicorn main:app --reload
```
The SQLite database is created automatically in `shopmate-ai/data/shopmate.db` on first startup. Keep the `data` folder writable and back it up with the project data.

### Payment completion and live dashboard reconciliation (14 Nov 2026)
- The merchant's active bill panel now detects the matching paid bill from the shared merchant summary, replaces the waiting state with a payment-completed receipt, clears the order text, and resets the draft for the next customer.
- The paid bill remains available in Pending customer payments as paid history; it is not deleted.
- Smart Offers sent, redeemed, and redemption-rate counters are calculated from the same offer ledger used to render customer offer cards.
- Overview impact counters use the same offer metrics, and merchant refreshes are serialized to prevent overlapping polling requests from applying stale responses.
- SQLite continues to persist offers, bills, payments, products, customers, dashboard state, notifications, events, and the activity log in `data/shopmate.db`.


## Merchant payment and offer reconciliation fix (14 Nov 2026)

- The merchant ledger now repairs missing offer entities from persisted customer offer notifications, preserving redeemed status and bill references. This addresses legacy records where the customer inbox showed a redeemed offer but the merchant offer ledger/counters were empty.
- Explicit SQLite ledgers (`offers`, `bills`, `payments`, `notifications`) are maintained alongside the generic entity ledger and activity log.
- Merchant summary and Overview metrics are derived from the reconciled offer and payment records.
- The merchant's active bill panel is reconciled against its bill reference on each dashboard refresh. Once payment is confirmed, the waiting message is replaced by a payment-completed receipt, and the draft input is cleared so the next bill can be created.
- Paid bills remain in history; they are not deleted.


### Offer synchronization verification build (14 Nov 2026)
- `/api/version` identifies the running build as `offer-sync-verified-2026-11-14`.
- Sending an offer explicitly persists the offer and customer notification before emitting the event.
- Merchant summary reconciles and persists the ledger before returning sent/redeemed/eligible counts.
- Merchant UI immediately renders the returned offer, then refreshes all dashboard metrics from the API.
- The root page sends no-cache headers to prevent stale HTML from being reused.

## Token-based login and prototype reset (14 Nov 2026)

- Merchant and customer login now issue a cryptographically random Bearer token.
- Tokens have a fixed **5-minute lifetime** from login (not sliding). Expired or invalid tokens receive HTTP 401 and the browser returns to the login screen.
- The browser sends the token in the `Authorization: Bearer <token>` header for protected API requests. Merchant and customer routes enforce their respective roles.
- The merchant and customer logout actions call the logout endpoint to revoke the current token, then clear the browser's session token. The merchant Soundbox WebSocket also requires a valid merchant token.
- The merchant sidebar includes **Reset test data**. After confirmation, this clears test transactions/payments, pending and paid bills, sent/redeemed offers, customer notifications, event/activity history, newly registered test customers, and supplier-order history. It also restores product stock and the original synthetic dashboard state.
- Reset retains the prototype's eight synthetic products, five original sample customers, and the original demo login accounts. It does not delete source code, API configuration, or prototype assets.
- Default demo credentials: `merchant / 1111`, `anita / 2222`, `rahul / 3333`, `sana / 4444`, `kiran / 5555`.
- This remains a local hackathon prototype. The in-memory session store is appropriate for the single-process demo server; production deployment should use a shared session store, HTTPS, password hashing, CSRF protections where applicable, and stronger account provisioning.
