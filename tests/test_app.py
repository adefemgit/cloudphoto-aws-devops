import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app import create_app


class CloudPhotoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = {"TESTING": True, "DATA_DIR": self.temp.name}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def upload(self, name="photo.png"):
        data = io.BytesIO()
        Image.new("RGB", (10, 10), "blue").save(data, format="PNG")
        data.seek(0)
        return self.client.post("/upload", data={"photo": (data, name)})

    def test_health_and_empty_gallery(self):
        self.assertEqual(self.client.get("/health").json, {"status": "ok"})
        self.assertIn(b"first photo", self.client.get("/").data)

    def test_upload_display_and_persistence_after_restart(self):
        self.assertEqual(self.upload().status_code, 303)
        restarted = create_app(self.config).test_client()
        self.assertIn(b"photo.png", restarted.get("/").data)
        saved = list((Path(self.temp.name) / "photos").glob("*.jpg"))
        self.assertEqual(len(saved), 1)
        response = restarted.get("/photos/" + saved[0].name)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/jpeg")
        response.close()

    def test_duplicate_names_do_not_overwrite(self):
        self.upload(); self.upload()
        self.assertEqual(len(list((Path(self.temp.name) / "photos").glob("*.jpg"))), 2)

    def test_invalid_or_missing_file_is_rejected(self):
        self.assertEqual(self.client.post("/upload").status_code, 400)
        r = self.client.post("/upload", data={"photo": (io.BytesIO(b"not an image"), "fake.jpg")})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(list((Path(self.temp.name) / "photos").iterdir()), [])

    def test_large_request_is_rejected(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 100
        self.assertEqual(self.upload().status_code, 413)

    def test_filename_cannot_escape_storage(self):
        self.assertEqual(self.upload("../../outside.png").status_code, 303)
        self.assertFalse((Path(self.temp.name) / "outside.png").exists())
        self.assertEqual(self.client.get("/photos/../metadata.sqlite3").status_code, 404)


if __name__ == "__main__":
    unittest.main()
