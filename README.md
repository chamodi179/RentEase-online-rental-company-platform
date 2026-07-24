# RentEase — Implementation

Full implementation of the architecture in `RentEase_Architecture.md`: one
FastAPI codebase deployed as two isolated instances (`api-public`,
`api-admin`), and two separate Next.js apps (`apps/customer`,
`apps/admin`) — all backed by your existing local MySQL database
(`localhost:3306`, user `root`, password `root`, database `rentease`,
schema already loaded).

## Layout

```
rentease/
├── apps/
│   ├── api/         # FastAPI — same code, deployed twice (APP_MODE=public|admin)
│   ├── customer/    # Next.js — public site + customer account (port 3000)
│   └── admin/        # Next.js — staff/super_admin dashboard (port 3001)
├── docker-compose.yml
└── RentEase_Architecture.md
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
separate cookie scopes), browse/search/availability check, price quoting,
booking creation with the no-double-booking guard, booking status state
machine + history logging, document upload records, manual + Stripe-stub
payments, full admin CRUD for inventory/bookings/customers/payments/staff,
and the dashboard summary.

Stubbed for MVP (clearly marked in code comments — swap for the real
integration when you're ready): Stripe Checkout session creation (`payments.py`
returns a fake URL instead of calling the Stripe SDK), MinIO presigned URLs
(`documents.py` returns a placeholder instead of calling boto3), and the
email task in `worker.py` (prints instead of calling SES/SendGrid).
