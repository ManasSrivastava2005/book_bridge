"""Isolated Notes regressions: python -m unittest -v test_notes_upload.

Uses real routers and JWT authentication with an in-memory database and temporary
uploads. Importing app.main is deliberately avoided because it initializes the
configured application database. No existing users, files, or records are used.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.library import Library
from app.models.note import Note
from app.models.resource_usage import ResourceUsage
from app.models.user import User, UserRole
from app.routers import auth, notes
from app.services.auth import create_access_token, hash_password


class NotesUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "temporary-notes-test-password"
        cls.password_hash = hash_password(cls.password)

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(
            self.engine, tables=[Library.__table__, User.__table__, Note.__table__, ResourceUsage.__table__]
        )
        self.session_factory = sessionmaker(bind=self.engine)
        self.tokens = {}
        self.user_ids = {}
        with self.session_factory() as db:
            library = Library(name="Test Library", code="NOTES-TEST", campus="Test Campus")
            db.add(library)
            db.flush()
            self.library_id = library.id
            for role in UserRole:
                user = User(
                    name=f"Notes {role.value}",
                    email=f"notes-{role.value}@example.com",
                    hashed_password=self.password_hash,
                    role=role,
                    library_id=self.library_id,
                )
                db.add(user)
                db.flush()
                self.user_ids[role.value] = user.id
                self.tokens[role.value] = create_access_token(user.id, role.value)
            db.commit()

        temporary_uploads = TemporaryDirectory(prefix="bookbridge-notes-tests-")
        self.addCleanup(temporary_uploads.cleanup)
        self.uploads_root = Path(temporary_uploads.name).resolve()
        self.notes_dir = self.uploads_root / "notes"
        self.notes_dir.mkdir()
        upload_patch = patch.object(notes, "UPLOAD_DIR", str(self.notes_dir))
        upload_patch.start()
        self.addCleanup(upload_patch.stop)

        def test_db():
            with self.session_factory() as db:
                yield db

        application = FastAPI()
        application.dependency_overrides[get_db] = test_db
        application.include_router(auth.router)
        application.include_router(notes.router)
        application.mount("/uploads", StaticFiles(directory=self.uploads_root), name="uploads")
        self.client = TestClient(application, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def headers(self, role="librarian"):
        return {"Authorization": f"Bearer {self.tokens[role]}"} if role else {}

    def upload(self, *, role="librarian", filename="lecture.txt", content=b"Study notes\n",
               mime="text/plain", fields=None):
        data = {
            "title": "  Database study notes  ",
            "subject": "  DBMS  ",
            "semester": "5",
            "branch": "  Computer Science & Engineering  ",
            "description": "  Normalization and transactions  ",
            "access_level": "public",
        }
        if fields:
            data.update(fields)
        return self.client.post(
            "/notes/upload", data=data,
            files={"file": (filename, content, mime)}, headers=self.headers(role),
        )

    def assert_no_uploads(self):
        self.assertEqual(list(self.notes_dir.iterdir()), [])
        with self.session_factory() as db:
            self.assertEqual(db.query(Note).count(), 0)

    def assert_useful_error(self, response, status_code):
        self.assertEqual(response.status_code, status_code, response.text)
        detail = response.json().get("detail")
        self.assertTrue(detail, response.text)
        return detail

    def test_upload_persists_metadata_lists_after_reload_and_downloads(self):
        content = b"Normalization: organize relations to reduce redundancy.\n"
        response = self.upload(content=content)
        self.assertEqual(response.status_code, 201, response.text)
        note = response.json()
        self.assertEqual(note["title"], "Database study notes")
        self.assertEqual(note["subject"], "DBMS")
        self.assertEqual(note["description"], "Normalization and transactions")
        self.assertEqual(note["user_id"], self.user_ids["librarian"])
        self.assertEqual(note["library_id"], self.library_id)
        self.assertEqual(note["file_type"], "TXT")
        self.assertEqual(note["status"], "published")
        self.assertEqual(note["download_count"], 0)
        stored = self.notes_dir / note["file_url"].rsplit("/", 1)[-1]
        self.assertEqual(stored.read_bytes(), content)
        with self.session_factory() as db:
            record = db.get(Note, note["id"])
            self.assertIsNotNone(record)
            self.assertEqual(record.file_url, note["file_url"])
            self.assertEqual(record.title, note["title"])
        for _ in range(2):
            listing = self.client.get("/notes/")
            self.assertEqual(listing.status_code, 200, listing.text)
            self.assertEqual([item["id"] for item in listing.json()], [note["id"]])
        fetched = self.client.get(f"/notes/{note['id']}")
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["file_url"], note["file_url"])
        download = self.client.get(note["file_url"])
        self.assertEqual(download.status_code, 200, download.text)
        self.assertEqual(download.content, content)
        for expected in (1, 2):
            tracked = self.client.post(f"/notes/{note['id']}/download")
            self.assertEqual(tracked.status_code, 200, tracked.text)
            self.assertEqual(tracked.json()["download_count"], expected)
            self.assertEqual(tracked.json()["file_url"], note["file_url"])
        self.assertEqual(self.client.get("/notes/").json()[0]["download_count"], 2)
        with self.session_factory() as db:
            self.assertEqual(db.get(Note, note["id"]).download_count, 2)

    def test_real_login_token_can_upload_and_profile_remains_accessible(self):
        login = self.client.post("/auth/login", json={
            "email": "notes-librarian@example.com", "password": self.password,
        })
        self.assertEqual(login.status_code, 200, login.text)
        self.tokens["librarian"] = login.json()["access_token"]
        profile = self.client.get("/auth/me", headers=self.headers())
        self.assertEqual(profile.status_code, 200, profile.text)
        self.assertEqual(profile.json()["role"], "librarian")
        self.assertEqual(self.upload().status_code, 201)

    def test_admin_and_librarian_can_upload(self):
        for role in ("admin", "librarian"):
            with self.subTest(role=role):
                response = self.upload(role=role)
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(response.json()["user_id"], self.user_ids[role])

    def test_student_cannot_upload_or_create_metadata(self):
        self.assert_useful_error(self.upload(role="student"), 403)
        created = self.client.post("/notes/", json={"title": "Not permitted"},
                                   headers=self.headers("student"))
        self.assert_useful_error(created, 403)
        self.assert_no_uploads()

    def test_missing_and_invalid_tokens_are_rejected(self):
        self.assert_useful_error(self.upload(role=None), 401)
        self.tokens["librarian"] = "invalid-token"
        self.assert_useful_error(self.upload(), 401)
        self.assert_no_uploads()

    def test_database_role_overrides_privileged_token_claim(self):
        self.tokens["student"] = create_access_token(self.user_ids["student"], "admin")
        self.assert_useful_error(self.upload(role="student"), 403)
        self.assert_no_uploads()

    def test_supported_extensions_and_mime_types(self):
        formats = {
            "PDF": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "ppt": "application/vnd.ms-powerpoint",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "txt": "text/plain",
        }
        for extension, mime in formats.items():
            with self.subTest(extension=extension):
                response = self.upload(filename=f"lecture.{extension}", mime=mime)
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(response.json()["file_type"], extension.upper())

    def test_file_at_25_mib_boundary_is_allowed(self):
        response = self.upload(content=b"x" * (25 * 1024 * 1024))
        self.assertEqual(response.status_code, 201, response.text)
        stored = self.notes_dir / response.json()["file_url"].rsplit("/", 1)[-1]
        self.assertEqual(stored.stat().st_size, 25 * 1024 * 1024)

    def test_file_over_25_mib_is_rejected_without_writes(self):
        response = self.upload(content=b"x" * (25 * 1024 * 1024 + 1))
        detail = self.assert_useful_error(response, 400)
        self.assertIn("25", str(detail))
        self.assert_no_uploads()

    def test_unsupported_extension_mime_and_empty_file_are_rejected(self):
        cases = (
            {"filename": "lecture.exe", "mime": "application/octet-stream"},
            {"filename": "lecture.pdf", "mime": "text/html"},
            {"content": b""},
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                self.assert_useful_error(self.upload(**arguments), 400)
                self.assert_no_uploads()

    def test_invalid_metadata_is_rejected_before_storage(self):
        cases = (
            {"title": "   "}, {"title": "x" * 256},
            {"subject": "   "}, {"subject": "x" * 101},
            {"branch": "x" * 101}, {"access_level": "x" * 51},
            {"semester": "0"}, {"semester": "9"}, {"semester": "not-a-number"},
        )
        for fields in cases:
            with self.subTest(fields=fields):
                self.assert_useful_error(self.upload(fields=fields), 422)
                self.assert_no_uploads()

    def test_missing_required_multipart_field_is_rejected(self):
        response = self.client.post(
            "/notes/upload", headers=self.headers(),
            data={"subject": "DBMS", "semester": "5"},
            files={"file": ("lecture.txt", b"Study notes", "text/plain")},
        )
        self.assert_useful_error(response, 422)
        self.assert_no_uploads()

    def test_traversal_and_long_names_stay_inside_upload_directory(self):
        for filename in ("../../outside.txt", "..\\..\\windows.txt", "x" * 300 + ".txt"):
            with self.subTest(filename=filename):
                response = self.upload(filename=filename)
                self.assertEqual(response.status_code, 201, response.text)
                file_url = response.json()["file_url"]
                self.assertTrue(file_url.startswith("/uploads/notes/"))
                basename = file_url.removeprefix("/uploads/notes/")
                self.assertNotIn("/", basename)
                self.assertNotIn("\\", basename)
                self.assertLessEqual(len(basename), 255)
                stored = (self.notes_dir / basename).resolve()
                self.assertEqual(stored.parent, self.notes_dir.resolve())
                self.assertEqual(stored.read_bytes(), b"Study notes\n")

    def test_duplicate_filenames_never_overwrite_existing_upload(self):
        first = self.upload(content=b"First document")
        second = self.upload(content=b"Second document")
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        self.assertNotEqual(first.json()["file_url"], second.json()["file_url"])
        self.assertEqual(self.client.get(first.json()["file_url"]).content, b"First document")
        self.assertEqual(self.client.get(second.json()["file_url"]).content, b"Second document")

    def test_commit_failure_rolls_back_metadata_and_removes_file(self):
        with patch.object(self.session_factory.class_, "commit",
                          side_effect=SQLAlchemyError("private database diagnostics")):
            response = self.upload()
        detail = self.assert_useful_error(response, 500)
        self.assertIsInstance(detail, str)
        self.assertNotIn("private database diagnostics", response.text)
        self.assert_no_uploads()

    def test_storage_failure_returns_useful_error_without_metadata(self):
        with patch("builtins.open", side_effect=PermissionError("private filesystem diagnostics")):
            response = self.upload()
        detail = self.assert_useful_error(response, 500)
        self.assertIsInstance(detail, str)
        self.assertNotIn("private filesystem diagnostics", response.text)
        self.assert_no_uploads()

    def test_json_creation_uses_authenticated_library_without_duplicate_keyword(self):
        response = self.client.post("/notes/", headers=self.headers(), json={
            "title": "Existing document", "subject": "DBMS", "library_id": 987654,
            "file_url": "https://example.com/study.txt", "file_type": "TXT",
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["library_id"], self.library_id)
        self.assertEqual(response.json()["user_id"], self.user_ids["librarian"])
        with self.session_factory() as db:
            self.assertEqual(db.scalar(select(Note.library_id)), self.library_id)

    def test_personal_notes_are_owner_only_and_outside_public_storage(self):
        with TemporaryDirectory() as private, patch.object(notes, "PRIVATE_UPLOAD_DIR", private):
            response = self.client.post("/notes/my/upload", headers=self.headers("student"),
                data={"title": "Private revision", "subject": "OS", "semester": "4", "access_level": "public", "status": "published", "user_id": self.user_ids["admin"]},
                files={"file": ("../../revision.txt", b"My private study notes", "text/plain")})
            self.assertEqual(response.status_code, 201, response.text)
            note = response.json()
            self.assertEqual(note["status"], "personal")
            self.assertEqual(note["access_level"], "private")
            self.assertEqual(note["user_id"], self.user_ids["student"])
            self.assertEqual(self.client.get("/notes/").json(), [])
            self.assertEqual(self.client.get("/notes/my", headers=self.headers("student")).json()[0]["id"], note["id"])
            self.assertEqual(self.client.get("/notes/my", headers=self.headers("admin")).json(), [])
            self.assertEqual(self.client.get("/notes/my").status_code, 401)
            for role in (None, "admin", "librarian"):
                self.assertIn(self.client.get(note["file_url"], headers=self.headers(role)).status_code, (401, 404))
                self.assertEqual(self.client.get(f"/notes/{note['id']}", headers=self.headers(role)).status_code, 404)
                self.assertEqual(self.client.post(f"/notes/{note['id']}/download", headers=self.headers(role)).status_code, 404)
            downloaded = self.client.get(note["file_url"], headers=self.headers("student"))
            self.assertEqual(downloaded.content, b"My private study notes")
            self.assertEqual(downloaded.headers["cache-control"], "private, no-store")
            self.assertEqual(list(self.notes_dir.iterdir()), [])
            self.assertEqual(self.client.get("/uploads/notes/" + note["file_url"].rsplit("/", 1)[-1]).status_code, 404)
            self.assertEqual(self.client.delete(f"/notes/{note['id']}", headers=self.headers("admin")).status_code, 404)
            self.assertEqual(self.client.delete(f"/notes/{note['id']}", headers=self.headers("student")).status_code, 204)
            self.assertEqual(list(Path(private).iterdir()), [])
            self.assertEqual(self.client.get(note["file_url"], headers=self.headers("student")).status_code, 404)

    def test_personal_upload_validation_and_rollback(self):
        self.assertEqual(self.client.post("/notes/", headers=self.headers(), json={"title": "Forged private note", "status": "personal"}).status_code, 422)
        with TemporaryDirectory() as private, patch.object(notes, "PRIVATE_UPLOAD_DIR", private):
            def upload(content=b"study", filename="notes.txt", role="student"):
                return self.client.post("/notes/my/upload", headers=self.headers(role),
                    data={"title": "Study", "subject": "CS", "semester": "1"},
                    files={"file": (filename, content, "text/plain")})
            self.assertEqual(upload(role=None).status_code, 401)
            self.assertEqual(upload(content=b"").status_code, 400)
            self.assertEqual(upload(filename="notes.exe").status_code, 400)
            self.assertEqual(upload(content=b"x" * (notes.MAX_FILE_SIZE + 1)).status_code, 400)
            with patch.object(self.session_factory.class_, "commit", side_effect=SQLAlchemyError("test")):
                self.assertEqual(upload().status_code, 500)
            self.assertEqual(list(Path(private).iterdir()), [])
            self.assert_no_uploads()

    def test_download_and_get_missing_note_return_404(self):
        self.assert_useful_error(self.client.get("/notes/999999"), 404)
        self.assert_useful_error(self.client.post("/notes/999999/download"), 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
