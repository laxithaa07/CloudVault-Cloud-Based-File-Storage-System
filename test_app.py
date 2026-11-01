import io
import os
import tempfile
import unittest
from pathlib import Path

import app as cloud_app


class CloudVaultTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        cloud_app.DATABASE = root / "test.db"
        cloud_app.UPLOAD_FOLDER = root / "uploads"
        cloud_app.UPLOAD_FOLDER.mkdir()
        cloud_app.app.config.update(TESTING=True, SECRET_KEY="test-secret", MAX_CONTENT_LENGTH=1024 * 1024)
        self.client = cloud_app.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def register_and_login(self, username="tester"):
        self.client.post("/register", data={"username": username, "password": "password123"}, follow_redirects=True)
        return self.client.post("/login", data={"username": username, "password": "password123"}, follow_redirects=True)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_register_login_and_dashboard(self):
        self.register_and_login()
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"My files", response.data)

    def test_upload_download_delete(self):
        self.register_and_login()
        response = self.client.post(
            "/upload",
            data={"file": (io.BytesIO(b"cloud test content"), "sample.txt")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        with cloud_app.app.app_context():
            row = cloud_app.get_db().execute("SELECT id FROM files").fetchone()
            file_id = row["id"]
        download = self.client.get(f"/download/{file_id}")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.data, b"cloud test content")
        deleted = self.client.post(f"/delete/{file_id}", follow_redirects=True)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get(f"/download/{file_id}").status_code, 404)

    def test_rejects_disallowed_extension(self):
        self.register_and_login()
        response = self.client.post(
            "/upload",
            data={"file": (io.BytesIO(b"nope"), "malware.exe")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertIn(b"File type not allowed", response.data)

    def test_user_cannot_download_another_users_file(self):
        self.register_and_login("alice")
        self.client.post(
            "/upload",
            data={"file": (io.BytesIO(b"private"), "private.txt")},
            content_type="multipart/form-data",
        )
        with cloud_app.app.app_context():
            row = cloud_app.get_db().execute("SELECT id FROM files").fetchone()
            file_id = row["id"]
        self.client.post("/logout")
        self.register_and_login("bob")
        self.assertEqual(self.client.get(f"/download/{file_id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
