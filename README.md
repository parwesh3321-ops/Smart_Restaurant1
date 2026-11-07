# Smart Restaurant Management & Digital Dining System

A complete local Flask + SQLite application with a restaurant workspace and a mobile-friendly digital menu. The sample restaurant is **Ember & Olive**. Frontend: HTML5, CSS3 and plain JavaScript. Backend: Python Flask. Data: SQLAlchemy and SQLite. QR codes: Python `qrcode`. Charts: locally bundled Chart.js. Icons: locally bundled Lucide.

**Start here:** follow the steps below in order. You do not need Node.js, npm, MySQL, a cloud account or any paid API. Internet is needed to install Python packages the first time. Food images, icons and charts are included and work offline afterwards.

The reference Instagram video was not present in the request, so this project uses an original restaurant design. No reference branding or logo was copied.

## 1. What is in the ZIP?

The archive contains one folder named `Smart_Restaurant`. It includes all source code, the demo SQLite database, the database initialization script, sample data, printable QR codes, tests and screenshots. The database is intentionally preloaded so there is something to explore immediately. Initialization is safe to run again; it preserves existing data.

## 2. Install the two things you need on your MacBook M2

1. Install **Visual Studio Code for macOS** from https://code.visualstudio.com/download. Choose Apple silicon or Universal. Drag Visual Studio Code into Applications and open it.
2. Install **Python 3.12 or 3.13 for macOS** from https://www.python.org/downloads/macos/. The macOS universal2 installer supports Apple silicon. Run the downloaded installer and finish the installation.
3. If Python installation creates an **Install Certificates.command** file in its Applications folder, run it if package installation later reports a certificate error.

The code uses Python 3.10 or newer. It was tested on Python 3.12 on Linux; a physical MacBook M2, Safari and an actual phone were not available for testing. The project uses portable packages and no Intel-only binaries.

## 3. Extract and open the project

1. Download `Smart_Restaurant_Project.zip`.
2. In Finder, open Downloads and double-click the ZIP to extract it.
3. You should see a folder named `Smart_Restaurant`.
4. Open VS Code.
5. Click **File → Open Folder…** and choose that `Smart_Restaurant` folder.
6. You should see `app.py`, `requirements.txt` and this `README.md` in the left sidebar. If you see only another folder, open that inner folder instead.
7. In VS Code, click **Terminal → New Terminal**. A panel opens at the bottom. This is where you type the commands below.

Commands are typed into the terminal, not into `app.py`. Press Return after each command. Do not type the `$` symbol or the triple backticks shown around examples.

## 4. Set up Python for this project — first time only

Check Python:

```bash
python3 --version
```

You should see `Python 3.12.x` or `Python 3.13.x`. If it says `command not found`, install Python first and reopen VS Code.

Create a private dependency folder for this project:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Your terminal prompt should now begin with `(.venv)`.

Install the dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Wait until installation finishes. Do not close the terminal while it is downloading packages.

Initialize the database:

```bash
python init_db.py
```

You will see either “Database created with demo accounts and sample data” or “Database already initialized. Your data was preserved.” Both mean it worked.

In VS Code you can also select the project interpreter: **Command + Shift + P → Python: Select Interpreter → .venv**. If that command is missing, install the official **Python** extension from Microsoft in VS Code. The terminal commands work without the extension.

## 5. Run the restaurant

In the same terminal:

```bash
python app.py
```

Keep that terminal open. Open Safari or Chrome and type:

```text
http://127.0.0.1:5001
```

Use `http`, not `https`. The site is running on your own Mac. Port **5001** avoids the common macOS AirPlay conflict on port 5000.

The welcome page has two clear entrances:

- **Customer View** → choose **Table 01** → browse the menu → **Start dining**. Customers do not need a staff username or password. You can also open `http://127.0.0.1:5001/customer` directly.
- **Staff Login** → use a demo account below to manage the restaurant. The staff dashboard also has a **Customer View** shortcut.

If you are replacing an older copy, extract this ZIP into a new folder and stop the old server before running the new one. To keep your earlier records, copy only your old `database/restaurant.db` into the new folder before starting; do not run a reset. Reprint QR codes from the app if your database was replaced.

To stop the app: click the terminal and press **Control + C**.

To start it on another day, open the folder in VS Code, open a terminal, and run:

```bash
source .venv/bin/activate
python app.py
```

Optional helpers are included:

```bash
bash SETUP_MAC.command
bash START_MAC.command
```

`SETUP_MAC.command` creates the environment, installs dependencies and initializes the database. `START_MAC.command` starts the local app after setup. Running the commands in Terminal avoids macOS blocking downloaded `.command` files.

## 6. Demo accounts

| Role | Username | Password | Access |
|---|---|---|---|
| Admin | `admin` | `Admin@12345` | Dashboard, tables, orders, kitchen, waiter requests, menu, payments, reviews and settings |
| Waiter | `waiter` | `Waiter@12345` | Tables, table bills/QRs, orders ready to serve and waiter requests |
| Kitchen | `kitchen` | `Kitchen@12345` | Kitchen board; advance pending orders to preparing, then ready |

On the login page, click **Admin**, **Waiter** or **Kitchen** to fill that role’s demo credentials, then click **Sign in**. Sign out using the button at the bottom of the sidebar. Change your current account’s password through the profile button or Admin Settings.

The demo credentials are intentionally public. This is a local educational project, not an Internet-facing production deployment.

## 7. First demonstration — complete restaurant workflow

Use a normal browser window for staff. Use a private/incognito window, a different browser, or a phone for the customer. Browser tabs share a login cookie; separate windows in the same normal profile do not create different guest identities.

### A. Explore the dashboard

1. Log in as `admin`.
2. The Overview shows today’s collected demo payments, order count, occupied/available tables, a live floor map, a revenue chart and popular dishes.
3. Six tables start available, four occupied, and two reserved. Historical sample orders provide chart data.
4. Revenue counts **successful payments**, not unpaid orders. Financial dates use Asia/Kolkata; order timestamps are stored in UTC and displayed in the browser’s local time.

### B. Manage tables

1. Open **Live floor map → Add table**.
2. Enter an unused table number, 1–20 seats, and a zone. Save it.
3. Select any table to edit its number, seats or zone; set a reservation; seat a group; view the bill; open the menu; or download its QR.
4. For a reservation, choose `reserved` and enter the reservation name. To seat that party, change to `occupied` and enter the group size.
5. Customer count means the number of people in the seated group, not the number of phones. A second phone joins the existing group without changing the count.
6. You can archive an available table with no active session. Historical records are kept.
7. To free an occupied table, all its orders must be **Served** and its balance must be **₹0**. Click **Close dining session**. Empty sessions can also be closed.

### C. Manage categories and dishes

1. Open **Menu management**.
2. Use **Categories** to add or rename a category. Only categories with no current or historical items can be deleted, preserving history.
3. Choose **Add dish**, enter its name, description, category and price, and select a bundled food image.
4. Toggle vegetarian/availability flags as needed. An unavailable dish stays visible to guests but cannot be added to an order.
5. Choose **Edit dish** to change it, or **Archive dish** to remove it from the customer menu.
6. Past orders retain the names and prices captured when ordered. Current menu price changes do not change existing bills.
7. Food images are illustrative sample photographs. To use your own images, see `docs/ARCHITECTURE.md`.

### D. Open a customer menu and place an order

1. Open `http://127.0.0.1:5001` and click **Customer View**. No admin login is required. You can also use the **Customer View** link on the login page.
2. Choose **Table 01 → View menu**. An occupied table says **Join your group**; select it only if you belong to that dining group. Reserved tables ask you to speak to staff.
3. Click **Start dining**, enter your name and group size, then join. If you start by adding food instead, the cart will ask you to join before checkout.
4. Browse categories or search dishes, then click **Add**. Use +/− to change quantities.
5. Click **View your cart**. The cart shows subtotal, demo tax and total.
6. Add an optional preparation note and click **Place order**.
7. The customer’s **My table** tab shows the order and its progress. The table is occupied and the staff kitchen board receives the order.
8. Open **Bill & pay** for splitting and demo payment, or **Little extras** for Wi-Fi, points, games and feedback.
9. Use **Choose table** to return to the table picker. Your current open dining session has a **Continue Table** shortcut. Selecting a different menu does not change your session until you explicitly join that table.

Printed QR codes still open the correct menu directly. Staff can also select a table on the floor map and click **Open digital menu**. Multiple phones joining the same table share its current bill and orders, with their own guest names and reward ledgers. Use an incognito window or another device when demonstrating customer and staff together.

The table picker is enabled for this local demonstration. To restrict entry to the printed QR links, copy `.env.example` to `.env`, set `ENABLE_TABLE_PICKER=0`, and restart the server. The `/customer` page will then explain QR scanning without listing tables or tokens. Possession of a table link is still the guest access mechanism; this is not a public reservation service.

### E. Kitchen and waiter

1. Sign in as `kitchen` in another browser/profile, or use the admin’s **Kitchen display**.
2. Click **Start preparing**, then **Mark ready**.
3. Sign in as `waiter`, open **Orders**, and click **Mark served** for the ready order. Admin can also perform each step.
4. Staff cannot skip steps. Kitchen staff cannot mark an order served. Waiters cannot start kitchen preparation.
5. On the customer screen click the bell / **Call waiter**, choose service, water or bill assistance, and submit.
6. In the staff **Waiter requests** page, click **Accept request**, then **Complete**. Repeat active requests of the same type are merged.
7. Live screens poll the server every five seconds. Forms are not overwritten while being edited.

### F. Split a bill and simulate payment

1. In the customer view open **Bill & pay**.
2. Choose **Split equally** and enter 2–20 people. Extra paise are distributed one at a time so shares add up exactly.
3. Or choose **Custom shares** and enter each person’s name and rupee amount. All shares must add up to the full bill, including tax.
4. Click **Pay share**. You can pay that share in full or enter a smaller positive amount. Without a split, use **Continue to demo payment** and choose any amount up to the remaining table balance.
5. Choose **Payment fails** and submit to see a failed transaction. The amount is recorded but the balance does not decrease.
6. Retry by opening a new payment and choose **Payment succeeds**. The balance decreases only once, even if the same request is accidentally repeated.
7. Complete the remaining shares. The balance reaches zero. Customers earn points for their own orders when the full table bill is paid.
8. Click **Final bill → Print / Save PDF**. In the Mac print dialog, use the PDF option to save a copy.
9. Staff marks all food served and closes the session. A new group starts a fresh bill.

**Billing rules:** all money is integer paise, quantities are 1–50 per line, tax is an illustrative fixed 5% rounded half-up per order, and there are no real card/UPI/bank fields. New orders are blocked once a split exists or a successful payment has begun. Finish the current dining session before ordering again. Shares can be replaced only before any successful payment or any payment attempt against a share. Failed attempts against a share keep that split plan fixed so its ledger remains traceable.

### G. Wi-Fi, loyalty, games and reviews

1. Open **Little extras**.
2. View/copy the demo Wi-Fi details. Change these in Admin Settings; they do not configure a real router.
3. Loyalty: each order earns `floor(order total in rupees / 100)` points once the whole table bill is paid. Points are credited to the person who placed the order, even if another person pays.
4. **Daily foodie quiz:** one attempt per guest per Asia/Kolkata day; requires an order in an open session. A correct answer earns 10 points. The server records even a wrong attempt to prevent repeated tries.
5. **Food pairs:** a six-pair memory game. Match cards while waiting. It has no cash value and grants no loyalty points.
6. Rate food and service from 1–5 stars and leave feedback. One review per guest per dining session; an order must exist first. Reviews appear in Admin → Guest reviews.
7. Guest identities are stored in the signed session cookie, with a 12-hour rolling session. Clearing cookies, using another device or signing in/out as staff can lose access to that guest profile; the database retains its points. There is no cross-device customer account or recovery flow in this demo.

## 8. Scan the QR from your phone

`127.0.0.1` on a phone refers to the phone, not your Mac. Use the Mac’s local Wi-Fi address instead.

1. Connect both Mac and phone to the **same private Wi-Fi network**. Guest Wi-Fi with device isolation may prevent connections.
2. On the Mac, find the IP in **System Settings → Wi-Fi → Details → TCP/IP**. Example: `192.168.1.20`. The actual address will be different.
3. Stop the running app with **Control + C**.
4. In the activated VS Code terminal run:

```bash
HOST=0.0.0.0 python app.py
```

5. On the Mac, open `http://127.0.0.1:5001`, log in as admin and go to **Settings**.
6. Set **QR base URL** to your actual Mac address and port, for example `http://192.168.1.20:5001`. Click Save.
7. Open **Live floor map → Print QR cards**, or select a table and **Download QR**.
8. Scan the newly generated code using your phone camera. It opens the correct table menu.
9. If macOS asks whether Python may accept incoming connections, allow it for this trusted local demo.
10. If your Mac’s Wi-Fi IP changes, update the setting and print new QR codes.

You can also export all current PNGs with:

```bash
python generate_qr.py
```

Files are saved in `qr_codes/`. The bundled initial PNGs use `http://127.0.0.1:5001`; regenerate them for phone scanning. Generated QR tokens are unique per table. Possession of a table QR allows joining that table’s current dining session: treat printed codes as local table access links.

## 9. Run the tests

Stop the server if you wish (tests use separate temporary databases). Activate `.venv`, then:

```bash
python -m pytest tests -q
```

The suite checks public customer entry without staff login, read-only table browsing, QR-only mode, current-session continuation, login/logout, passwords, CSRF, role boundaries, tables, categories, menu CRUD, QR PNGs, customer ordering, duplicate requests, kitchen transitions, waiter lifecycle, equal/custom splits, invalid money, successful/failed payments, concurrency, reviews, rewards, table closure, bill isolation and database foreign keys.

The tests do **not** alter your restaurant database. See `docs/TEST_REPORT.md` for the executed results and browser verification scope.

## 10. Troubleshooting

| What you see | What to do |
|---|---|
| `python: command not found` | Run `source .venv/bin/activate`. Use `python3` for initial environment creation. |
| `No module named flask` | Activate `.venv`, then run `python -m pip install -r requirements.txt`. |
| `requirements.txt` not found | Open the folder containing `app.py` in VS Code. Run `pwd` and `ls` to see your current folder. |
| `no such table` / database unavailable | Run `python init_db.py` in the activated environment, then restart the app. |
| Browser says connection refused | Start `python app.py`, keep the terminal open, and use port 5001. |
| Address already in use | Stop the old running server, or run `PORT=5002 python app.py` and use `http://127.0.0.1:5002`. Update the QR base URL too. |
| Phone cannot connect | Check same Wi-Fi, actual Mac IP, port 5001, `HOST=0.0.0.0`, firewall and guest-network isolation. |
| Session changed / CSRF message | Refresh the affected tab. Sign-in/out changes session credentials; use separate browsers/profiles for simultaneous roles. |
| Cannot mark a table available | Complete payment, serve every order, then use **Close dining session**. |
| Cannot place an order after splitting | That bill is in checkout. Finish it, let staff close the session, then join a new session. |
| A category cannot be deleted | It contains current or archived items. Rename it or leave it for history. |
| A price appears different in an older bill | Orders retain their original price. This is intentional. |
| Images or JS seem outdated after changing source | Hard-refresh the browser with Command + Shift + R. |
| `externally-managed-environment` | Do not use system-wide pip. Create and activate `.venv` first. |

## 11. Data, backup and reset

The database is `database/restaurant.db`. Stop the app before backing it up. Copy the file somewhere safe. A local random signing key is generated at `database/.secret_key`; keep it private and do not upload it. Changing/deleting the key signs every session out.

`python init_db.py` is non-destructive. To start over, **stop the app, back up the database, rename `database/restaurant.db` to a backup name**, then run `python init_db.py` and `python generate_qr.py`. This creates a new demo database and new QR tokens. The previous database remains in your backup file.

## 12. Folder guide

| File/folder | Purpose |
|---|---|
| `app.py` | App factory, request protection, error handling and local server |
| `config.py` | Configuration and environment variables |
| `database.py` | SQLAlchemy instance and SQLite foreign-key setup |
| `models/` | All database models and relationships |
| `routes/public.py` | Welcome page, customer table picker and current-session continuation |
| `routes/auth.py` | Login/logout and password changes |
| `routes/staff.py` | Staff dashboard, table/menu management and operations |
| `routes/customer.py` | Table joining, ordering, payments, rewards and feedback |
| `routes/common.py` | Validation, permissions and bill serializers |
| `templates/` | Jinja HTML pages, printable bills and QR cards |
| `static/css/`, `static/js/` | Responsive design and frontend behaviour |
| `static/images/` | Bundled food photography and favicon |
| `static/vendor/` | Chart.js, Lucide and license notices |
| `seed.py` | Sample menu, users, tables, historical and active orders |
| `init_db.py` | Non-destructive database setup |
| `generate_qr.py` | Export all active table QR PNGs |
| `database/schema.sql` | Readable SQLite schema reference; initialize through Python |
| `tests/` | Isolated automated tests |
| `docs/` | Architecture, test results and image credits |
| `screenshots/` | Screenshots taken from the running app |

## 13. MySQL readiness and scope

SQLAlchemy provides portable models and queries; all money remains integer paise. To try a **new empty MySQL database**, install `pymysql`, create a database using InnoDB and utf8mb4, copy `.env.example` to `.env`, and set `DATABASE_URL=mysql+pymysql://user:password@localhost/smart_restaurant?charset=utf8mb4`. Run `python init_db.py` to create and seed it. Use a least-privilege account. URL-encode special password characters.

This does not transfer existing SQLite records. A real data migration requires a backup, ETL/import, schema migrations (for example Alembic), row-count/financial reconciliation and MySQL integration testing. MySQL was not available for runtime testing; SQL schema compilation is checked separately.

This project intentionally provides local educational operation, five-second polling, a single restaurant, simple manual reservations, demo payments and a lightweight loyalty ledger. It has no real gateway, public hosting, customer account recovery, refunds, scheduled booking calendar, inventory purchasing or production deployment setup. For public production use add HTTPS, a production WSGI server, operational backups, audit/monitoring, migrations, stronger guest enrollment and a real reviewed payment integration. Do not expose Flask’s development server directly to the Internet.

## References and bundled licenses

- Flask: https://flask.palletsprojects.com/en/stable/quickstart/
- SQLAlchemy SQLite behaviour: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
- Chart.js (MIT): `static/vendor/chart.LICENSE.md`
- Lucide (ISC): `static/vendor/lucide.LICENSE`
- Photography sources and license: `docs/IMAGE_CREDITS.md`

Original application code is MIT-licensed; see `LICENSE`. Third-party assets retain their own licenses.
