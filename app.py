import os
import sqlite3
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

APP_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", APP_DIR / "cloudvault.db"))
UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER", APP_DIR / "storage"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "20"))
ALLOWED_EXTENSIONS = {
    "pdf", "txt", "csv", "doc", "docx", "xls", "xlsx",
    "ppt", "pptx", "png", "jpg", "jpeg", "gif", "zip"
}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-secret"),
    MAX_CONTENT_LENGTH=MAX_UPLOAD_MB * 1024 * 1024,
    UPLOAD_FOLDER=str(UPLOAD_FOLDER),
)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def get_db():
    if "db" not in g:
        DATABASE.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL UNIQUE,
            size_bytes INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    db.commit()


@app.before_request
def prepare_database():
    init_db()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html", max_upload_mb=MAX_UPLOAD_MB)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3 or len(username) > 40:
            flash("Username must be between 3 and 40 characters.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        else:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), datetime.now(timezone.utc).isoformat())
                )
                db.commit()
                flash("Account created. Please sign in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username is already taken.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    files = get_db().execute(
        "SELECT * FROM files WHERE user_id = ? ORDER BY uploaded_at DESC",
        (session["user_id"],)
    ).fetchall()
    total_bytes = sum(item["size_bytes"] for item in files)
    return render_template("dashboard.html", files=files, total_bytes=total_bytes,
                           max_upload_mb=MAX_UPLOAD_MB)


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        flash("Choose a file before uploading.", "error")
        return redirect(url_for("dashboard"))
    safe_name = secure_filename(uploaded.filename)
    if not safe_name or not allowed_file(safe_name):
        flash("File type not allowed. Check the supported formats shown on the page.", "error")
        return redirect(url_for("dashboard"))
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    destination = UPLOAD_FOLDER / stored_name
    uploaded.save(destination)
    size_bytes = destination.stat().st_size
    try:
        db = get_db()
        db.execute(
            """INSERT INTO files (user_id, original_name, stored_name, size_bytes, uploaded_at)
               VALUES (?, ?, ?, ?, ?)""",
            (session["user_id"], safe_name, stored_name, size_bytes,
             datetime.now(timezone.utc).isoformat())
        )
        db.commit()
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    flash(f"{safe_name} uploaded successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/download/<int:file_id>")
@login_required
def download(file_id):
    record = get_db().execute(
        "SELECT * FROM files WHERE id = ? AND user_id = ?",
        (file_id, session["user_id"])
    ).fetchone()
    if not record:
        abort(404)
    path = UPLOAD_FOLDER / record["stored_name"]
    if not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=record["original_name"])


@app.route("/delete/<int:file_id>", methods=["POST"])
@login_required
def delete_file(file_id):
    record = get_db().execute(
        "SELECT * FROM files WHERE id = ? AND user_id = ?",
        (file_id, session["user_id"])
    ).fetchone()
    if not record:
        abort(404)
    (UPLOAD_FOLDER / record["stored_name"]).unlink(missing_ok=True)
    db = get_db()
    db.execute("DELETE FROM files WHERE id = ? AND user_id = ?",
               (file_id, session["user_id"]))
    db.commit()
    flash("File deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/health")
def health():
    return {"status": "ok", "service": "CloudVault"}, 200


@app.errorhandler(413)
def too_large(_error):
    flash(f"File is too large. Maximum upload size is {MAX_UPLOAD_MB} MB.", "error")
    return redirect(url_for("dashboard") if "user_id" in session else url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
