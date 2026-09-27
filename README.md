# CloudPhoto

CloudPhoto is a Flask application for uploading photos and viewing them in a gallery.
The current implementation stores images on the local filesystem and photo records
in SQLite.

## Requirements

- Python 3.11 or newer
- A writable directory for application data

Local execution does not require AWS credentials or an external database.

## Local setup

Run the following commands from the repository root on macOS or Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app run --host 127.0.0.1 --port 5001
```

Open [CloudPhoto](http://127.0.0.1:5001) in your browser. Stop the server with `Ctrl+C`.
The application creates its data directory and database on startup.

Dependencies are defined in `requirements.txt` with bounded version ranges.
`tested-requirements.txt` records the exact versions used during verification;
install that file instead when reproducing the verified dependency environment.

## Configuration

| Setting | Default | Description |
| --- | --- | --- |
| `CLOUDPHOTO_DATA_DIR` | `data/` in the project root | Optional environment variable specifying the writable data directory. Use an absolute path. |
| Listening address | `127.0.0.1` in the startup command | Set with the Flask CLI `--host` option. |
| Listening port | `5001` in the startup command | Set with the Flask CLI `--port` option. |

The Flask application factory is `app:create_app()`.

## Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/` | Renders the photo gallery. |
| `POST` | `/upload` | Accepts a multipart file in the `photo` field; returns a 303 redirect to the gallery on success. |
| `GET` | `/photos/<filename>` | Returns a stored image, or 404 if it does not exist. |
| `GET` | `/health` | Returns HTTP 200 with `{"status":"ok"}`. |

The health endpoint reports application liveness. It does not check database
availability or filesystem readiness.

### Upload behavior

- Supported input formats: JPEG and PNG.
- Maximum image dimensions: 16 million pixels in total.
- Maximum request size: 6 MiB, including multipart overhead. Choose files under
  5 MB to allow room for that overhead.
- Images are validated and re-encoded as JPEG under generated filenames.
  Original files and embedded image metadata are not retained.
- Missing or invalid images return HTTP 400. Oversized requests return HTTP 413.

## Storage

```text
data/
├── photos/           Uploaded images, re-encoded as JPEG
└── metadata.sqlite3  Photo identifiers, sanitized names and upload timestamps
```

Both paths are located under `CLOUDPHOTO_DATA_DIR` when it is configured.
Preserve the entire data directory across restarts or application replacement.
Moving application code alone does not move its photos or database.

Local files and SQLite are specific to this implementation. Running multiple
instances with independent data directories would produce separate galleries.
Shared object storage and an external database require application changes.

## Testing

From the repository root, with the virtual environment activated:

```sh
python -m unittest discover -v
```

The tests cover health and gallery responses, upload retrieval, persistence across
application re-creation, duplicate filenames, invalid uploads, request size limits
and filename traversal handling. Tests use temporary storage and clean it up.

With the application running, verify the health response separately:

```sh
curl -i http://127.0.0.1:5001/health
```

For a manual check, upload a photo through the browser, restart the server and
confirm that the photo is still visible.

## Operational status

This version supports local development and verification. Production deployment
configuration is not included.

- The startup command uses Flask's development server and binds to localhost.
  Production deployment requires a production WSGI server.
- Authentication, authorization, CSRF protection, rate limiting and moderation
  are not implemented. Public access requires further security work.
- Request and error output is available in the development server terminal.
- Templates are rendered by Flask; they cannot be served directly as a standalone
  static frontend without application changes.
- Container packaging, cloud infrastructure and CI/CD configuration are not yet
  part of the repository.

## Repository structure

```text
app/                     Flask application, templates and styles
tests/                  Automated tests
requirements.txt         Application dependency ranges
tested-requirements.txt  Verified dependency versions
.gitignore               Local data, environments and generated-file exclusions
README.md                Application documentation
```

The `.gitignore` excludes application data, Python caches, virtual environments,
local environment files, IDE settings and logs. Keep credentials out of version
control.

## References

- [Flask file upload documentation](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
- [Flask development server documentation](https://flask.palletsprojects.com/en/stable/server/)
