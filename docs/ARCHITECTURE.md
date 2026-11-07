# Architecture and implementation notes

## Request flow

Jinja renders the page shell and its session CSRF token. Plain JavaScript uses same-origin JSON APIs. Flask blueprints validate each mutation, enforce staff roles or table-scoped guest membership, write through SQLAlchemy, then return database-derived state. Five-second polling updates service screens. No third-party runtime service or payment API is called.

## Database relationships

- `restaurants` → `tables`, `menu_categories`.
- `tables` → `visits` (one active session enforced by the serialized write path), `orders`.
- `menu_categories` → `menu_items`.
- `visits` → `orders`, `payments`, `bill_splits`, `waiter_requests`, `reviews`.
- `customers` → `orders`, `payments`, `waiter_requests`, `reviews`, `rewards`.
- `orders` → `order_items` and an optional earned reward ledger entry.
- `menu_items` → `order_items`; each line snapshots the name and unit price.
- `bill_splits` → `payments` (optional foreign key; no-split payments are supported).
- `users` → accepted `waiter_requests`.
- `notifications` stores restaurant service activity.
- `login_attempts` stores a hash of the remote address for a 10-attempt / 10-minute login limit.

All entities have primary keys. Foreign keys are enabled explicitly on SQLite connections. Named/unique business keys prevent duplicate usernames, table numbers, QR tokens, request keys, duplicate reviews and duplicate reward awards. Check constraints protect quantities, ratings, roles, table statuses, payment amounts and order states. Guest identity is not based on an unverified email address: it is a server-signed session cookie with an opaque customer ID.

`visits` is an additional essential table: using only `table_id` for bills would mix separate groups over time. `login_attempts` is an additional security table. All fourteen requested tables are present.

## Money and concurrency

- Every monetary column stores integer paise. JSON responses use integer paise; display code formats them as INR.
- Inputs accept decimal rupee strings with up to two decimal places. The server never trusts a client total or a menu price supplied by a browser.
- Per-order tax: `(subtotal_paise * 500 + 5000) // 10000` (5% half-up).
- Bill total: sum of immutable order totals in one visit.
- Paid: sum of successful payments only. Failed records are retained.
- Equal shares use integer division and allocate the remainder one paise at a time.
- Every mutation starts a SQLite `BEGIN IMMEDIATE` transaction before reading balances or active visits. This serializes local writes and prevents simultaneous overpayment. The busy timeout is 15 seconds.
- The MySQL path acquires a restaurant row lock with `SELECT ... FOR UPDATE`. This simple one-restaurant locking strategy favours correctness for a local demo. Runtime MySQL testing remains future work.
- Order and payment submissions carry unique idempotency keys. Replaying the same key for the same customer and session returns the original result. Keys belonging to another customer/session are rejected.
- Each write route commits explicitly; remaining transactions are rolled back in `after_request`, including validation failures, so locks are released.
- Split plans freeze further ordering. A successful payment also freezes ordering. This keeps split and outstanding totals consistent.

## Authorization

| Capability | Admin | Waiter | Kitchen | Guest |
|---|---|---|---|---|
| Financial dashboard, payments, reviews | Yes | No | No | Own shared table bill only |
| Configure tables/menu/categories/settings | Yes | No | No | No |
| Seat/reserve/close table; print QR/bill | Yes | Yes | No | No |
| Pending → Preparing → Ready | Yes | No | Yes | No |
| Ready → Served | Yes | Yes | No | No |
| Accept/complete service requests | Yes | Yes | No | No |
| Place order, request assistance, pay, review | Via guest flow | Via guest flow | Via guest flow | Current joined session |

Passwords use Werkzeug scrypt hashing. Mutations require CSRF validation. Sessions are HttpOnly and SameSite=Lax; Secure cookies can be enabled with `COOKIE_SECURE=1` when actually serving HTTPS. Templates autoescape, JavaScript escapes database text before generating HTML, and CSP permits bundled scripts only. Images use an allow-listed bundled gallery; no arbitrary URL fetches or file uploads are accepted. JSON body size is limited to 64 KB.

A printed table QR is a capability link with a random 32-byte token. The app deliberately lets guests who possess that QR join the current table. This is suitable for an in-person local demo, not strong identity verification for public Internet ordering. A closed visit cannot accept orders or payments, and a guest cannot inspect a different visit simply by changing its numeric ID.

## Main API groups

- Public entry: `GET /` welcomes customers and staff; `GET /customer` lists local demo tables. Set `ENABLE_TABLE_PICKER=0` for QR-only entry. These GET routes never seat a group or create orders.
- Authentication: `POST /api/login`, `/api/logout`, `/api/password`.
- Staff state: `GET /api/staff/bootstrap`.
- Tables: `POST /api/tables`, `PATCH/DELETE /api/tables/<id>`, `POST /api/tables/<id>/close`, `GET /api/tables/<id>/qr` and `/bill`.
- Menu: `POST /api/menu`, `PUT/DELETE /api/menu/<id>`, category CRUD under `/api/categories`.
- Kitchen: `PATCH /api/orders/<id>/status`.
- Waiter: `PATCH /api/requests/<id>`.
- Settings: `PUT /api/settings`; activity acknowledgment: `POST /api/notifications/read`.
- Public menu: `GET /menu/<token>`, `GET /api/menu/<token>`.
- Guest: `POST /api/guest/join`, `GET /api/guest/state`, POST `/api/guest/orders`, `/requests`, `/splits`, `/payments`, `/reviews`, `/game`.
- Printable pages: `GET /bill/<visit_id>`, `/staff/qr-print`.
- Health: `GET /health`.

API calls that change data must include `X-CSRF-Token` from the page meta tag and the matching session cookie. An idempotency key must be 16–80 alphanumeric, hyphen or underscore characters. See test helpers for working examples.

## Customization

Change restaurant name/address/Wi-Fi/QR base URL through Admin Settings. To replace a photo without changing code, replace the matching JPEG in `static/images/` with your own properly licensed image. To add new gallery choices, add filenames to `routes/staff.py` (`IMAGES`) and the image-picker list in `static/js/staff.js`. Keep paths local and allow-listed. No user-supplied HTML is needed.

The design uses CSS variables at the beginning of `static/css/app.css` for colours. The frontend has no build step. Chart.js 4.4.8 and Lucide 0.468.0 are vendored with their licenses.

## Operating limits

One restaurant, local trusted network, small demo dataset. Orders and payment screens show all recorded data; production scale would require pagination and server-side summaries instead of repeatedly loading full history. Notifications show the latest 30, requests/reviews the latest 100, and the kitchen Served column the latest eight served orders. All active kitchen orders are displayed. No background jobs, external payment integrations or automatic refunds exist.

Guest carts are local browser storage. Bills, orders, splits, requests, reviews, points and payment records are database-backed. The memory game is purely client-side and does not award points. Reward quiz attempts and points are server-validated and stored.

For source schema changes after first installation, `create_all()` is not a migration system. Use proper migrations for retained real data. A reset of this disposable demo uses a backed-up/renamed database and fresh initialization, as explained in the README.
