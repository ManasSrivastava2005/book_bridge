# Phase 4 — Completed reader features

ROOT CAUSE:
The original browser PDF iframe could not report page changes, text selection, actual page count, or chapter destinations. The first increment therefore stored manual bookmarks in one browser. A controlled PDF renderer and private server-side state were required to complete Phase 4.

FILES MODIFIED:
- app/main.py
- frontend/src/pages/student/PDFReaderPage.tsx
- frontend/src/utils/reader.ts
- frontend/package.json and frontend/package-lock.json
- frontend/test-reader.mjs
- verify_reader_live.py
- .gitignore

FILES ADDED:
- app/models/reader_state.py
- app/schemas/reader.py
- app/routers/reader.py
- migrate_reader.py
- test_reader_state.py
- frontend/src/components/PdfWorkspace.tsx
- frontend/src/hooks/useReaderState.ts
- frontend/scripts/prepare-pdf.mjs

CHANGES:
- Real PDF rendering, selectable text, actual page count, previous/next/direct navigation, chapter outlines when embedded in the PDF, responsive zoom, and paper/sepia/night themes.
- Automatic account-synced reading position. This is a single-page viewer; changing pages automatically saves the position.
- Private page bookmarks/notes and persistent text highlights with editable notes, deletion, and page navigation. Highlight rectangles use normalized coordinates so they remain aligned when zoom changes.
- JWT-protected GET/PUT /reader/{resource_id}/state. Ownership comes from the authenticated account, never a caller-supplied user ID. Bounded request schemas and optimistic versions prevent stale sessions overwriting newer data.
- Older browser bookmarks and their saved page can be imported explicitly. Existing server notes win when bookmark pages overlap. Browser copies are retained.
- Fingerprints detect a replaced PDF and pause editing/saving rather than applying old highlights to new text.
- Shared Notes permissions, JWT implementation, AI Assistant, local summarizer, and existing routes retained. Phase 4 reader notes are private data in their own table, not student uploads to shared Notes.

DEPENDENCIES:
React-PDF 10.5.0 is pinned and supports the existing React 18 application. React-PDF 11 requires React 19, so it was not selected. The viewer is loaded on demand; its PDF.js worker, character maps, fonts, and WASM assets are served locally. `npm run dev` and `npm run build` prepare those assets automatically. Source documentation: https://github.com/wojtekmaj/react-pdf/tree/v10.x/packages/react-pdf

DATABASE:
Added reader_states with a unique (user_id, resource_id) constraint, JSON data, optimistic version, timestamp, and foreign keys. The idempotent migration was tested in SQLite and applied twice to PostgreSQL. Existing users, books, borrowing records, resources, and Notes counts were verified unchanged. No existing table was reset or repopulated.

TESTS:
- 55 backend tests passed: reader ownership/versioning/validation/migration plus existing summarization and Notes regressions.
- TypeScript and production build passed.
- Utility checks passed for old browser-state parsing, account/document separation, unsafe URLs, and page limits.
- Real three-page PDF browser check passed: canvas/text rendering, page count, automatic resume, bookmark import, bookmark/notes persistence, highlight creation/edit/removal, chapter navigation, theme, zoom, 390px mobile layout, missing and unsafe links, and no page errors.
- Cleared old browser data and reloaded: progress, bookmarks, highlights and theme were restored from the server.
- A second independent HTTP client verified persistence. A competing save triggered the intended browser conflict error; reloading recovered the newer server state without overwriting it.
- Temporary verification records and PDFs were removed.

RESULT:
Phase 4's reader, bookmarks, automatic progress, private notes and highlights are implemented and verified. Open Digital Library → Read Online for a PDF. The API/frontend are running locally. Cross-device access requires the other device to reach this Book Bridge server and use the same account; localhost is not an internet deployment.

KNOWN LIMITATIONS:
- Image-only scans need OCR for selectable text/highlighting. No OCR was added.
- External PDF servers must permit browser cross-origin access. Blocked, encrypted, invalid PDFs provide an Open original fallback. External non-PDF pages retain embedded reading without PDF-specific tools.
- PDF fonts are fixed-layout; zoom is supported, font replacement is not.
- A changed PDF preserves existing notes and pauses edits; automatic annotation remapping is not supported.
- Changes must finish syncing before closing the page. Save failures and version conflicts are shown explicitly.
- npm audit reports two existing moderate React Router findings; the new PDF dependency was not flagged. No unrelated major router upgrade was performed.

PHASE 5:
Librarian improvements follow this completed phase. Backups are in backups/phase4-completion and the original backups/phase4-reader.
