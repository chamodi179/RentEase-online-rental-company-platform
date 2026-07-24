# RentEase — System Architecture (Customer Site + Admin Dashboard, Separated)

## 0. Architecture classification (used architecture)

**This is a modular monolith backend, deployed as two isolated runtime instances, behind two separate frontend apps. It is not microservices.**

| | This architecture | Microservices |
|---|---|---|
| Codebase | 1 (`apps/api`) | Many, one per service |
| Database | 1 shared MySQL | Typically 1 per service |
| Deployed processes | 2 (`api-public`, `api-admin`) — same code, different mount | Many, independently deployed |
| Communication | In-process function calls within each instance | Network calls / messaging between services |
| Failure isolation | Per-instance (public traffic can't crash admin's instance) | Per-service |
| Why this, not microservices | Booking/payment/document creation touches multiple tables in one transaction — splitting them into services would mean distributed transactions for basic writes, with no team-scaling or independent-release benefit at MVP size | Justified once a specific capability (e.g. payments) needs independent scaling, its own team, or its own release cycle |

The two-instance split (Section 4) gets you real failure isolation between customer and admin traffic — the actual goal — without taking on distributed-systems costs (service discovery, network retries, eventual consistency, distributed tracing) that microservices would require. If a specific piece (e.g. payments) ever outgrows this, the code is already namespaced by domain (`routers/public`, `routers/admin`, `services/`), so it can be peeled out into its own service later without a rewrite.

---

## 1. Why separate the two frontends

The MVP spec left the door open to running admin as "a second set of routes in the same Next.js app." For a real build, splitting them is the better call:

| Concern | Shared app | Separate apps |
|---|---|---|
| Bundle size | Customers download admin JS they'll never use | Each app ships only what it needs |
| Security blast radius | One XSS/auth bug exposes both surfaces | Admin is isolated from public traffic |
| Deploy cadence | A risky admin feature blocks a customer hotfix | Deploy independently |
| Auth model | Must awkwardly support two token types in one app | Each app has one clean auth flow |
| Team scaling | Hard to hand admin to a different dev/agency later | Clean ownership boundary |

Given RentEase already leans FastAPI + Next.js, the cleanest way to get this split without duplicating logic is a **monorepo with two Next.js apps, backed by one FastAPI codebase deployed as two isolated runtime instances** (Section 4).

---

## 2. High-level topology

```
                                       ┌─────────────────────────┐
                                       │        Stripe            │
                                       └───────────▲──────────────┘
                                                   │ webhooks
┌────────────────┐   HTTPS   ┌────────────────────┴──┐
│  Customer App    │ ───────▶ │  api-public (instance) │──┐
│  app.rentease.com│          │  same code as api-admin│  │
│  (Next.js)       │          │  mounts /public/* only │  │
└────────────────┘          └────────────────────────┘  │   SQL   ┌──────────────┐
                                                            ├──────▶│  MySQL        │
┌────────────────┐          ┌────────────────────────┐  │         └──────────────┘
│  Admin App       │ ───────▶ │  api-admin (instance)   │──┘   ┌──────────────┐
│  admin.rentease. │          │  same code as api-public│─────▶│  Redis        │
│  com (Next.js)   │          │  mounts /admin/* only   │      └──────────────┘
└────────────────┘          └───────────┬────────────┘      ┌──────────────┐
                                          │ enqueue           ──────────────▶│  MinIO/S3     │
                                          ▼                                  └──────────────┘
                                  ┌──────────────┐
                                  │ Celery worker │  (emails, receipts, thumbnails)
                                  └──────────────┘
```

**Same codebase, two isolated processes.** `api-public` and `api-admin` are literally the same FastAPI app (`apps/api`) deployed twice, each started with a different env var that controls which router group it mounts. No code duplication, no separate services to maintain — but a crash, traffic spike, or bad deploy on the customer-facing instance never touches the admin instance, because they're different processes with their own memory and their own DB connection pool. Both still talk to the one shared MySQL database — see Section 0 for why that's the right boundary to keep shared and where the process boundary is worth paying for.

---

## 3. Repository layout (monorepo, pnpm + Turborepo)

A monorepo — not two unrelated repos — because the apps share types, an API client, and UI primitives that must never drift out of sync.

```
rentease/
├── apps/
│   ├── customer/              # Next.js — public site + customer account
│   ├── admin/                 # Next.js — staff/super_admin dashboard
│   └── api/                   # FastAPI — single backend, both apps call it
├── packages/
│   ├── api-client/            # Typed fetch client, generated from OpenAPI
│   ├── ui/                    # Shared design-system components (buttons, inputs, modal)
│   └── config/                # Shared eslint/tsconfig/tailwind config
├── docker-compose.yml
├── pnpm-workspace.yaml
└── turbo.json
```

- `packages/api-client` is generated straight from FastAPI's `/openapi.json` (via `openapi-typescript` or `orval`). Both apps import from it — never hand-write fetch calls to the same endpoint twice.
- `packages/ui` holds truly generic components only (Button, Input, Card). Admin-specific components (DataTable, StatusBadge) live in `apps/admin`; customer-specific ones (ItemCard, AvailabilityCalendar) live in `apps/customer`. Don't force premature sharing of domain UI.

---

## 4. Backend: one codebase, two deployed instances

```
apps/api/
├── main.py                    # reads APP_MODE env var, mounts routers accordingly
├── core/
│   ├── config.py              # APP_MODE: "public" | "admin"
│   ├── security.py          # JWT issue/verify, password hashing
│   └── deps.py              # get_current_user, require_role()
├── routers/
│   ├── public/               # mounted only when APP_MODE=public
│   │   ├── items.py          # browse, availability search
│   │   ├── bookings.py       # create booking, my bookings
│   │   ├── auth.py           # customer login/register
│   │   └── payments.py       # Stripe checkout session
│   └── admin/                 # mounted only when APP_MODE=admin
│       ├── items.py           # CRUD inventory
│       ├── bookings.py        # list/filter, status change
│       ├── customers.py       # customer list, document review
│       ├── payments.py        # manual payment recording
│       └── staff.py           # staff account management
├── models/                    # SQLAlchemy models (shared by both instances)
├── schemas/                   # Pydantic schemas, split public/ and admin/
└── services/                  # business logic: availability check, pricing, booking state machine
```

```python
# main.py
app = FastAPI()

if settings.APP_MODE == "public":
    app.include_router(public_router, prefix="/api/v1")
elif settings.APP_MODE == "admin":
    app.include_router(admin_router, prefix="/api/v1")
```

Each running instance only ever loads *one* router group into memory — an `api-public` process has no admin routes registered at all, not even behind a permission check, so there's nothing for public traffic to accidentally hit. **Models and services are shared** (one `bookings` table, one availability-check function, imported by whichever instance needs them) but **routers and schemas are split** by audience, and now so is the running process itself. This avoids duplicating business logic while still giving each surface its own request/response contracts, permission checks, and — critically — its own failure domain.

### RBAC enforcement — three layers now, not two

1. **Process-level isolation**: the `api-public` instance has zero admin routes registered (Section 4) — this isn't a permission check, it's the absence of a route to even attack.
2. **Router-level dependency**: within `api-admin`, every route requires `require_role(["staff", "super_admin"])`. Within `api-public`, every route with side effects (create booking, cancel) requires `require_role(["customer"])`.
3. **Row-level checks in services**: e.g. a customer fetching booking detail must also own that `customer_id` — role alone isn't enough, since `require_role` doesn't know *whose* booking it is.

```python
# core/deps.py
def require_role(allowed: list[str]):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in allowed:
            raise HTTPException(403, "Forbidden")
        return user
    return checker
```

---

## 5. Auth: separate flows, same mechanism

Both apps use JWT access + refresh tokens in **httpOnly, Secure cookies** (not localStorage — avoids XSS token theft). The mechanism is identical; the *flows* differ:

| | Customer app | Admin app |
|---|---|---|
| Login endpoint | `/public/auth/login` | `/admin/auth/login` |
| Who can obtain a token | `role = customer` | `role = staff, super_admin` |
| Token cookie domain | `app.rentease.com` | `admin.rentease.com` |
| Session length | Longer (7d refresh) | Shorter (8h refresh) — admin sessions should expire faster |

Because the cookies are scoped to different subdomains, a customer session cookie is never even sent to the admin app — that's a free extra layer of isolation on top of the role check.

---

## 6. Frontend structure

### `apps/customer` (Next.js App Router)

```
app/
├── (public)/
│   ├── page.tsx                # home / browse
│   ├── items/[id]/page.tsx     # item detail + availability calendar
│   └── search/page.tsx
├── (auth)/login, register
├── (account)/                  # requires customer auth
│   ├── bookings/page.tsx       # My Bookings
│   ├── bookings/[id]/page.tsx
│   └── checkout/page.tsx       # date select → price → doc upload → Stripe
└── layout.tsx
```

- Mobile-first (per spec §6) — build with Tailwind, test at 375px width first.
- Server Components for browse/search (SEO matters for a public site); Client Components + TanStack Query for anything interactive post-login (My Bookings, checkout).

### `apps/admin` (Next.js App Router)

```
app/
├── (dashboard)/
│   ├── page.tsx                 # today's pickups/returns, active rentals
│   ├── inventory/page.tsx       # item CRUD
│   ├── bookings/page.tsx        # filterable list
│   ├── bookings/[id]/page.tsx   # detail + status change
│   ├── customers/page.tsx       # list + document review
│   ├── payments/page.tsx        # transaction list + manual entry
│   └── staff/page.tsx           # super_admin only
└── layout.tsx                   # sidebar nav, auth guard
```

- No SEO concerns → everything can be a Client Component behind auth; optimize for data density (tables, filters) over marketing polish.
- Middleware (`middleware.ts`) checks the session cookie and role on every route — redirect to admin login if missing, 403 page if role is `customer` (shouldn't happen given separate cookie domains, but defense in depth).

---

## 7. Cross-cutting concerns

- **Shared types**: `packages/api-client` types are the single source of truth. If a Pydantic schema changes, regenerate the client — TypeScript will flag every call site that breaks. This is what actually prevents customer/admin drift.
- **File uploads** (item photos, ID documents): both apps request a **presigned MinIO/S3 URL** from the API, then upload directly from the browser. The API never proxies file bytes.
- **Background jobs**: booking confirmation emails, receipt generation — enqueued to Celery from the API, processed by a worker container. Neither frontend talks to Celery directly.
- **Stripe**: customer app creates a Checkout Session via the API; Stripe webhook hits the API directly (`/public/payments/webhook`), which updates `payments`/`bookings` — never trust the frontend to confirm payment success.

---

## 8. Deployment (Docker Compose, single VM — matches MVP scope)

Both API services build from the **same Dockerfile / same `apps/api` code** — they differ only by the `APP_MODE` env var, which controls which routers get mounted (Section 4) and gives each its own connection pool size:

```yaml
services:
  api-public:
    build: ./apps/api
    environment:
      - APP_MODE=public
      - DB_POOL_SIZE=20        # sized for higher customer traffic
    env_file: .env

  api-admin:
    build: ./apps/api          # same image as api-public
    environment:
      - APP_MODE=admin
      - DB_POOL_SIZE=10        # smaller — admin traffic is low volume
    env_file: .env

  customer-web:
    build: ./apps/customer
    environment:
      - API_URL=http://api-public:8000
    depends_on: [api-public]

  admin-web:
    build: ./apps/admin
    environment:
      - API_URL=http://api-admin:8000
    depends_on: [api-admin]

  worker:
    build: ./apps/api
    command: celery -A app.worker worker

  mysql:
    image: mysql:8.0
  redis:
    image: redis:7
  minio:
    image: minio/minio
```

> **Note:** this snippet is illustrative of a production VM deploy where the database also runs in Docker. In the actual implementation (`docker-compose.yml` in the delivered project), the database runs on the host machine rather than in a container — so there's no `mysql:` service defined there at all; `api-public` and `api-admin` reach it via `host.docker.internal`. See the project's `README.md` for the real setup.

Reverse proxy (Caddy/Nginx) routes by subdomain:
- `app.rentease.com` → `customer-web:3000` → `api-public:8000`
- `admin.rentease.com` → `admin-web:3000` → `api-admin:8000`
- (no public `api.rentease.com` — each frontend only ever reaches its own backend instance, kept on the internal Docker network)

This is still "one VM, docker-compose" per your MVP tech stack decision — you're adding one extra service definition (`api-admin`), not new infrastructure. If `api-public` crashes under a traffic spike or a bad deploy, Docker restarts *that* container only; `api-admin` keeps running and staff can keep confirming bookings and recording payments uninterrupted. When you outgrow one VM, `api-public`/`customer-web` scale out independently of `api-admin`/`admin-web` — customer traffic will always dwarf admin traffic, so this is also where the split starts paying for itself on cost, not just resilience.

---

## 9. What this buys you for interviews

This split is a legitimate talking point beyond RentEase's CRUD surface: you can speak to *why* you isolated auth cookies by subdomain, *why* the API runs as two instances of one codebase instead of two separate services, and the tradeoff between a full microservices split (overkill here — see Section 0) vs. this modular-monolith-with-two-instances approach (right-sized for the MVP's actual failure-isolation need without taking on distributed-systems cost).
