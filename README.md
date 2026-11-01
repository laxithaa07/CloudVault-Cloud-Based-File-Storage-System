# CloudVault — Cloud-Based File Storage System

A beginner-friendly, cloud-deployable file storage web application built with **Python, Flask, SQLite, HTML and CSS**.

## Features

- User registration and login with hashed passwords
- Private file storage: users can see and manage only their own files
- Upload, download and delete files
- Storage dashboard showing file count and total usage
- File type allow-list and configurable upload size limit
- Health-check endpoint at `/health`
- Docker and Gunicorn deployment support

## Project structure

```text
cloudvault_project/
├── app.py
├── requirements.txt
├── Procfile
├── Dockerfile
├── .env.example
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
├── static/style.css
├── storage/.gitkeep
└── tests/
```

## Run locally

Requires Python 3.10 or newer.

### Windows

```bash
py -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Create an account and upload a test file.

## Run with Docker

```bash
docker build -t cloudvault .
docker run --rm -p 5000:5000 \
  -e SECRET_KEY="replace-this-with-a-long-random-value" \
  -v cloudvault-data:/app/storage \
  -v cloudvault-db:/app/data \
  cloudvault
```

For a persistent database path, set `DATABASE_PATH=/app/data/cloudvault.db` and `UPLOAD_FOLDER=/app/storage` in the container environment.

## Deploy to a cloud platform

The included `Procfile` supports platforms that build Python web services from a GitHub repository (for example, Render-style services).

1. Push this project to a GitHub repository.
2. Create a new **Web Service** and connect the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variable `SECRET_KEY` with a long random value.
6. Configure a **persistent disk/volume** and set:
   - `DATABASE_PATH` to a file path on that disk, for example `/var/data/cloudvault.db`
   - `UPLOAD_FOLDER` to a directory on that disk, for example `/var/data/storage`
7. Deploy, then open `/health` to check that the service responds with `{"status":"ok","service":"CloudVault"}`.

**Important:** Many free hosting instances use temporary storage. Without a persistent disk or managed database/object storage, uploaded files and SQLite data may disappear after a restart or redeploy. For production, use managed object storage (such as Amazon S3, Azure Blob Storage or Google Cloud Storage), a managed database, HTTPS, CSRF protection, rate limiting, malware scanning, backups and secret management.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | development-only value | Flask session signing; set a strong secret in deployment |
| `PORT` | `5000` | Web server port |
| `MAX_UPLOAD_MB` | `20` | Maximum upload size per request |
| `DATABASE_PATH` | `cloudvault.db` in project folder | SQLite database location |
| `UPLOAD_FOLDER` | `storage/` in project folder | Uploaded file location |

## Supported upload types

PDF, TXT, CSV, DOC, DOCX, XLS, XLSX, PPT, PPTX, PNG, JPG, JPEG, GIF and ZIP.

## API / service check

- `GET /health` — basic health status for monitoring and deployment checks.

## GitHub upload

1. Extract the ZIP.
2. Create a new GitHub repository named `cloudvault-cloud-storage`.
3. Upload the extracted project files (not the ZIP itself) or use Git:

```bash
git init
git add .
git commit -m "Add CloudVault cloud file storage project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/cloudvault-cloud-storage.git
git push -u origin main
```

## Academic project summary

**Title:** CloudVault — Cloud-Based File Storage and Management System

**Objective:** To build a web application that demonstrates cloud-style file storage, user authentication, file management and deployment.

**Modules:** User registration, authentication, file upload, file listing, download, deletion and storage dashboard.

**Future enhancements:** Integrate S3/Cloud Storage, PostgreSQL, file sharing with expiring links, audit logs, role-based administration, encryption at rest and automated backups.
