# Verification report

Initial release verified on 6 November 2026. Customer-entry update verified on 7 November 2026 (Asia/Kolkata).

## Automated checks

Command: `python -m pytest tests -q --disable-warnings`

**47 tests passed** in the development verification run. Each test uses its own temporary SQLite database. Tests do not modify the bundled sample database.

Coverage includes:

- Public welcome and customer table selection without staff authentication; browsing creates no visits/orders.
- Archived/reserved table-link exclusion, private reservation-name exclusion and optional QR-only entry.
- Customer entry → join → order, with staff API access still denied; continuation only for an open session.

- Login/logout, incorrect credentials, change-password verification, CSRF and ten-attempt login limiting.
- Admin/waiter/kitchen API permissions and restricted data visibility.
- Table creation, duplicate validation, reserve/seat/resize/close/archive behaviour and QR PNG generation.
- Category create/rename/delete constraints, menu add/edit/archive, image allow-list and preserved historic prices.
- Table QR validation, reserved-table handling, multi-phone shared sessions, order idempotency and quantity validation.
- Server-side menu prices, unavailable dishes, duplicate cart-line rejection and tax rounding.
- Strict kitchen state transitions and division of kitchen/waiter duties.
- Waiter requests, active duplicate coalescing, accept/complete state transitions.
- Equal splits with remainder paise, custom split totals, wrong-share payment rejection and checkout locking.
- Failed/successful/partial payments, request replay, overpayment prevention and invalid numerical inputs.
- Two simultaneous payments from separate clients/connections: one succeeds; the other is rejected; no overcharge.
- One-time loyalty rewards, rating bounds, duplicate review rejection and daily quiz attempt limits.
- Closed sessions, fresh clean bills for the next group, and rejection of another table’s receipt.
- Settings validation, notification updates, print pages and bundled assets.
- Required schema, active SQLite foreign keys, referential integrity and compilation of all models to MySQL DDL.

Python modules compile successfully. Browser JavaScript passes `node --check`. Mac startup scripts pass `bash -n` syntax validation.

## Interactive browser verification

Checked in Chromium against a running Flask server:

- Demo admin login and rendered dashboard, actual revenue chart and floor statuses.
- Kitchen board, table detail dialog, QR image, and correct table menu link.
- Customer menu and category images; dish search and cart quantities.
- Customer joining a group and placing an order through the UI.
- Equal split into two ₹220.50 shares for a ₹441.00 demo bill.
- Simulated failure with unchanged balance, followed by a successful partial settlement.
- Saved waiter request and saved guest review.
- Daily quiz awarding 10 points and blocking another attempt in the displayed state.
- Food-pair memory-game card reveal, matched-pair state and move count.
- Responsive reflow at approximately 454 px and 340 px CSS viewport widths using normal browser zoom; measured page content width did not exceed the viewport. This is a responsive-layout check, not an iPhone/Android hardware test.

Screenshots in `screenshots/` were captured from the actual app. Desktop screenshots show full pages or the current viewport. The two narrow-layout screenshots show viewports. Some screenshots include records created during verification and may show earlier sample dish labels. The delivered database is freshly seeded and excludes the UI test guest’s transactions.

## Customer-entry update browser check — 7 November 2026

Verified the new public welcome → Customer View → Table 01 → Start dining route without signing in as staff. Added basil pesto farfalle to the cart, placed order #0025 and observed Pending status and the ₹441.00 total (₹420.00 + ₹21.00 demo tax). The same bill appeared under Bill & pay. Choose table offered Continue Table 01, which reopened the existing guest menu.

The new home and table-picker pages fit a 337 px CSS viewport without horizontal overflow; the picker was also measured at 449 px using normal browser zoom. These are browser reflow checks, not physical mobile-device tests. Actual customer screenshots 07–10 were added. This check used a separate copy of the sample database; the delivered database remains unchanged.

## Explicit limits

- No physical MacBook M2, Safari, iPhone, Android device or real LAN QR camera scan was available.
- MySQL DDL compilation was verified, but no live MySQL server/data migration was exercised.
- No real payments were attempted; this application has no payment gateway or credentials.
- No production-load, public deployment or independent penetration test was performed.
- A persistent browser-extension diagnostic was visible in the test environment; it was outside this application. No application exception was observed in the exercised workflows.

The runtime and installation verification result for the deliverable is recorded in `RELEASE_CHECK.txt`.
