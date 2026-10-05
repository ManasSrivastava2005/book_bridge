# Book Bridge V2 — Inspection and approval plan

Date: 2026-09-30
Status: inspection complete; implementation NOT started. Approval required before code/schema/data changes.

## Inspection scope and evidence

Reviewed application routes, role guards, staff/student layouts, resource schemas/storage, circulation/reservations/reviews, moderation, academic models, planning/recommendations, existing test inventory and prior completion reports. Queried PostgreSQL inside a read-only transaction. Did not import app.main during inspection because it calls create_all. Did not run seed scripts, migrations, publish actions or tests against working data. This planning document is the only new artifact.

Working database: bookbridge_v2. Current counts: 42 tables, 5 users, 10 books, 8 borrow records, 5 digital resources, 0 reservations, 0 contributions, 1 academic profile, 0 curricula/nodes, 3 XP transactions and 0 reader states. These are an inspection snapshot, not a baseline to overwrite future activity.

### Confirmed findings

1. Draft publishing already has a UI action and PUT /admin/digital-resources/{id}. Uploads commit records and managed files use authenticated serving. The one current draft (ID 5) is an external open_access entry and passes DigitalResourceCreate validation with is_published=true. No publish mutation was attempted. Its reported failure is NOT yet reproduced, so no definitive root cause is claimed. Reproduce in an isolated fixture first; capture the actual HTTP response and persisted status.
2. Digital resources have only is_published, no archived lifecycle. License defaults are permissive; explicit distribution evidence is not required. Staff UI lacks cover upload and complete lifecycle controls. Managed PDFs protect drafts, but legacy /uploads URLs are served statically and third-party URLs cannot be revoked by a database flag.
3. The student digital page reads stored resources rather than visibly performing a live multi-provider merge. Three published rows are open_access entries. Curation must address the stored catalogue and its readers/search surfaces, not just remove a frontend fetch.
4. Contribution upload/private preview/approval/publication/audit/notification/+2 XP/badges already exist. Rejection reason is optional, and the moderation list has status tabs but no resource-kind filter. Essential upload/status UI currently lives in a separate Contributions page.
5. Staff navigation links to student Notes, Question Banks, Settings and Student workspace. Curriculum and generic Users remain visible. A separate staff profile does not exist. There is no duplicate Dashboard item within the current Content group; preserve the actual main dashboard while cleaning the real links.
6. Student routes use ProtectedRoute without allowedRoles. Staff APIs have role checks, but academic/exam/plan APIs generally accept any authenticated role. Staff can enter student workflows. Shared JWT storage/credentials should remain; roles must be separated at route and API boundaries, with deliberate shared exceptions such as staff PDF preview.
7. POST /borrows/ permits any authenticated account to issue a book to itself. POST /borrows/{id}/return permits the borrower to record a physical return. Staff checkout delegates directly to the same handler with the student as current_user. Changing only that handler's dependency would not be sufficient: extract a shared circulation service with explicit actor and borrower.
8. Staff checkout selects from bulk-loaded dropdowns; it has no due-date field or selected-student detail panel. Server checkout validates copies and duplicate active loans, but does not implement the requested selected-library/membership checks.
9. Reservations use pending/fulfilled/cancelled, where fulfilled actually means held for pickup. A return can create a hold; checkout deletes the reservation. This conflicts with fulfilled-history retention. Preserve records and separate ready-for-pickup from completed checkout. Existing reservation policy only allows requests when no copies are available; retain that policy unless separately changed.
10. Review creation/update checks that the book exists but does not check a qualifying BorrowRecord or student role.
11. AcademicProfile is already owner-linked, with optional fields/custom subjects. Curriculum has no owner; nodes support subject/unit/topic only. Structured topics currently require staff curricula. No private syllabus upload, proposal review or student curriculum authoring exists. Public /academic/catalog must be scoped before adding private curricula.
12. Recommendations, learning paths, plans, topic progress, quizzes and badges already work with curriculum IDs/mappings. Extend these services instead of creating a second academic system. Custom-subject text alone currently supplies no structured plan or mapped-book relevance.

## Safety and architecture decisions

- Keep current React/FastAPI/PostgreSQL/JWT and local AI implementation.
- Before any migration: create a new timestamped pg_dump backup and archives of uploads AND private_uploads; validate archive contents and restore the database backup to a disposable database. Do not reuse an old backup as proof of current recoverability. Never log credentials.
- Record fresh counts/relationships immediately before each migration. Test additive, versioned migrations twice against an isolated PostgreSQL database, then compare working data afterward. No destructive reset or history deletion.
- Reuse existing User, AcademicProfile, BorrowRecord, Reservation, Contribution, XPTransaction, Curriculum and topic/task models.
- Proposed migrations below are names/designs, not existing files or completed changes. New required fields need backward-compatible defaults/nullability and explicit legacy handling.
- Keep API URLs where possible. Document intended permission changes: student self-issue/return and unverified review requests will become forbidden. Add staff/owner endpoints instead of duplicating business logic.
- Preserve physical inventory accounting: a pending request is not a loan and does not consume stock; a ready hold may reserve a copy separately from a loan. Checkout consumes the held copy exactly once. Cancellation releases it exactly once.
- Legacy fulfilled reservations must be treated as ready holds under the old convention, not completed loans. Current working count is zero, but migration fixtures must include all legacy statuses and preserve held-stock accounting.
- Existing third-party resource records/files will be retained. Resources without staff provenance/legal-basis confirmation will be excluded from the curated student collection pending staff review. Locally hosted legacy files need authenticated serving and reference-preserving migration; externally hosted URLs cannot be made private by Book Bridge.
- Personal curricula: add nullable owner_user_id and private/legacy visibility to existing Curriculum. Keep old curriculum IDs/progress/history. Student edits must retain stable node IDs for unchanged topics; archive removed referenced nodes instead of deleting their progress, exams or completed tasks.

## Stage B — Librarian first

All paths below are relative to C:\Backend\bookbbbb. Each phase ends with relevant backend tests, TypeScript validation, production build and a focused UI workflow check. New tests use isolated fixtures. No Stage C implementation before B8 passes.

### B1. Staff authentication and separate profile

Files: app/dependencies.py; app/routers/auth.py; app/schemas/user.py; app/routers/academic.py; app/routers/student_exams.py; app/routers/academic_plan.py; frontend/src/context/AuthContext.tsx; frontend/src/components/ProtectedRoute.tsx; frontend/src/App.tsx; frontend/src/pages/auth/LoginPage.tsx; frontend/src/pages/auth/StaffLoginPage.tsx; frontend/src/layouts/StaffLayout.tsx. Add app/routers/staff_profile.py and frontend/src/pages/librarian/StaffProfilePage.tsx; register in app/main.py.
Models: reuse User/Library; no second account/profile table expected. Migration: none expected.
API: retain /auth/login and /auth/me; add GET/PATCH /admin/profile with a narrow field allowlist; prevent changing role/library via staff self-profile. Restrict student-only academic actions by role. Preserve shared authorized reader preview.
Acceptance: student/librarian/admin login, mismatch redirects, expired token, refresh/logout, direct URLs/API denial and avatar/profile permission checks. Extend test_staff_auth.py; add test_staff_profile.py.

### B2. Draft/publish repair and lifecycle

Files: app/routers/admin.py; app/routers/digital_resources.py; app/schemas/digital_resource.py; app/models/digital_resource.py; app/services/ebook_storage.py; frontend/src/pages/librarian/DigitalResourceManagementPage.tsx; frontend/src/types/index.ts. Inspect actual type-file location before editing if layout changed.
Models/migration: additive archive timestamp/status metadata while retaining is_published compatibility; proposed migrate_v2_resources.py.
API: preserve existing upload/list/PUT routes; use explicit lifecycle operations or a narrow PATCH action under /admin/digital-resources/{id}. Enforce legal transitions, transactions and clear errors. Separate status updates from unnecessarily resubmitting all metadata.
Acceptance: reproduce failure with isolated records first; draft -> reload -> edit -> publish -> student listing/file read -> unpublish/archive -> denied listing/file read. Recreate backend app/client and confirm persisted state. Extend test_ebooks.py and test_staff_operations.py; add test_resource_lifecycle.py. Do not publish the user's draft just to diagnose it.

### B3. Contribution moderation

Files: app/routers/contributions.py; app/services/contributions.py; app/models/contribution.py (only if necessary); frontend/src/pages/librarian/ContributionsPage.tsx. Reuse app/routers/student_contributions.py and existing publication destinations.
Migration: none initially expected. API: extend GET /admin/contributions with kind/search filters; require nonblank rejection reason in POST /{id}/decision; retain private /{id}/file.
Acceptance: four kinds, preview authorization, approval/rejection, persisted owner status, correct resource destination, staff/time/audit, notifications, +2 exactly once and badges. Extend test_contribution_moderation.py/test_student_contributions.py; include rollback/file-failure and repeated decision cases.

### B4. Staff navigation cleanup

Files: frontend/src/layouts/StaffLayout.tsx; frontend/src/App.tsx; frontend/src/pages/librarian/LibrarianDashboardPage.tsx (verify existing filename); related dashboard shortcuts.
Models/migration/API: none. Remove student content/workspace links; retain Operations Dashboard and staff quizzes; route account to staff profile. Hide Curriculum normal workflow but preserve tables/history. Keep generic Users entry until Student Data replacement works in B6, then redirect its old URL; do not leave a dead Student Data link during transition.
Acceptance: all displayed links work, mobile navigation, role boundaries, staff PDF preview does not redirect into student-only UI. Add a staff reader route if required by B1 guards.

### B5. Circulation, student search and reservations

Files: app/routers/admin.py; app/routers/borrows.py; app/routers/reservations.py; app/routers/renewals.py; app/models/borrow.py; app/models/reservation.py; app/schemas/borrow.py; app/schemas/reservation.py; frontend/src/pages/librarian/CirculationPage.tsx. Add app/services/circulation.py to centralize transactions.
Models/migration: preserve loans/renewals; add staff attribution, request idempotency metadata and reservation lifecycle timestamps/loan link as needed. Proposed migrate_v2_circulation.py with explicit legacy-ready status mapping and duplicate-data preflight before unique indexes.
API: extend /admin/students search or use B6 paginated directory service; use /admin/catalog title/author/ISBN search; extend POST /admin/loans with selected library, validated due date and request key; make POST /borrows/ staff-only compatibility or documented rejection; staff-only return. Add reservation ready/process transition; retain cancellation/release compatibility; never delete reservation at checkout.
Acceptance: membership/library/student/book checks, duplicate checkout/retry, stock exhaustion, deterministic lock order, queue fairness, holds/release/cancel/checkout, overdue/history/renewals, notification delivery and denied direct student issue/return. Extend test_staff_operations.py/test_renewals.py/test_remaining.py; add test_v2_circulation.py with isolated PostgreSQL concurrency checks.
Note: deny unsafe student API actions in this staff phase; student UI replacement follows Stage C, with a truthful staff-only message during the interim. Do not keep self-issue enabled merely to preserve an obsolete button.

### B6. Student Data

Files: app/routers/staff_users.py; app/routers/admin.py; app/schemas/user.py; frontend/src/layouts/StaffLayout.tsx; frontend/src/App.tsx. Replace normal usage of frontend/src/pages/librarian/StaffUsersPage.tsx with new StudentDataPage.tsx and shared student picker/detail components.
Models/migration: reuse User, AcademicProfile, Library, SubjectEnrollment, BorrowRecord, Reservation. No second profile table; add search indexes only if justified.
API: paginated GET /admin/student-data and GET /admin/student-data/{id}; reuse protected /admin/users/{id}/membership or provide compatible alias. Explicit staff response schemas exclude secrets/private notes and private syllabus documents.
Acceptance: name/Student ID/email search, branch/semester/membership filters, academic fields, selected subjects, loans/due/overdue/reservations and circulation handoff; unauthorized access and sensitive-field exclusion. Add test_student_data.py.

### B7. Curated staff digital library

Files: B2 resource files plus frontend/src/pages/student/DigitalResourcesPage.tsx (only staff-publication visibility integration here), app/routers/unified_search.py, app/routers/reader.py, app/routers/ai.py, frontend/src/services resource helpers and app/main.py static-file policy where required.
Models/migration: explicit distribution basis/evidence, staff provenance/review status and cover metadata under migrate_v2_resources.py or a separate versioned follow-up. Preserve existing records and managed URLs.
API/UI: staff-only upload with license evidence, cover selection/upload, metadata, archive/unpublish/safe remove. Students see only curated published resources. Preserve OpenLibrary metadata lookup but remove arbitrary third-party content from this collection. Reconcile public URLs without moving shared files blindly.
Acceptance: public-domain/open-license/permission validation, legacy records retained but not auto-approved, draft/private URL denial, membership access, covers, existing bookmark/reading-state compatibility, safe deletion/reference protection. Extend test_ebooks.py/test_reader_state.py/test_resource_references.py.

### B8. Librarian acceptance gate

Run B1–B7 end-to-end fixture scenarios, existing librarian regression suites, TypeScript/build and browser checks. Verify backup/migration evidence and no historical data loss. Report actual draft root cause once reproduced; distinguish fixes from unconfirmed hypotheses. Only proceed to Stage C when this gate passes.

## Stage C — Student changes after librarian acceptance

### C9. Student-only circulation UI and Discover

Files: frontend/src/pages/student/BrowseBooksPage.tsx; BookDetailsPage.tsx; DashboardPage.tsx; RecommendationsPage.tsx; frontend/src/utils/library.ts; app/routers/books.py; app/schemas/book.py; app/routers/dashboard.py.
Models/migration: reuse BorrowRecord/Book/Review/Library; indexes only if needed. API: add GET /books/discover (before dynamic ID route) or documented sort/aggregate fields on existing list. Use real historical borrow counts and ratings, including honest zero counts. Remove student borrow actions everywhere; keep only permitted reservations/location/details. Tests: test_catalog_management.py plus new test_discover.py; assert no student self-issue API path is usable.

### C10. My Library synchronization

Files: frontend/src/pages/student/MyBooksPage.tsx; DashboardPage.tsx; frontend/src/types/index.ts; frontend/src/utils/library.ts; existing borrow/reservation response schemas and B5 service.
No second loan store/migration. APIs: /borrows/my, /reservations/my, /dashboard/summary must show consistent new statuses/library/due dates; refresh on relevant navigation/focus without inventing realtime updates. Remove student physical-return actions. Test staff issue -> student loan -> ready reservation -> fulfilled -> return/history, including notifications/inventory and reload persistence.

### C11. Verified borrower reviews

Files: app/routers/reviews.py; app/schemas/review.py; frontend/src/pages/student/BookDetailsPage.tsx and any actual review form component discovered. Reuse Review/BorrowRecord; preserve historical reviews.
API: backend student role and qualifying borrowed/returned history check for both creation and update; add read-only eligibility response such as GET /reviews/book/{id}/eligibility. Keep one-review-per-user/book. No purchase system. Tests: extend test_features.py and add test_review_eligibility.py covering legacy review preservation and forbidden edits without eligibility.

### C12. Student-managed curriculum and subjects

Files: app/models/curriculum.py; app/models/academic_profile.py; app/schemas/academic.py; app/routers/academic.py; app/services/academic.py; app/services/student_curriculum.py; app/routers/curriculum.py; frontend/src/components/AcademicFields.tsx; AcademicProfileForm.tsx; frontend/src/pages/student/CurriculumPage.tsx; frontend/src/pages/auth/RegisterPage.tsx.
Migration: proposed migrate_v2_personal_curricula.py adding ownership/visibility, optional node details and archival support. Reuse existing nodes, enrollment and progress. API: owner-only personal curriculum/subject/unit/topic editing under /academic; keep existing profile/topic completion contracts. Public catalog must never expose private owner records; historical shared curricula remain preserved as legacy choices/reference where applicable.
Tests: existing academic/topic/curriculum suites plus test_personal_curriculum.py, especially two-user isolation, staff denial, legacy profiles, edits preserving IDs/exam links/completed tasks and manual custom-subject structure without staff setup.

### C13. Syllabus PDF proposal and confirmation

Add app/models/syllabus_upload.py; app/schemas/syllabus.py; app/services/syllabus_processing.py; app/routers/syllabus.py; frontend/src/components/SyllabusUpload.tsx and SyllabusReview.tsx; register route in app/main.py. Reuse extraction from app/services/book_summarization.py without changing the summarization contract or assuming FLAN-T5 can parse structure reliably.
Migration: proposed migrate_v2_syllabus.py for owner/private-file metadata and proposal/confirmation state. Private storage: private_uploads/syllabi, never StaticFiles.
API: POST /academic/syllabi, GET /academic/syllabi/{id}, authenticated file access, and POST /{id}/confirm with editable validated proposal. Deterministic headings/course-code detection with evidence/page references, uncertain/unparsed sections surfaced, manual authoring fallback. Do not invent hierarchy for unrecognized prose. Confirm saves stable curriculum nodes transactionally with retry protection; upload alone does not replace a confirmed curriculum.
Tests: test_syllabus_processing.py/test_syllabus_api.py with text PDF, malformed/encrypted/oversized/image-only PDF, owner access, ambiguous headings, manually corrected structure, objectives/subtopics and repeat confirmation. No paid provider or new OCR dependency without separate approval.

### C14. Personalization from confirmed student curriculum

Files: app/services/recommendations.py; student_curriculum.py; academic_plan.py; badges.py; app/routers/academic.py; student_exams.py; frontend/src/pages/student/AcademicPlanPage.tsx; LearningPathPage.tsx; RecommendationsPage.tsx; components/ExamManager.tsx.
Reuse models/routes; no separate recommendation engine. Match real resource metadata to confirmed subjects/topics with explained evidence; retain existing weighted factors without assigning unsupported relevance. Resolve published quiz mappings carefully because private topic IDs differ from staff quiz topic IDs. Keep daily budgets, missed-day scheduling, completed tasks and empty states. Tests: extend test_recommendations.py/test_academic_plan.py/test_student_topics.py/test_student_exams.py/test_student_badges.py, including curriculum edits and partial parsing.

### C15. Resource-section submission/status integration

Files: frontend/src/pages/student/NotesPage.tsx; QuestionBanksPage.tsx; ContributionsPage.tsx; app/routers/student_contributions.py; app/routers/notes.py; app/routers/question_banks.py. Extract reusable frontend/src/components/ContributionSubmission.tsx and ContributionStatusList.tsx.
Reuse Contribution and moderation APIs; add owner kind/status filters as needed. Include a clear permitted-study-material submission entry in the appropriate resource section. Preserve private My Notes distinctly. Tests: test_student_contributions.py/test_notes_upload.py plus UI checks for pending -> approved/rejected, notifications, proper destination, retained old submissions, deduplicated XP/badges and no bypass publication.

### C16. Student navigation cleanup

Files: frontend/src/layouts/StudentLayout.tsx; frontend/src/App.tsx; related links in Notes/QuestionBanks/Profile/Dashboard. Remove My Contributions menu only after C15 works. Redirect /contributions bookmarks to an appropriate resource submission/status view rather than breaking existing links. Preserve AI/reader/quizzes/XP pages. No data migration.

### C17. Student regression gate

Exercise discovery/reservation/history/review eligibility, personal subjects, syllabus proposal/edit/confirmation, recommendations/path/plan, contribution statuses, personal notes and ownership checks. Repeat existing XP/streak/levels/badges/leaderboard/quizzes/Study Together tests and reader/summarizer tests. TypeScript/build and live UI acceptance required.

## Stage D — Final integration

Use one isolated integrated scenario through both portals: staff curated PDF lifecycle; student personal syllabus confirmation; staff-created quiz; student study/quiz; staff physical issue/return and reservation fulfillment; student eligible review; pending note/paper approval/rejection and exactly-once XP. Include refresh/backend restart persistence. Database state checks include inventory, FK references, counts excluding intended new records, files and preserved historical IDs.

Create BOOK_BRIDGE_V2_COMPLETION_REPORT.md with a per-feature matrix (implemented, backend tested, UI tested, persistence tested, remaining checks). Each phase report includes root cause/limitation, files added/modified, schema/API/UI changes, test commands/results and limits. Device camera/printing, actual local-model quality/performance and deployment/load checks are reported separately; mocked tests or a successful page load will not be described as full workflow certification.

## Approval requested

Approve this librarian-first plan to begin B1. After approval, proceed incrementally through Stage B acceptance before Stage C, then final integration. No further blanket approval is needed for ordinary work inside this approved scope; separate approval is still required for a paid AI dependency or a materially destructive/unrequested change.
