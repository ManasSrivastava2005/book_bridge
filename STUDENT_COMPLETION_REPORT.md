# Student completion report

Date: 2026-09-28. Scope: the approved 15 student phases, built on the accepted librarian/admin foundation.

## Implemented features

1. Server-side XP using the existing XPTransaction ledger and authenticated history.
2. Fifty cumulative reader levels shared by Dashboard and Profile.
3. Persisted server-timed reading sessions, meaningful reading days and streaks.
4. Automatic, idempotent badge ownership from persisted activity.
5. PostgreSQL weekly/monthly/all-time leaderboard and academic filters.
6. Backend-derived, display-only daily missions.
7. Optional academic profile, custom subjects and four-step registration.
8. Staff curriculum selection, enrollment, mapped resources and topic completion.
9. Owner-scoped exam CRUD with all six requested exam types.
10. Persisted Academic Plan, workload limits and missed-day rescheduling.
11. Learning path based on selected curriculum, progress and exams.
12. Explainable recommendations using real catalog/history/review data.
13. Persisted ten-question chapter quizzes with server scoring.
14. Private student contribution uploads and moderation status.
15. Professional profile with real progress, XP history, badges, exams and plan shortcuts.

JWT and existing librarian permissions remain in place. The AI Assistant and local FLAN-T5 summarization services were preserved; no ML packages, model or cloud-fallback settings were changed in this student implementation. The dashboard now reports an AI failure honestly instead of inventing catalog answers.

## Database migrations

All migrations are additive and individually repeatable:

- migrate_student_xp.py: event type and description on the existing ledger.
- migrate_student_reading.py: reading sessions and daily aggregates.
- migrate_student_badges.py: badge definitions and unique user/badge ownership.
- migrate_student_academic.py: optional academic profiles.
- migrate_student_topics.py: user/topic completion.
- migrate_student_exams.py: student exams.
- migrate_student_plan.py: persisted academic tasks.
- migrate_student_quizzes.py: quiz attempts and immutable question snapshots.
- migrate_student_contributions.py: nullable request key/hash and unique user/request constraint.

The final migration check executed all nine migrations twice and confirmed unchanged counts across all 42 existing tables, including four users and ten books. Earlier phase checks preserved existing rows as new tables were introduced. Badge-definition insertion was intentional. No tables were dropped, truncated or reset. Temporary live verification records/files were removed.

## XP rules

The backend awards daily login +25, meaningful reading +25, valid quiz completion +25 and reading streak continuation +25, each at most once per UTC calendar day. Approval grants +2 per contribution. Pending/rejected submissions grant nothing. Unique event keys and owner locks prevent repeat rewards; the browser cannot submit an XP amount. Missions and badges do not add duplicate XP. Login rewards require a successful login, not merely restoring a stored session.

## Level formula

Completing level L costs 200 × L XP. Level L begins at cumulative 100 × (L−1) × L. Level 50 starts at 245,000 XP and completes at 255,000; lifetime XP can continue increasing. Titles progress from New Reader through Bronze Reader (5), Silver Scholar (10), Gold Scholar (20), Knowledge Master (35) and Book Bridge Legend (50). Levels are calculated from the ledger.

## Badge rules

- Reading: 1/5/10/25/50 distinct borrowed titles.
- Streak: longest streak of 3/7/14/30/100 qualifying days.
- Level: 5/10/20/35/50.
- Contributions: first approval, first approved paper, five approvals, twenty approvals.
- Quizzes: first distinct quiz, five distinct quizzes scoring at least 80%, any perfect score, twenty distinct quizzes.
- Curriculum: select a subject; reach 25%, 50%, or 100% in a selected subject; complete a subject with an upcoming exam.

Ownership is stored in UserBadge with a uniqueness constraint. Previously existing definitions are preserved; legacy definitions without a new automatic rule are not falsely marked earned. Badge ownership is retained once awarded.

## Leaderboard rules

Students only. Weekly means UTC Monday-start week; monthly means UTC calendar month. Rankings sum timestamped XP events, with stable ID ordering for ties, while displayed levels use lifetime XP. Branch/semester filters use the signed-in student's real academic values; absent values produce an honest unavailable/empty result. Public rows omit IDs and email. The current student's rank is returned even outside the displayed page.

## Reading and streak rules

Only server-verifiable library-uploaded PDFs qualify. Heartbeats validate ownership, page bounds and increasing sequence numbers. The server credits bounded elapsed time, not client-provided durations. Page counting requires dwell time and avoids duplicate page credit in the same day. One active session per user limits parallel farming. A day qualifies at ten pages OR 900 seconds. Streak continuation requires the previous day to qualify. Current/longest streaks derive from stored qualifying dates.

Browser visibility/focus and recent interaction gate activity. This deters obvious farming but cannot prove attention or comprehension. External PDFs remain readable without verified reading rewards. Totals count daily recorded pages; rereading a page on another day can count again.

## Academic profile and curriculum integration

Academic fields are optional for existing accounts and registration. The hierarchy supports college, program, branch, specialization, semester, staff curriculum, selected subjects and custom subjects. Registration has four steps with skippable academic setup; exams are added after registration. Staff curriculum remains the source of units, topics and resource mappings. Owner-scoped topic completion updates subject progress and badges. Profile changes refresh exam subject options.

## Exam planning and Academic Plan

Exams support CAT-I, CAT-II, Midterm, End Semester, Practical and Custom. Plans combine selected topics, resource mappings, completion, saved reading position, published quizzes and upcoming exams. Remaining work is rescheduled on retrieval; completed work is preserved. A daily time budget caps allocations, with explicit warnings and unscheduled tasks when capacity is insufficient. Without an exam, planning uses a rolling seven-day window. Study/revision completion is self-reported; quiz tasks require a persisted attempt. Custom subjects without staff topic structure receive exam dates but no invented syllabus. The page links learning paths and recommended resources.

## Recommendations

Score out of 100: curriculum relevance up to 40 (20 for completed-topic revision), exam urgency up to 25 over a 30-day window, borrowed-category history 15, available copies 10 and actual average rating up to 10. Explanations accompany each result. Zero ratings/reviews stay zero. This is a deterministic relevance score, not a probability or trained model.

## Quiz system

Only active, published, permission-confirmed librarian quizzes are exposed. Ten questions are snapshotted at attempt creation; answer keys are hidden until submission. Answers, score, timestamp and book/subject/chapter/topic context persist. Submission validates ownership and answers; identical retries return the stored result and changed resubmissions are rejected. +25 XP is capped daily. No content was inferred or downloaded from ISBN.

## Contribution workflow

Students submit notes, papers, question banks or study materials with academic metadata and PDF/text files up to 25 MB. Files remain private while pending. The owner can see status and download their own submission; other students cannot. Retry keys prevent duplicate uploads. Existing librarian approval/rejection stays authoritative and grants +2 only on approval. Personal notes uploads remain available separately.

## Profile

Real level/title/lifetime XP, progress, paginated XP history, current/longest streak, verified reading totals, completed quiz count/average, approved contributions, badges, subject progress, academic information, exam management and plan links are shown. Books read is explicitly a proxy: distinct returned loan titles. Empty records show zero/no attempts instead of demo values. Sample dashboard activity, reading statistics and fake student-ID fallback were removed.

## Tests

The final regression batches passed 263 backend test executions (200 broad regression + 56 student/contribution + 7 profile). Shared inherited test classes mean this is an execution count, not 263 unique scenarios. The final profile adjustment was rechecked: seven executions passed on 2026-09-28. Coverage includes authentication/roles, catalog/circulation, renewals, contributions, curricula, staff/student quizzes, announcements, analytics, QR, resources, notes, reader state, study, summarizer error behavior, XP/levels/streaks/badges, leaderboard, missions, academic profile/exams/planning/recommendations and profile ownership.

TypeScript: npx tsc --noEmit --project tsconfig.app.json passed.
Production frontend: npm run build passed on 2026-09-28.
Live student checks throughout the phases covered reading tracking, badges, rankings, registration entry, curriculum completion, exams, planning, learning paths, recommendations, quiz submission, pending contribution upload and final Profile/Dashboard. Final profile/dashboard check passed after restarting services. These used temporary fixtures with cleanup.

Final librarian UI regression on 2026-09-28: all twelve screens loaded their expected headings with no alert messages: dashboard, books, circulation, resources, contributions, curricula, quizzes, announcements, analytics, QR, users and study moderation. No staff records were changed.

## Known limitations

- Vite reports a non-blocking bundle above 500 kB; route splitting remains a performance improvement.
- Production load/concurrent multi-worker stress testing and a fresh real FLAN-T5 quality benchmark were not performed in this student pass. Summarizer regression tests use controlled fixtures.
- Reading verification cannot establish human attention. Daily reward and ranking boundaries use UTC.
- Planning durations are estimates, the chosen time budget resets on page load, and custom subjects need structured topics for automatic scheduling.
- Full registration was covered by API fixtures; automated browser checks did not type a real user's password.
- Existing profile notification toggles are outside this student scope; this report does not claim new notification scheduling.
- This is a local development deployment, not a public hosted release.

## Local access

Student: http://127.0.0.1:5173/login
Librarian/admin: http://127.0.0.1:5173/librarian/login
Backend: http://127.0.0.1:8000

The local services must remain running for these URLs to work.
