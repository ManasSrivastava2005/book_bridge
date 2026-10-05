# Phase 5 — Librarian operations

ROOT CAUSE:
- The staff dashboard expected flat metrics although /admin/dashboard returns a nested metrics object. It also called nonexistent overdue/student endpoints, leaving hardcoded numbers visible after errors.
- Demand cards used fixed figures and a fabricated ML confidence statement.
- Admin analytics and seed endpoints lacked role enforcement, while staff UI routes were guarded only by login.
- PostgreSQL stores legacy timestamps without an offset in the database time zone; comparing them to aware Python datetimes could fail in recent-loan activity.
- Existing circulation APIs were not exposed in a staff workflow. Checkout/return inventory changes also needed serialization for concurrent requests.

FILES MODIFIED:
- app/routers/admin.py
- app/routers/borrows.py
- app/routers/reservations.py
- app/routers/digital_resources.py
- app/schemas/digital_resource.py
- frontend/src/pages/librarian/LibrarianDashboardPage.tsx
- frontend/src/App.tsx
- frontend/src/layouts/StudentLayout.tsx

FILES ADDED:
- frontend/src/pages/librarian/CirculationPage.tsx
- frontend/src/pages/librarian/DigitalResourceManagementPage.tsx
- test_staff_operations.py
- verify_staff_live.py
- PHASE5_REPORT.md

CHANGES:
- Real dashboard metrics, popular-book activity, inventory pressure and recent loan records with loading/error/retry states. Existing demand response fields remain for compatibility, but the UI labels these as rule-based inventory signals, not trained ML forecasts. Added demand_method=inventory_heuristic.
- Staff-only student, overdue and reservation listings; staff checkout for a selected student reuses the existing checkout logic and 14-day loan period.
- Circulation tabs for active, overdue, returned and reserved items; search, library/status filtering and 25-row display pagination.
- Explicit confirmation for physical returns, pending-reservation cancellation and held-copy release. Returned/released copies go to the oldest pending reservation, or back to inventory if nobody is waiting. Held checkout consumes the already-held copy without a second stock decrement.
- PostgreSQL row locks serialize book/queue mutations. Queue ties are resolved by ID after creation time.
- Staff digital-resource registration, metadata editing, draft/publication controls, and previews. Existing PDF URLs and external links are supported; new binary upload handling was not introduced.
- Digital-resource URL/length validation and library-reference checks. Draft metadata is visible only to staff; published metadata retains public access.
- Librarian/admin guards for admin endpoints and staff UI pages; seed additionally requires admin. No seed command was run.
- No schema migration was required for Phase 5. The Phase 4 reader table remains the only new table from this work. Existing staff-wide library scope is preserved.

TESTS:
- All 61 isolated backend tests passed, covering staff operations, reader state, Book Summarizer, and shared Notes.
- TypeScript and production build passed.
- Live browser/PostgreSQL tests passed: dashboard, issue/return, overdue view, held-copy release, pending cancellation, digital draft/publish/edit, mobile layout, student route denial, and no browser page errors.
- Two simultaneous checkouts of one available copy yielded one 201 and one 400. Two simultaneous returns of that loan yielded one 200 and one 400. PostgreSQL inventory ended at exactly one available copy.
- Verified digital metadata edits and publication state persisted in PostgreSQL.
- Live fixtures used existing accounts without modifying/deleting users. Only the verification books, loans, reservations and resource rows were removed afterwards.
- The historical test_admin_suite.py calls seed and expects unauthenticated admin access; it was not run against the working database. The new isolated suite verifies the corrected permission contract.

RESULT:
Phase 5's core librarian workflows are implemented. Sign in as librarian/admin and open Staff → Librarian Hub, Circulation, or Manage E-Books. Student borrowing, JWT auth, AI Assistant, local summarization and the completed Phase 4 reader remain available.

PENDING / LIMITATIONS:
- Demand indicators are heuristics; no demand model was trained or claimed.
- Resource management registers existing files/URLs. Secure private file delivery, new binary upload flows, and automated overdue reminders remain separate enhancements. Access/download metadata does not turn existing public upload URLs into private storage; this is explained in the staff form.
- Circulation uses the existing full-list APIs and paginates display locally. Server pagination and analytics query optimization can follow if record volume requires them.
- No new fine policy, loan renewal policy, or campus-specific staff ownership policy was invented.

Backups: backups/phase5. Completion of the reader before this phase is documented in PHASE4_REPORT.md.

## Personal Notes follow-up — 2026-09-19
Added owner-private Notes uploads and reverified all Phase 5 core workflows in the live app. Combined backend suite now passes 63 tests. Staff checkout/return, overdue, reservations, digital-resource publication/editing, concurrent inventory protection and student route denial passed again. See PERSONAL_NOTES_REPORT.md. Digital-resource upload/reminder limitations above still apply.

## Phase 5 continuation: circulation analytics — 2026-09-19

ROOT CAUSE:
The librarian hub showed only snapshot totals. It lacked reporting periods, per-library activity, daily trends and an export. Dashboard popularity calculation also ran five queries per catalog title; recent returns were ordered by their original checkout date.

FILES MODIFIED:
- app/routers/admin.py
- frontend/src/pages/librarian/LibrarianDashboardPage.tsx
- test_staff_operations.py
- PHASE5_REPORT.md

FILES ADDED:
- frontend/src/components/CirculationAnalytics.tsx
- verify_analytics_live.py

CHANGES:
- Staff-only GET /admin/analytics with validated days (1–366, default 30) and optional library_id. Uses existing loan timestamps and the database time zone; no schema changes or new dependencies.
- Daily checkouts and returns with zero-filled days, totals and distinct borrowing users. Returns count by return date, including books checked out before the reporting period. Future timestamps are excluded.
- Current overdue age groups (under 7 days, 7 to under 30, 30 or more), independently of reporting period, scoped to the selected library.
- Up to eight categories ranked by checkouts in the reporting period. Empty categories are labeled Uncategorized.
- Added analytics to the existing Librarian Hub: 7/30/90-day selector, library filter, accessible chart and exact data table, loading/error/retry/empty states, refresh, and daily CSV download containing dates and counts only.
- Labels clarify that filters affect this section and that overdue ages are a current snapshot.
- Replaced per-book dashboard count queries with independent grouped aggregates; avoids multiplying counts across reviews and loans. Eager-loaded recent activity relationships and ordered loan records by their latest checkout/return event. Existing dashboard response contract retained.

TESTS:
- 66 isolated backend tests passed across staff operations, Notes, reader state and summarization.
- New tests cover calendar boundaries, future exclusion, older loans returned in-period, exact overdue boundary classification, library isolation, zero activity, invalid inputs, JWT/staff restrictions, correct aggregate counts and fixed dashboard query count as catalog size grows.
- TypeScript check and production build passed.
- Live PostgreSQL and browser verification passed: selected-library totals, date filter, 7-row daily table, CSV download and exact downloaded bytes, 390px mobile width, no page errors.
- Existing Phase 5 browser workflows passed again: dashboard, checkout/return, overdue, reservations, digital draft/publish/edit and student route denial. Concurrent inventory checks passed.
- All live test fixtures were removed. Existing accounts and records were preserved. Backend restarted with the changes and remains running.

RESULT:
Phase 5 now includes real circulation reporting in Staff > Librarian Hub > Circulation analytics.

PENDING:
- Secure binary e-book uploads/private delivery and automated overdue reminders remain separate enhancements, as previously documented.
- Analytics reflects retained loan records and current book categories/library assignments; it is not an immutable historical audit ledger or a trained demand forecast. Day boundaries use database-local time.
- A pre-existing PostgreSQL libraries primary-key sequence mismatch was observed during fixture setup (generated ID 1 already existed). No existing rows or sequence configuration were changed. The test instead used a unique explicit temporary ID and cleaned it up. Repairing that sequence remains a separate database maintenance item.

Backups: backups/phase5-analytics.

## Remaining features follow-up — 2026-09-25
Managed PDF uploads/private delivery, in-app overdue reminders and the library ID sequence repair are now implemented and verified. See REMAINING_FEATURES_REPORT.md for behavior, tests and practical limits; its results supersede the corresponding pending items above.
