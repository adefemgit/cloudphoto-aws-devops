"""Developer-supplied local CloudPhoto application."""
import os
import sqlite3
import warnings
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATA_DIR=os.environ.get("CLOUDPHOTO_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")),
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    data = Path(app.config["DATA_DIR"]).resolve()
    photos = data / "photos"
    photos.mkdir(parents=True, exist_ok=True)
    database = data / "metadata.sqlite3"
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("CREATE TABLE IF NOT EXISTS photos (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")

    @app.get("/health")
    def health():
        # Liveness only: this does not check storage readiness.
        return jsonify(status="ok")

    @app.get("/")
    def gallery():
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM photos ORDER BY created_at DESC, rowid DESC").fetchall()
        return render_template("gallery.html", photos=rows)

    @app.post("/upload")
    def upload():
        photo = request.files.get("photo")
        if not photo or not photo.filename:
            return render_template("error.html", message="Choose a JPEG or PNG photo."), 400
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(photo.stream) as source:
                    if source.format not in {"JPEG", "PNG"}:
                        raise ValueError("Unsupported format")
                    if source.width * source.height > 16_000_000:
                        raise ValueError("Too many pixels")
                    source.load()
                    normalized = source.convert("RGB")
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
            return render_template("error.html", message="Use a valid JPEG or PNG up to 16 megapixels."), 400
        # Generated names avoid traversal and duplicate-name overwrites.
        filename = uuid4().hex + ".jpg"
        target = photos / filename
        try:
            normalized.save(target, "JPEG", quality=85)
            with closing(sqlite3.connect(database)) as conn, conn:
                conn.execute("INSERT INTO photos (id, name) VALUES (?, ?)",
                             (filename, secure_filename(photo.filename)[:180] or "Photo"))
        except Exception:
            target.unlink(missing_ok=True)
            raise
        finally:
            normalized.close()
        app.logger.info("Photo uploaded: %s", filename)
        return redirect(url_for("gallery"), code=303)

    @app.get("/photos/<filename>")
    def image(filename):
        return send_from_directory(photos, filename)

    @app.errorhandler(413)
    def too_large(error):
        return render_template("error.html", message="Upload request is too large. Choose a photo smaller than 5 MB."), 413

    return app
