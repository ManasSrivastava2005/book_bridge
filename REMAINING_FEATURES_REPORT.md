# Remaining features — completed and verified, 2026-09-25

ROOT CAUSE:
The six core phases were implemented, but library IDs could collide, e-book uploads lacked protected storage, Notifications was a placeholder, and collaboration lacked invitations, automatic refresh, shared files and reporting/auditing. The interrupted session had left final live verification unfinished.

FILES ADDED:
- repair_library_sequence.py
- app/services/ebook_storage.py
- app/models/overdue_reminder.py
- app/services/overdue_reminders.py
- migrate_remaining.py
- frontend/src/pages/student/NotificationsPage.tsx
- frontend/src/components/StudyFiles.tsx
- frontend/src/pages/librarian/StudyModerationPage.tsx
- test_ebooks.py
- test_remaining.py
- verify_remaining_live.py
- verify_remaining_concurrency.py
- REMAINING_FEATURES_REPORT.md

FILES MODIFIED:
- app/main.py
- app/routers/admin.py
- app/routers/digital_resources.py
- app/routers/reader.py
- app/routers/notifications.py
- app/routers/study.py
- app/schemas/digital_resource.py
- app/schemas/study.py
- app/models/study.py
- migrate_study.py
- frontend/src/App.tsx
- frontend/src/layouts/StudentLayout.tsx
- frontend/src/components/ProtectedRoute.tsx
- frontend/src/components/PdfWorkspace.tsx
- frontend/src/pages/auth/LoginPage.tsx
- frontend/src/pages/student/PDFReaderPage.tsx
- frontend/src/pages/student/StudyTogetherPage.tsx
- frontend/src/pages/librarian/DigitalResourceManagementPage.tsx
- test_study.py
- verify_staff_live.py (cleanup now handles reminder notifications belonging to test fixtures)

CHANGES:
1. Library ID sequence: safely advanced the existing PostgreSQL sequence past existing IDs without renumbering or deleting rows. Recheck confirms next ID 3, highest existing ID 2, no repair needed. The maintenance script defaults to inspection and supports --apply.
2. Managed e-books: staff can upload readable, unencrypted PDFs up to 25 MiB from Manage E-Books. Files are stored under private_uploads/ebooks, outside the public static mount. Upload failures roll back metadata and clean up created files. Draft delivery is staff-only; all managed files require JWT; Library members access checks the selected library. Publication and download policy are enforced server-side. File references cannot be reassigned to another managed resource.
3. Reader: PDF.js receives JWT only for recognized managed URLs from the API. Existing external/public PDF behavior remains unchanged. Protected downloads use authenticated requests and blob downloads. Reader-state access also checks protected-library access.
4. Notifications: replaced the placeholder with a paginated inbox, individual/all mark-read actions, unread badge, and automatic per-account overdue checks while the app is active. Daily reminders are deduplicated by loan/date and stop generating after return. Other accounts cannot read or mark a user's notices.
5. Study Together: invitation-only rooms with unguessable owner-shareable links; existing rooms remain public. Private rooms are hidden from nonmembers unless they have the invitation. Invited users must still sign in and join. Login preserves a study invitation destination. Members receive in-app notifications for new posts.
6. Discussion updates: automatic refresh every 10 seconds while the tab is visible, with overlapping polls prevented. Loading older history pauses updates so that it is not immediately replaced. Manual refresh remains available.
7. Shared room files: members can explicitly upload PDF or UTF-8 TXT documents up to 10 MiB. Files are stored outside public uploads and delivered as authenticated attachments to members/staff. Authors or room moderators can remove files with confirmation. Archived rooms cannot accept new files. Personal Notes are never shared automatically.
8. Moderation: members can report a message once; staff can review/resolve reports from Study Moderation. Authors, room owners and staff retain message removal. Staff-only audit history records creation, membership changes, posting, archive/reopen, file actions, message removal and report resolution; removed message text is retained in this restricted audit history. There are no audit-edit/delete API routes.
9. Limits: account-scoped PostgreSQL-backed limits of 5 new rooms/hour, 20 posts/minute, 5 attachments/minute and 10 reports/hour; 100 members per room. HTTP 429 includes Retry-After. Room/message/file/audit/inbox listing is bounded and has pagination where needed.
10. Concurrency: account limits use FOR NO KEY UPDATE, allowing foreign-key checks when another member receives a notification. Room/report lock order is consistent. Room-level serialization and retry keys preserve duplicate-post protection.

DATABASE / DEPENDENCIES:
- Added overdue_reminders, study_audit, study_reports and study_attachments.
- Added study_rooms.is_private (false for existing rooms) and nullable invite_code.
- Migration applied twice with all pre-existing table row counts unchanged. Existing account records were not modified or deleted.
- No new dependency installation, package downgrade, or model change.
- PostgreSQL was found stopped after the session interruption and resumed using its existing data directory. No database initialization or replacement occurred.

TESTS:
- All 114 backend suite cases passed (the count includes inherited regression cases reused by the new suites).
- Final lock fix additionally passed the 20-case remaining-features suite.
- TypeScript check and production build passed.
- Combined live browser/PostgreSQL test passed: PDF upload, staff draft preview, published student PDF canvas rendering, PDF download bytes, invitation isolation/join, room-file upload/download bytes, report/resolution persistence, automatic discussion updates, notification mark-read, mobile layout, and no page errors.
- Live concurrent tests passed: both accounts posting together, simultaneous identical request IDs yielding one message, and simultaneous overdue checks yielding one reminder.
- Temporary rooms/resources/files/notifications created by these checks were cleaned up. Existing users were preserved.
- Backend runs at http://127.0.0.1:8000 and frontend at http://127.0.0.1:5173.

RESULT:
The previously listed remaining features now have working implementations. Open Staff > Manage E-Books for PDF upload, the bell for Notifications, Study Together for invitations/files/discussions, and Staff > Study Moderation for reports/auditing.

PRACTICAL LIMITS:
- Reminders are in-app and checked while an account uses Book Bridge (including the minute-by-minute unread check); no offline scheduler, email or SMS delivery is included.
- Discussion updates use 10-second polling, not WebSockets, voice/video or typing presence.
- Invitations are reusable bearer links; share them carefully. Link expiry/revocation, account bans and member removal controls are not added.
- Only PDF e-books and PDF/TXT room attachments are supported. No malware scanning service is configured.
- Disabling downloads controls the download action/endpoint; it cannot prevent copying bytes already authorized for reading. Existing legacy public upload URLs remain public.
- Limits cover the new study write actions, not a global gateway/login rate limiter. The audit is append-only through the application API, not tamper-proof against database administrators.
- Summarizer Save to Notes remains intentionally deferred. FLAN-T5 and the AI Assistant are unchanged.

Backups: backups/remaining-features, plus the earlier phase backups.
