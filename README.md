# ShopMate AI

**An AI-powered growth partner for neighbourhood retailers.**

ShopMate AI is a merchant-first prototype built for the Paytm Build for India AI Hackathon in Hyderabad. It brings everyday kirana-store workflows into one workspace: voice-assisted billing, customer offers and cashback, inventory restocking, payment announcements, business health checks, and daily action recommendations.

> **Prototype notice:** ShopMate uses synthetic store data and simulated customer payments, cashback, supplier orders, and notifications. It does not initiate UPI/Paytm payments, contact suppliers, or send SMS/WhatsApp messages. Do not enter real customer or payment data.

---

## Contents

- [What ShopMate does](#what-shopmate-does)
- [Features and how to use them](#features-and-how-to-use-them)
- [Getting started](#getting-started)
- [Sign-in accounts](#sign-in-accounts)
- [Merchant workflow](#merchant-workflow-end-to-end)
- [Customer workflow](#customer-workflow)
- [AI and voice capabilities](#ai-and-voice-capabilities)
- [Authentication and sessions](#authentication-and-sessions)
- [Resetting prototype activity](#resetting-prototype-activity)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [API overview](#api-overview)
- [Troubleshooting](#troubleshooting)
- [Prototype limitations and security](#prototype-limitations-and-security)

## What ShopMate does

Small retailers often manage billing, inventory, customer retention, and supplier follow-ups separately. ShopMate demonstrates how an AI-assisted merchant workspace can connect those activities using a shared prototype ledger.

The design is **merchant-first**: the merchant creates the bill and manages the sale. A customer can sign in to view an assigned bill, complete the simulated payment, see cashback history, and receive offers in their ShopMate inbox.

## Features and how to use them

### 1. Overview dashboard

A single view of the store's synthetic operating picture:

- Sales and transaction summary.
- Average bill and recent transaction activity.
- Product stock and low-stock signals.
- Shortcuts into merchant workflows.

The figures are illustrative and update as you complete actions in the prototype.

### 2. Voice Billing

Create an itemised bill by speaking or typing an order.

1. Open **Voice Billing**.
2. Enter an order such as `2 milk, 1 bread` or use the microphone.
3. Choose the recognition language where available (English/Telugu).
4. Review the recognised products, quantities, prices, and bill total.
5. Select the registered customer who will pay. Selecting the correct customer is important for associating the payment and any eligible cashback.
6. Generate the bill and wait for customer payment.
7. The customer opens their account, selects the pending bill, enters the exact payable amount, and confirms the simulated payment.
8. The merchant workspace reconciles the bill, stock, sales, payment history, and Soundbox announcement.

A bill remains in **Waiting for customer payment** until the customer payment action succeeds. Stock and sales are updated only after successful payment. Paid bills remain visible in payment history.

### 3. Smart Offers

Create personalised cashback offers for customers who have opted in to promotional messages.

1. Open **Smart Offers**.
2. Select an eligible customer and a product.
3. Enter the cashback amount and optionally write a message.
4. Select **Send offer**.
5. The offer appears in the merchant's Customer offers list and in the customer's ShopMate inbox.
6. The dashboard shows eligible customers, offers sent, redeemed offers, and redemption rate based on the offer ledger.

An offer can be redeemed against a matching product on a subsequent qualifying bill. Cashback is reserved for the bill and marked redeemed only after the customer completes payment. A single bill can apply at most one matching offer.

Customers who have not opted in are excluded from promotional offer delivery. Customers can manage their consent from their account.

### 4. Restock Assist

Review products that are at or below their reorder thresholds and create a simulated supplier purchase order.

1. Open **Restock Assist**.
2. Review low-stock products and suggested replenishment quantities.
3. Create a purchase order for the required product and quantity.
4. Review the order in supplier order history.
5. Update its status through the available lifecycle controls to demonstrate the workflow.

Supplier status changes are manual prototype actions. No order is sent to a real supplier.

### 5. Cash Leak Check

Review collection variances and a structured investigation checklist. This is an operational prompt to help a merchant check records such as QR ownership, settlement information, cash-book entries, and missed payment confirmations.

**A variance is only a signal to investigate; it is not evidence of theft or wrongdoing.**

### 6. Daily Briefing

Generate a short store briefing and recommended next action.

1. Open **Daily Briefing**.
2. Select English or Telugu.
3. Generate the briefing.
4. Use **Listen** to hear the briefing.
5. Review the suggested action before selecting **Yes, take action**.

Depending on the generated recommendations, the prototype can create local restock orders or send ShopMate inbox offers to opted-in customers. These actions remain within the local prototype.

### 7. Impact Tracker

Review offer activity and illustrative campaign impact, including offer delivery/redemption and cashback cost. These are prototype ledger calculations, not independently measured causal campaign results or actual Paytm campaign analytics.

### 8. Customer workspace

Customers can:

- View pending bills assigned to their account.
- Pay the exact amount requested in the simulated payment flow.
- View previous payments and cashback used.
- Read merchant offers and notifications.
- Manage promotional opt-in consent.
- Log out of their account.

### 9. Payment Soundbox

When a customer completes a pending bill payment, ShopMate emits a payment event to the merchant workspace. The merchant browser can announce the amount and customer using Sarvam text-to-speech when configured, with browser speech synthesis as a fallback. Enable browser sound when prompted.

This is a software simulation; it is not connected to physical Paytm Soundbox hardware.

## Getting started

### Requirements

- Python 3.10 or newer.
- pip.
- A modern browser (Chrome or Edge recommended).
- Optional: a Sarvam AI API key for AI text and voice features.

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd <REPOSITORY_FOLDER>
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

Open `.env` and add your Sarvam API key if you want to use the Sarvam-powered AI and voice features. Never commit `.env` or share your API key.

### 5. Start the application

Run this command from the directory containing `main.py`:

```bash
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000** in your browser.

To stop the server, press `Ctrl + C` in the terminal.

## Sign-in accounts

The project includes preconfigured prototype accounts:

| Role | Username | PIN |
|---|---|---|
| Merchant | `merchant` | `1111` |
| Customer | `anita` | `2222` |
| Customer | `rahul` | `3333` |
| Customer | `sana` | `4444` |
| Customer | `kiran` | `5555` |

New customer registration is available from the login screen. The merchant customer selector is populated from the current customer records. Use synthetic information only.

## Merchant workflow end-to-end

A simple way to demonstrate the complete experience:

1. Sign in with the merchant account.
2. Open **Smart Offers** and send Anita a cashback offer for a product (for example, Milk 500ml).
3. Open **Voice Billing** and create a bill for Anita that includes the same product.
4. Generate the bill and leave it waiting for payment.
5. Sign out of the merchant account and sign in as Anita.
6. Open the pending bill, check the cashback deduction and payable amount, then pay the exact amount.
7. Sign back in as merchant.
8. Verify that the bill is paid, the offer is redeemed, the inventory and sales have changed, and the payment announcement is available.
9. Explore **Overview**, **Restock Assist**, **Cash Leak Check**, **Daily Briefing**, and **Impact Tracker**.

## Customer workflow

1. Sign in using one of the customer accounts or register a new prototype customer.
2. Review any pending bill assigned to that account.
3. Enter the exact payable amount and complete the simulated payment.
4. Review cashback wallet and past payments.
5. Open Offers & notifications to see merchant offers.
6. Change promotional consent if needed.
7. Use **Log out** to end the session.

## AI and voice capabilities

ShopMate integrates with Sarvam AI from the backend:

- **Chat completion:** structured order interpretation and natural-language generation for offer/briefing workflows. Default model: `sarvam-105b`.
- **Speech-to-text:** Saaras v4 for voice order transcription, with English/Telugu support in the app.
- **Text-to-speech:** Bulbul v3 for spoken briefings and payment announcements.
- **Fallbacks:** typed billing remains available without Sarvam; browser speech synthesis can be used for announcements when the Sarvam key or service is unavailable.

The Sarvam API key is read by the backend from `.env`. It is not embedded in the browser code.
Microphone recordings are converted in the browser to mono 16 kHz PCM WAV before upload, so no FFmpeg installation is required.

## Authentication and sessions

- Login issues a cryptographically random Bearer token.
- Tokens have a fixed **5-minute lifetime** from login; activity does not extend the expiry.
- Protected API calls send `Authorization: Bearer <token>`.
- Merchant and customer endpoints enforce their respective roles.
- Refreshing the page in the same browser tab restores the session from `sessionStorage`, provided the server-side token is still valid.
- Logout calls the server to revoke the token and clears browser session data.
- Expired or invalid tokens require the user to log in again.
- The merchant Soundbox WebSocket checks the merchant token.

Sessions are stored in server memory. Restarting the server invalidates active sessions. The in-memory session approach is intended for this single-process prototype, not multi-worker production deployment.

## Resetting prototype activity

The merchant sidebar includes **Reset test data**. After confirmation, it clears activity created while testing, including:

- Current and historical prototype transactions and payments.
- Pending and paid bills.
- Offers sent and redeemed, and customer notifications.
- Newly registered test customers.
- Supplier order history and activity/event records.

The reset retains the prototype seed data required to run the app, including the original sample products, sample customers, and original sign-in accounts. Product stock and synthetic dashboard state are restored to their initial values. The reset does not delete source code or environment configuration.

## Configuration

`.env.example` contains the supported settings:

```dotenv
SARVAM_API_KEY=your_sarvam_api_key_here
SARVAM_CHAT_MODEL=sarvam-105b
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_SPEAKER=shubh
```

| Variable | Purpose |
|---|---|
| `SARVAM_API_KEY` | API key for Sarvam AI services. Optional for non-AI prototype paths. |
| `SARVAM_CHAT_MODEL` | Chat completion model name. |
| `SARVAM_TTS_MODEL` | Text-to-speech model name. |
| `SARVAM_SPEAKER` | Voice used for speech generation. |

## Project structure

```text
.
├── main.py                 # FastAPI app, APIs, business logic and authentication
├── static/
│   └── index.html          # Merchant/customer web interface
├── data/
│   ├── merchant_customer_demo.json # Legacy demo-state import/backup
│   └── supplier_orders.json # Local supplier-order prototype data
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore
├── render.yaml             # Example Render deployment configuration
└── README.md
```

The app persists its shared demo ledger in the local SQLite database `data/shopmate.db`. It stores products, customers, demo users, consent, offers, bills, payments, notifications, supplier orders, merchant state, and events, with an append-only activity log. The SQLite state is restored on startup; `merchant_customer_demo.json` remains as a legacy import/backup, and supplier-order history is also kept in `supplier_orders.json`. Keep the `data` directory writable and back up these files if you want to preserve demo activity. This is a local, single-process prototype—not a shared production database.

## API overview

The FastAPI application exposes interactive API documentation at **http://127.0.0.1:8000/docs** while the server is running.

Common route groups include:

| Route | Purpose | Access |
|---|---|---|
| `POST /api/demo/login` | Authenticate and issue a token | Public |
| `POST /api/demo/register` | Register a customer | Public |
| `GET /api/demo/me` | Validate current session / identify user | Authenticated |
| `POST /api/demo/logout` | Revoke current token | Authenticated |
| `GET /api/dashboard` | Merchant overview data | Merchant |
| `POST /api/bill` | Interpret/build a bill | Merchant |
| `GET /api/demo/catalog` | Read product catalogue | Merchant |
| `GET /api/demo/customers` | Read customer list | Merchant |
| `POST /api/demo/offers/send` | Send a ShopMate inbox offer | Merchant |
| `GET /api/demo/merchant/summary` | Merchant ledger and offer metrics | Merchant |
| `POST /api/demo/merchant/create-pending-bill` | Create a customer payment request | Merchant |
| `GET /api/demo/customer/pending-bills` | Read bills assigned to customer | Customer |
| `POST /api/demo/customer/pay` | Complete simulated payment | Customer |
| `GET /api/demo/offers` | Read customer's offers and notifications | Customer |
| `POST /api/demo/merchant/reset-data` | Reset prototype activity | Merchant |
| `GET /api/version` | Identify running build | Public |
| `GET /api/health` | Health check | Public |

For protected routes, include the token in the `Authorization` header:

```http
Authorization: Bearer <token>
```

## Troubleshooting

**The browser returns to login after five minutes**

This is expected: access tokens expire after five minutes. Sign in again.

**The browser returns to login after restarting the server**

Sessions are held in memory and are invalidated when the server process restarts. Sign in again.

**Voice features are unavailable**

Check that `.env` exists, `SARVAM_API_KEY` is valid, and the key has access/credits for the selected Sarvam models. Typed billing and non-AI dashboard functions can still be used.

**Microphone access does not work**

Use Chrome or Edge, allow microphone access for `localhost`, and check the browser's input-device selection. Localhost is treated as a secure context by modern browsers.

**Port 8000 is already in use**

Stop the other server or run `uvicorn main:app --reload --port 8001`, then open http://127.0.0.1:8001.

**A token is rejected after a code/server restart**

Log in again to receive a new token.

## Prototype limitations and security

ShopMate AI is a hackathon prototype, not a production payment or retail-management platform.

- All initial store, customer, transaction, and campaign data is synthetic.
- Customer payments are simulated confirmations; no UPI intent, payment gateway, bank transfer, or settlement is performed.
- Cashback is a local ledger calculation, not money transferred to a wallet.
- Customer notifications stay in the ShopMate interface; there is no SMS, WhatsApp, or Paytm app delivery.
- Supplier purchase orders and lifecycle updates are local simulations.
- Soundbox announcements use the browser/Sarvam speech layer; no physical Paytm Soundbox is controlled.
- Five-minute Bearer sessions are stored in process memory. Default PINs are public prototype credentials, not secure production authentication.
- The app should be deployed only for controlled demonstrations with synthetic data. Production use would require HTTPS, securely hashed credentials, a persistent/shared session store, proper database access controls, audit logging, rate limiting, and authorized payment/customer/supplier integrations.

## Acknowledgements

Built as a Paytm Build for India AI Hackathon prototype in Hyderabad. Sarvam AI powers the optional language and speech capabilities.
