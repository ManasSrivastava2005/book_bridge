# Student implementation progress

## Phase 1 — XP foundation
Extended the existing XPTransaction ledger with event_type and description. Successful student password login awards +25 once per UTC calendar day using a unique key and database ON CONFLICT protection. Invalid logins and staff logins award nothing. Contribution keys and +2 approval rewards are preserved. Authenticated /xp/history is owner-scoped and paginated; no client reward mutation endpoint exists.

Validated: 27 backend test executions including librarian auth/moderation/announcements; application TypeScript and production build passed. Additive migration applied twice, preserving all existing ledger values and counts across 35 tables. Browser login-form presence and authenticated live XP-history response verified. Live password submission was not automated; tested through isolated backend fixtures.

Reading, streak and quiz awards will be connected only to their later validated activity implementations. No historical XP is invented from old ReadingActivity demo values.

## Phase 2 — Reader levels
Added ledger-derived /xp/level, the cumulative 200 × L completion formula (50 levels), academic milestone titles, and a shared Dashboard/Profile card. Level 50 starts at 245,000 lifetime XP and completes at 255,000; lifetime XP remains uncapped while level progress caps at 100%. Old demo ReadingActivity XP/level fields no longer drive dashboard level data.
Validated: 26 backend executions including every level boundary and librarian operations; TypeScript/build passed; live Dashboard and Profile both displayed the same real zero-XP level. No schema migration needed.

## Phase 3 — Reading activity and streak
Added server-timed sessions and daily aggregates; server verifies uploaded PDF page bounds, serializes per user, allows one active session and rejects sequence gaps. Ten distinct pages with at least 30 seconds dwell each OR 900 active seconds qualifies. Replays, rapid pings, idle gaps over 45 seconds and hidden/inactive frontend heartbeats earn nothing. Reading +25/day; streak continuation +25 only when yesterday also qualified. Current/longest streak are computed from qualifying dates, while existing ReadingActivity streak fields are updated without trusting legacy XP.
27 backend executions passed, TypeScript/build passed, migration repeated preserving old table counts. Live temporary PDF tracking enabled successfully; fixture cleaned. Browser verification initially used the wrong auth storage key; corrected. Time tests use a controlled server clock rather than waiting fifteen real minutes.
Limits: uploaded managed PDFs only; browser interaction signals mitigate obvious farming but cannot prove human comprehension. UTC day boundaries. External resources remain readable without rewards.

## Phase 4 — Automatic badges
Reused Badge/UserBadge, added unique ownership index, seeded missing definitions without replacing existing IDs/ownership. Backend events and badge collection reads automatically evaluate persisted borrowing, reading streak, level and contribution criteria. No bonus badge XP. Quiz and curriculum rules are defined but await validated records in phases 8/13. Dashboard/Profile now render ownership-backed earned/locked states.
39 backend executions passed after correcting a missing due_date in a test fixture. TypeScript/build and live Profile badge display passed. Migration applied twice: definitions 5 → 30, all other counts unchanged. Reading badges use distinct borrowed titles at 1/5/10/25/50; contribution totals 1/5/20 and first approved question paper. Exact remaining thresholds are in app/services/badges.py and visible in Profile.

## Phase 5 — Leaderboard
Replaced all static leaderboard accounts with authenticated database rankings: UTC Monday-based weekly, calendar month, all time; optional real branch/semester filters; level from lifetime ledger, current streak and verified-page counts. Staff excluded. API omits user IDs/emails/academic identifiers; current student flagged. Stable tie ordering and pagination; own rank returned even outside current page.
20 backend executions and TypeScript/build passed. Live leaderboard displayed three database students and All Time filter responded 200. No schema changes.

## Phase 6 — Daily missions
Missions derive exclusively from authenticated owner/day XP event keys, not frontend state. Removed manual toggle handlers and fake starting completions; display-only accessible checkboxes refresh on focus and each minute. Reading/quiz/streak missions do not issue separate duplicate XP. Academic task mission will follow persisted planning; not fabricated now.
20 backend executions, TypeScript/build and live disabled-checkbox verification passed. No database migration.

## Phase 7 — Academic profile
Added optional AcademicProfile storage and owner-scoped APIs for institution/program/specialization, curriculum/subject selection, custom subjects and goals. Existing branch/semester remain on User. New signup no longer invents branch/semester/student ID. Four signup steps support skipping remaining academic setup; exam dates follow in phase 9. Shared academic form appears in Profile. Curriculum choices come from staff records, not a hardcoded subject list.
16 backend executions, TypeScript/build and live Profile/signup entry checks passed. Registration behavior tested through isolated API fixtures; real password entry not automated. Additive migration repeated with existing 37 table counts unchanged.

## Phase 8 — Curriculum enrollment
Added /curriculum student view from staff-owned curriculum nodes/resource mappings, subject enrollment synchronization and owner-scoped topic progress with idempotent completion. Existing completed topics survive curriculum selection changes; only selected subjects are displayed. Curriculum badges now use real selected-subject progress.
22 backend executions including librarian curriculum/announcements passed; TypeScript/build passed; migration repeated preserving old counts. Live temporary topic completion reached 100%, confirmed by fresh browser snapshot and HTTP 200 after the initial automation checkbox assertion checked too early. Fixture records removed. Verification script now clicks and waits for server-confirmed progress.

## Phase 9 — Exam dates
Added owner-scoped PostgreSQL exam CRUD for selected or custom subjects, six exam types, names and dates. Profile includes create/edit/delete controls; old/past dates remain valid records but will not be scheduled as upcoming exams.
Nine backend executions plus staff authentication regressions passed; TypeScript/build passed. Migration repeated preserving existing 39 table counts. Live temporary student created an exam through the UI; records removed.

## Phase 10 — Academic plan
Added persisted AcademicTask records and /academic-plan. Plans combine selected topics, self-reported completion, upcoming exams, mapped resources, saved reading position estimates and published topic quizzes. Unfinished work is recalculated against a user-selected daily time budget; completed tasks and dates stay intact. Overflow remains unscheduled with an explicit warning. Defaults: 120 minutes/day, 30-minute study and 15-minute quiz/revision estimates, rolling seven-day window when no exam exists. Custom subjects without structured topics get exam dates but no invented syllabus. Quiz completion connects in phase 13.
Academic mission now derives from stored task completion and grants no extra XP. Twenty-five backend executions passed, including capacity, missed-day rescheduling and ownership. TypeScript/build passed. Migration applied twice preserving all 40 prior table counts. Live temporary plan task completion reached 100%; fixture removed.

## Phase 11 — Dynamic learning path
Replaced static Python/OOP/DSA demonstration with selected curriculum subjects, units and topics ordered by nearest exam. Completed/next/upcoming states derive from saved progress; no fabricated prerequisites. Dashboard preview uses the same API. Existing completion data preserved.
13 regression executions plus three targeted path status/ownership executions passed; TypeScript/build passed. Live temporary curriculum displayed Paging fixture as the next topic; records cleaned. No schema migration.

## Phase 12 — Recommendations
Shared Dashboard/recommendations engine uses mapped curriculum relevance (40 incomplete, 20 revision), exam urgency (up to 25, tapering over 30 days), borrowed-category history (15), available copies (10), actual average rating (up to 10). Deterministic scores are labelled relevance, not probabilities. Every item explains its reasons; zero reviews/ratings remain zero. Removed fabricated recommendation accounts/books/ratings from both pages.
16 backend executions, TypeScript/build and live ten-book recommendation/explanation checks passed. No schema changes.

## Phase 13 — Chapter quizzes
Student quiz catalogue uses only active, published, permission-confirmed staff quizzes. Ten-question attempts persist an immutable question/mapping snapshot. Correct answers stay hidden until submission. Backend calculates scores, validates answers and ownership, prevents changed repeat submissions, and awards +25 XP once per UTC day. Completed attempts update plan quiz tasks and quiz badges. No copyrighted content was fetched or inferred from ISBN.
24 backend executions including staff quizzes/auth passed; TypeScript/build passed. Migration repeated preserving existing 41 table counts. Live temporary ten-question quiz scored 100%; database confirmed one attempt and 25 XP. All temporary records removed. Quiz fixture initially needed its curriculum model imports corrected before any live quiz was committed.

## Phase 14 — Student contributions
Completed private PDF/text submissions for all four contribution kinds, academic metadata, retry deduplication, owner-only file access and status tracking. Existing moderation remains authoritative; only approval grants +2 XP. Personal notes uploads remain separate and unchanged. 37 targeted executions passed during implementation; the final 263-execution regression set also passed. TypeScript/build and live pending-upload UI passed. A temporary verification cleanup initially lacked model imports; those imports were fixed and the exact temporary records removed. Both additive columns and the unique request index were checked twice without changing existing row counts.

## Phase 15 — Professional profile
Completed real reading time/pages/current and longest streak, distinct returned book titles, persisted quiz count/average, approved contributions, subject progress and XP history pagination. Existing level, badge, academic profile and exam sections remain integrated, with Academic Plan/Curriculum shortcuts. Removed sample dashboard activities/statistics, fabricated AI failure replies and fake profile ID. Academic profile changes refresh exam subject choices. Profile owner isolation/empty-state tests passed (7 executions), TypeScript/build passed, and the live profile/dashboard check passed again on 2026-09-28. No schema migration required.

Final acceptance evidence and limitations are recorded in STUDENT_COMPLETION_REPORT.md.
