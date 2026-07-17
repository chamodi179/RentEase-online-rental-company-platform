# Project Scenario: RentEase — Online Rental Company Platform

**Document type:** Client requirements brief for development team
**Prepared for:** Development Team (Backend, Frontend, DevOps, QA, Data Engineer)
**Prepared by:** Client (Business Owner / Product Owner)

---

## 1. Business Background

We run a rental company that rents out physical items to customers — think vehicles, equipment, or property (this scenario is written generically so it fits **vehicles, tools/equipment, or real estate/short-stay rentals** with minor naming changes). Today, bookings happen over phone calls and WhatsApp, which causes double-bookings, missed follow-ups, and no central record of who has what.

We need a website where:
- Customers can browse available items, check real availability, and book/pay online.
- Our staff can manage inventory, bookings, customers, and payments from one dashboard.
- Management can see reports on revenue, utilization, and overdue returns.

---

## 2. Goals

1. Stop double-bookings by showing real-time availability.
2. Let customers self-serve: browse, book, pay, and manage their own bookings.
3. Give staff a single dashboard to manage the entire rental lifecycle (booking → handover → return → settlement).
4. Give owners visibility into revenue, item performance, and overdue items.
5. Be usable on mobile, since most of our customers browse on their phones.

---

## 3. User Roles

| Role | Description |
|---|---|
| **Guest** | Anyone browsing the public site without an account. Can search/browse listings. |
| **Customer** | Registered user. Can book, pay, message support, view booking history, cancel/reschedule (within policy). |
| **Staff (Booking Agent)** | Confirms bookings, handles handover/return check-in, logs damage, resolves disputes. |
| **Inventory Manager** | Adds/edits items, sets pricing, blocks items for maintenance. |
| **Finance/Admin** | Views payments, refunds, invoices, generates financial reports. |
| **Super Admin (Owner)** | Full access: manages staff accounts, roles, settings, and all reports. |

---

## 4. Customer-Facing Website — Functional Requirements

### 4.1 Browsing & Search
- Home page with featured/popular items and promotions.
- Category/type filters (e.g., item type, location/branch, price range, capacity/size, transmission type — adapt per rental domain).
- Search bar with autocomplete.
- Availability search: customer picks a date range (and pickup/drop-off location if applicable) and only sees items free for that window.
- Item detail page: photos gallery, description, specifications, pricing breakdown (daily/weekly/monthly rate, deposit, extra fees), included add-ons, reviews/ratings, and a live availability calendar.

### 4.2 Booking Flow
1. Customer selects item + date range + optional add-ons (e.g., insurance, delivery, extra driver/equipment).
2. System shows price breakdown: base rate × duration, add-ons, taxes, deposit, discounts.
3. Customer logs in or creates an account (email/phone + password, or Google/Facebook login).
4. Customer enters pickup/drop-off details and any required verification documents (ID, driving license, etc. — upload with preview).
5. Payment: full payment or partial deposit online (card, plus support for at least one local payment gateway/mobile wallet), remainder on pickup if applicable.
6. Booking confirmation page + email/SMS confirmation with booking reference number.
7. Booking appears in customer's "My Bookings" dashboard.

### 4.3 Customer Account Area
- My Bookings: upcoming, active (currently rented), past, cancelled — with status badges.
- Booking detail: contract/agreement PDF, invoice/receipt download, item condition photos at handover and return.
- Cancel/reschedule requests, subject to cancellation policy (e.g., free before 48h, partial refund after).
- Saved payment methods (tokenized, PCI-compliant — never store raw card numbers).
- Support/contact: ticket or chat with staff, FAQ page.
- Notification preferences (email/SMS).
- Loyalty/discount code entry at checkout (optional phase 2 feature).

### 4.4 Other Public Pages
- About Us, Locations/Branches (map), Terms & Conditions, Rental Policy, Privacy Policy, Contact Us.
- Reviews/testimonials on item and company level.

---

## 5. Admin Dashboard — Functional Requirements

### 5.1 Dashboard Home
- KPI widgets: today's pickups, today's returns, active rentals, overdue returns, revenue this month, occupancy/utilization rate per item category.
- Alerts: overdue returns, low-availability items, pending payment verifications, expiring insurance/documents.

### 5.2 Inventory Management
- Add/edit/delete rental items: name, category, description, photos, specifications, branch/location, status (available, rented, maintenance, retired).
- Pricing rules: base rate, seasonal/peak pricing, weekend pricing, long-term discounts.
- Maintenance scheduling: block an item for a date range, log maintenance history/cost.
- Bulk import (CSV) for large inventories.

### 5.3 Booking Management
- Calendar view (per item and overall) showing all bookings, drag-to-reschedule (with conflict warnings).
- Booking list with filters: status, date range, branch, customer.
- Manual booking creation (for phone/walk-in customers).
- Booking detail page: full timeline (created → confirmed → handed over → returned → closed), attached documents, payment status, notes/internal comments.
- Handover checklist: condition photos, fuel/battery level, odometer or usage meter, staff sign-off, customer e-signature.
- Return checklist: condition comparison, damage flagging, late fee auto-calculation, deposit refund or deduction.

### 5.4 Customer Management (CRM-lite)
- Customer list with search, booking history, total spend, flags (e.g., blacklisted, VIP).
- Document verification queue (approve/reject uploaded ID/license).
- Communication log (emails/SMS sent, support tickets).

### 5.5 Payments & Finance
- Transaction list: payments, refunds, deposits held/released, payment gateway reference IDs.
- Manual payment recording (cash/bank transfer) for offline payments.
- Invoice generation (PDF) and export.
- Reports: revenue by period/branch/category, outstanding balances, refund summary — exportable to CSV/Excel.

### 5.6 Staff & Roles
- Staff account management, role assignment (per Section 3), branch assignment.
- Activity/audit log: who changed what and when (critical for accountability on bookings/pricing/refunds).

### 5.7 Content & Settings
- Manage homepage banners/promotions.
- Manage branches/locations, business hours, holidays.
- Manage cancellation/refund policy rules (so late-fee and refund logic is configurable, not hardcoded).
- Tax/fee configuration.
- Notification templates (email/SMS wording).

---

## 6. Non-Functional Requirements

- **Responsive design**: mobile-first, since most traffic is expected from phones.
- **Performance**: item search/availability check should return in under 1–2 seconds even with large inventories.
- **Security**: HTTPS everywhere, PCI-DSS-compliant payment handling (use a payment gateway/tokenization, never store raw card data), role-based access control on the admin side, rate limiting on auth endpoints.
- **Availability**: target 99.5%+ uptime; booking/payment flow must not go down during peak hours.
- **Auditability**: every booking status change, price override, and refund must be logged with actor and timestamp.
- **Localization-ready**: currency and date formats configurable; multi-language support is a nice-to-have for phase 2.
- **Scalability**: architecture should support adding new branches/locations and item categories without redesign.
- **Backups**: automated daily database backups with a tested restore procedure.

---

## 7. Database Design

Below is the relational schema the team should use as a starting point (works well in PostgreSQL or MySQL).

### 7.1 Entity Overview

- `users` — all people who can log in (customers, staff, admins), differentiated by `role`.
- `branches` — physical pickup/drop-off locations.
- `categories` — item categories/types.
- `items` — the actual rentable assets.
- `item_photos` — gallery images per item.
- `item_pricing_rules` — seasonal/weekday/long-term pricing overrides.
- `bookings` — the core rental transaction.
- `booking_addons` — extra services/products attached to a booking.
- `booking_status_history` — audit trail of status changes.
- `payments` — all payment/refund transactions tied to bookings.
- `documents` — uploaded ID/license/verification files.
- `handover_reports` / `return_reports` — condition check-in/check-out records.
- `reviews` — customer reviews per item/booking.
- `support_tickets` — customer support conversations.
- `audit_logs` — general admin action log.

### 7.2 Core Tables (columns)

**users**
- id (PK), full_name, email (unique), phone, password_hash, role (enum: customer, staff, inventory_manager, finance, super_admin), branch_id (FK, nullable — for staff), is_verified, is_blacklisted, created_at, updated_at

**branches**
- id (PK), name, address, city, latitude, longitude, phone, business_hours (JSON), is_active

**categories**
- id (PK), name, description, parent_category_id (nullable, for subcategories)

**items**
- id (PK), branch_id (FK), category_id (FK), name, description, specifications (JSON), base_price_daily, deposit_amount, status (enum: available, rented, maintenance, retired), created_at, updated_at

**item_photos**
- id (PK), item_id (FK), url, sort_order

**item_pricing_rules**
- id (PK), item_id (FK), rule_type (enum: seasonal, weekend, long_term_discount), start_date, end_date, price_modifier_type (fixed/percentage), value

**bookings**
- id (PK), booking_reference (unique, human-readable), customer_id (FK → users), item_id (FK), branch_pickup_id (FK), branch_dropoff_id (FK), start_datetime, end_datetime, status (enum: pending, confirmed, active, completed, cancelled, overdue), base_amount, addon_amount, tax_amount, discount_amount, deposit_amount, total_amount, created_at, updated_at

**booking_addons**
- id (PK), booking_id (FK), addon_name, price

**booking_status_history**
- id (PK), booking_id (FK), old_status, new_status, changed_by (FK → users), changed_at, note

**payments**
- id (PK), booking_id (FK), type (enum: payment, refund, deposit_hold, deposit_release), amount, method (card, cash, bank_transfer, wallet), gateway_reference, status (pending, success, failed), created_at

**documents**
- id (PK), user_id (FK), document_type (id_card, license, other), file_url, verification_status (pending, approved, rejected), reviewed_by (FK → users, nullable), created_at

**handover_reports** / **return_reports**
- id (PK), booking_id (FK), staff_id (FK → users), condition_notes, meter_reading, photos (JSON array of URLs), customer_signature_url, created_at
- return_reports additionally has: damage_flag (bool), damage_cost, late_fee

**reviews**
- id (PK), booking_id (FK), customer_id (FK), item_id (FK), rating (1–5), comment, created_at

**support_tickets**
- id (PK), customer_id (FK), subject, status (open, in_progress, closed), assigned_to (FK → users, nullable), created_at, updated_at

**audit_logs**
- id (PK), actor_id (FK → users), action, entity_type, entity_id, old_value (JSON), new_value (JSON), created_at

### 7.3 Key Relationships
- One `user` (customer) → many `bookings`.
- One `item` → many `bookings`, many `item_photos`, many `item_pricing_rules`.
- One `booking` → many `payments`, one `handover_report`, one `return_report`, many `booking_addons`.
- `branches` link to both `items` (home branch) and `bookings` (pickup/drop-off, which may differ).

### 7.4 Availability Check Logic
To check if an item is available for a date range, the query excludes any item that has a booking in status (`pending`, `confirmed`, `active`) whose `start_datetime`/`end_datetime` overlaps the requested range. This overlap check plus a maintenance-block table (or a `maintenance` status window on the item) is the core of the search feature — this should be indexed carefully (`item_id`, `start_datetime`, `end_datetime`) since it runs on every search.

---

## 8. Suggested Tech Stack (adjust to team's expertise)

- **Backend**: REST or GraphQL API — Node.js/Express, or Python/FastAPI, or Laravel — whichever the team is strongest in.
- **Database**: PostgreSQL (recommended for JSON fields + strong relational integrity) or MySQL.
- **Frontend (customer site)**: React or Next.js for SEO-friendly server rendering of item listing pages.
- **Admin dashboard**: React (SPA) with a component library (e.g., shadcn/ui, Ant Design) for fast build-out of tables/forms.
- **File storage**: S3-compatible object storage for photos/documents.
- **Payments**: Stripe or a regional gateway supporting cards + local wallets.
- **Notifications**: Email via SES/SendGrid, SMS via Twilio or local SMS gateway.
- **Hosting**: Docker containers on a cloud provider (AWS/GCP/Azure) or a managed PaaS for faster launch.
- **Background jobs**: for reminders (upcoming pickups, overdue returns, expiring documents) — a job queue (e.g., Redis + a worker) is recommended.

---

## 9. Phased Delivery Plan (suggested)

**Phase 1 — MVP (customer booking + core admin)**
- Browse/search, item detail, availability check, booking + payment, customer account.
- Admin: inventory CRUD, booking calendar, manual booking, basic payment recording.

**Phase 2 — Operations**
- Handover/return checklists with photo capture, damage/late-fee logic, deposit handling.
- Staff roles & branch assignment, audit log.

**Phase 3 — Growth**
- Reviews, loyalty/discount codes, multi-language, advanced reports/analytics, CRM features, support ticketing.

---

## 10. Open Questions for the Dev Team to Confirm

1. What rental domain exactly (vehicles / equipment / property) — this affects field naming (e.g., "odometer" vs "usage hours") and document requirements.
2. Do we need multi-branch inventory transfer (moving an item between branches)?
3. Local payment gateway requirements/compliance in our region?
4. Do we need a native mobile app in addition to the responsive website, or is mobile web sufficient for launch?
5. Expected inventory size and booking volume at launch (affects infra sizing).

---

*End of scenario document. Please review and flag any sections that need more detail before estimation/sprint planning.*
