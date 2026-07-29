# RentEase — Implementation

Full implementation of the architecture in
[`docs/RentEase_Architecture.md`](docs/RentEase_Architecture.md): one
FastAPI codebase deployed as two isolated instances (`api-public`,
`api-admin`), and two separate Next.js apps (`apps/customer`,
`apps/admin`) — all backed by your existing local MySQL database
(`localhost:3306`, user `root`, password `root`, database `rentease`,
schema already loaded).

This is **not** a tooled monorepo (no pnpm workspaces, no Turborepo, no
shared `packages/`) — see `docs/RentEase_Architecture.md` §3 for why, and
what that tradeoff means in practice. It's one Git repo holding three
independently-managed apps.

## Layout

```
rentease/
├── apps/
│   ├── api/         # FastAPI — same code, deployed twice (APP_MODE=public|admin)
│   ├── customer/    # Next.js — public site + customer account (port 3000), own package.json
│   └── admin/        # Next.js — staff/super_admin dashboard (port 3001), own package.json
├── docs/
│   ├── RentEase_Architecture.md
│   ├── RentEase_MVP_Specification.md
│   ├── 01_schema.sql ... 06_migration_2026_07.sql
│   └── ...
├── docker-compose.yml
└── README.md
```

Database: your existing local MySQL — `localhost:3306`, user `root`,
password `root`, database `rentease`, schema already loaded. Nothing here
creates or manages that database; the apps just connect to it.

## Before you start: allow MySQL to accept connections from Docker

Your MySQL is running on the host machine, not in a container, so the API
containers reach it via `host.docker.internal`. By default MySQL's `root`
user is often restricted to connections from `localhost` only, which
`host.docker.internal` doesn't count as. Check and fix if needed:

```sql
-- Run inside your existing mysql session:
SELECT user, host FROM mysql.user WHERE user = 'root';
-- If you only see 'root'@'localhost', add a host-agnostic grant for dev:
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'root';
GRANT ALL PRIVILEGES ON rentease.* TO 'root'@'%';
FLUSH PRIVILEGES;
```

Also confirm MySQL is listening on all interfaces, not just `127.0.0.1`
(check `bind-address` in `/etc/mysql/mysql.conf.d/mysqld.cnf` — comment it
out or set it to `0.0.0.0`, then `sudo systemctl restart mysql`).

## Run everything

```bash
docker compose up --build
```

This starts:

| Service | URL | Notes |
|---|---|---|
| Customer site | http://localhost:3000 | talks only to `api-public` |
| Admin dashboard | http://localhost:3001 | talks only to `api-admin` |
| Public API | http://localhost:8001/docs | Swagger UI, `/public/*` routes only |
| Admin API | http://localhost:8002/docs | Swagger UI, `/admin/*` routes only |
| MinIO console | http://localhost:9001 | minioadmin / minioadmin |
| MailDev (booking confirmation emails) | http://localhost:1080 | catches every email the `worker` sends — nothing leaves your machine |

Booking confirmation emails (spec §4.2) are sent for real over SMTP, not
just logged — the `worker` container sends them to the `mailer` (MailDev)
container, viewable at the URL above. Point `SMTP_HOST`/`SMTP_PORT`/etc at a
real provider (SES, SendGrid's SMTP relay, ...) for production; no code
change needed.

Database backups (spec §6) run automatically once a day via the `db-backup`
container — a `mysqldump` of your existing MySQL, gzipped, into the
`db_backups` Docker volume, with 7-day retention. Inspect what's there with:

```bash
docker compose exec db-backup ls -lh /backups
```

or copy the latest one out to your host:

```bash
docker compose cp db-backup:/backups/$(docker compose exec -T db-backup sh -c 'ls -t /backups | head -1') ./
```

Both `api-public` and `api-admin` connect to your existing MySQL at
`host.docker.internal:3306` — no database container is created or managed
by this compose file.

## First-time setup

If your `rentease` database only has the schema and no rows yet, seed at
least one branch, one category, one item, and one super_admin:

```sql
USE rentease;
INSERT INTO branches (name, address, city) VALUES ('Colombo Central', '123 Main St', 'Colombo');
INSERT INTO categories (name) VALUES ('Vehicles');
INSERT INTO item_catalog (category_id) VALUES (1);
INSERT INTO items (catalog_id, branch_id, name, description, base_price_daily, deposit_amount)
  VALUES (1, 1, 'Toyota Aqua 2019', 'Compact hybrid, great on fuel.', 25.00, 100.00);
```

Create your first super_admin directly (the `/admin/staff` endpoint requires
an existing super_admin, so the very first one has to be seeded):

```bash
docker compose exec api-admin python3 -c "
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.models import User
db = SessionLocal()
db.add(User(full_name='Admin', email='admin@rentease.local',
            password_hash=hash_password('changeme123'), role='super_admin', is_verified=True))
db.commit()
"
```

## Local frontend dev (without Docker)

```bash
cd apps/customer && npm install && npm run dev   # http://localhost:3000
cd apps/admin && npm install && npm run dev       # http://localhost:3001
```

Copy `.env.local.example` to `.env.local` in each app first.

## Backend dev (without Docker)

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # already points at localhost:3306, root/root, db=rentease
APP_MODE=public uvicorn app.main:app --reload --port 8001
# in a second terminal:
APP_MODE=admin uvicorn app.main:app --reload --port 8002
```

Running the API directly on your host (not in Docker) is actually simpler
here, since it talks to `localhost:3306` directly with no
`host.docker.internal` networking to worry about.

## What's implemented vs. stubbed

Implemented against the real schema: auth (customer + staff/super_admin,
separate cookie scopes, account lockout after repeated failed logins,
server-side password policy), browse/search/availability check, price
quoting, booking creation with the no-double-booking guard, booking status
state machine + history logging, full admin CRUD for
inventory/bookings/customers/payments/staff, and the dashboard summary.

**Registration** — `POST /auth/register` (customer) and `POST /staff`
(super_admin-only staff/super_admin creation) both validate the password
server-side (`validate_password_strength()` in `core/security.py`: 8+
characters, at least one letter and one digit, common passwords rejected)
regardless of what the frontend already checked client-side.

**Account lockout** — both `/auth/login` endpoints (customer and
staff/admin) track `failed_login_attempts` per account. After 5 wrong
passwords in a row the account is locked for 15 minutes
(`MAX_LOGIN_ATTEMPTS` / `LOCKOUT_MINUTES` in `config.py`) — the correct
password won't work either until the lock expires. Any successful login
resets the counter. If you're upgrading an existing database rather than
starting from a fresh `01_schema.sql`, run `docs/06_migration_2026_07.sql`
first to add the required columns.

**Payments** — real Stripe Checkout integration (`payments.py`): if
`STRIPE_SECRET_KEY` in `.env` is a real key, `/payments/checkout/{id}`
creates an actual `stripe.checkout.Session` and the customer is redirected
to real Stripe. Locally, `.env.example` ships with a placeholder key, so
the same endpoint instead returns a link to an in-app **mock checkout page**
(`/mock-checkout/[sessionId]` in the customer app) that simulates a
successful card payment — this is how you pay for a booking end-to-end
without needing a Stripe account. Swap in a real key and the mock path is
never used; nothing else changes. Checkout no longer includes an ID/document
upload step — it's just review → pay.

**Manual payments** — recording a manual (cash/bank-transfer) payment or
refund from the admin Payments screen (`POST /admin/payments`) is
restricted to `super_admin`. Regular `staff` accounts can still view the
full payments ledger (`GET /admin/payments`); the "Record manual payment"
form itself is only rendered for a signed-in `super_admin` and the API
enforces the same restriction independently, so this can't be bypassed by
calling the API directly.

**Cancellations & refunds** — cancelling a `pending`/`confirmed` booking
is always allowed; it's the *refund* that's policy-gated
(`CANCELLATION_FREE_HOURS`, default 48, in `config.py`): full refund if
cancelled that far out from pickup, no refund if closer in. Refunds are
recorded `pending` first, then `issue_refund()` attempts a real
`stripe.Refund.create(...)` when Stripe is configured, or leaves it
`pending` for manual reconciliation via the admin Payments screen
otherwise — the same as a cash/bank-transfer refund would be handled. Staff
cancellations (admin dashboard) skip this policy entirely by design; refunds
there are still manual (Phase 2: "Refund workflow automation").

**Booking confirmation emails** are sent for real over SMTP by the
`worker` container (`worker.py`), not just logged — see the Docker section
above.

Nothing in the current codebase is a placeholder/stub — the two things
that used to be (a document-upload feature that never proxied real files,
and an email task that only printed) have either been removed entirely
(document upload — see below) or replaced with a real implementation
(email, over SMTP).

### Removed: ID/document submission workflow

An earlier version of this project required customers to upload a
photo of an ID document as a blocking step in checkout, with a
corresponding admin screen to approve/reject uploads. That workflow has
been removed in full:

- No `documents` table, model, schemas, or API routes (`/documents/*`,
  `/customers/documents/*`) — running `docs/01_schema.sql` fresh no longer
  creates a `documents` table at all; `docs/06_migration_2026_07.sql`
  drops it on an existing database.
- Checkout is now just **Review → Pay** — no upload step in between.
- The admin Customers screen is a plain list + search; there's no
  pending-document-review section.

Item-catalog **photo** uploads (a completely separate feature, used by
staff in the admin Catalog screen) are unaffected — they still use the
same presigned-MinIO-URL pattern.

## Paying for and cancelling a booking (local dev)

With the default placeholder `STRIPE_SECRET_KEY`:

1. Book an item as a customer through the normal checkout flow — you'll be
   redirected to `/mock-checkout/...` instead of real Stripe.
2. Click **Simulate successful payment**. This hits
   `/payments/mock-complete/{booking_id}`, which records a successful
   payment and moves the booking to `confirmed` (same state-machine path
   the real Stripe webhook uses, so it shows up in
   `booking_status_history` either way).
3. From `/account/bookings/{id}`, **Cancel booking** works at any point —
   the page tells you upfront whether you're inside or outside the 48h
   free-cancellation window, and the confirmation message reflects the
   real outcome (`refunded`, `pending`, or `failed`).

Set a real `STRIPE_SECRET_KEY` (and `STRIPE_WEBHOOK_SECRET` for the
`/payments/webhook` endpoint) to switch both flows over to live Stripe
without touching the frontend.