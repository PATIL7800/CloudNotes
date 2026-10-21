
import io
import os
import uuid

import firebase_admin
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    session,
    request,
    jsonify,
    redirect,
    url_for,
    send_file,
)
from firebase_admin import credentials, firestore, storage, auth
from supabase import create_client
from werkzeug.utils import secure_filename


# --------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------

load_dotenv()

FLASK_SECRET_KEY = os.environ["FLASK_SECRET_KEY"]
FIREBASE_CREDENTIALS = os.environ["FIREBASE_CREDENTIALS"]
FIREBASE_STORAGE_BUCKET = os.environ["FIREBASE_STORAGE_BUCKET"]

SUPABASE_URL = os.environ["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ[
    "SUPABASE_SERVICE_ROLE_KEY"
].strip()
SUPABASE_STORAGE_BUCKET = os.environ[
    "SUPABASE_STORAGE_BUCKET"
].strip()

if not SUPABASE_URL.startswith("https://"):
    raise ValueError("Invalid SUPABASE_URL in .env")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Supabase server-side key is missing")

if not SUPABASE_STORAGE_BUCKET:
    raise ValueError("Supabase bucket name is missing")


# --------------------------------------------------
# FLASK CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# --------------------------------------------------
# FIREBASE INITIALIZATION
# --------------------------------------------------

cred = credentials.Certificate(FIREBASE_CREDENTIALS)

if not firebase_admin._apps:
    firebase_admin.initialize_app(
        cred,
        {"storageBucket": FIREBASE_STORAGE_BUCKET}
    )

db = firestore.client()

# Keep the Firebase Storage connection available
# for compatibility with your existing configuration.
firebase_bucket = storage.bucket()


# --------------------------------------------------
# SUPABASE INITIALIZATION
# --------------------------------------------------

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)


# --------------------------------------------------
# HOME AND AUTHENTICATION PAGES
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/auth/session", methods=["POST"])
def create_session():
    data = request.get_json(silent=True) or {}
    id_token = data.get("idToken")

    if not id_token:
        return jsonify({
            "error": "Missing authentication token"
        }), 401

    try:
        decoded_token = auth.verify_id_token(id_token)

        session.clear()
        session["uid"] = decoded_token["uid"]

        return jsonify({"success": True}), 200

    except Exception:
        app.logger.exception("Firebase authentication failed")
        return jsonify({
            "error": "Authentication failed"
        }), 401


@app.route("/dashboard")
def dashboard():
    if "uid" not in session:
        return redirect(url_for("home"))

    return render_template("dashboard.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


# --------------------------------------------------
# USER-SPECIFIC FIRESTORE COLLECTIONS
# --------------------------------------------------

def get_user_notes():
    uid = session.get("uid")

    if not uid:
        return None

    return (
        db.collection("users")
        .document(uid)
        .collection("notes")
    )


def get_user_files():
    uid = session.get("uid")

    if not uid:
        return None

    return (
        db.collection("users")
        .document(uid)
        .collection("files")
    )


# --------------------------------------------------
# NOTES: LIST
# --------------------------------------------------

@app.route("/api/notes", methods=["GET"])
def get_notes():
    notes_ref = get_user_notes()

    if notes_ref is None:
        return jsonify({
            "error": "Please log in first"
        }), 401

    notes = []

    for doc in notes_ref.stream():
        note = doc.to_dict() or {}
        note["id"] = doc.id
        notes.append(note)

    return jsonify(notes), 200


# --------------------------------------------------
# NOTES: CREATE
# --------------------------------------------------

@app.route("/api/notes", methods=["POST"])
def create_note():
    notes_ref = get_user_notes()

    if notes_ref is None:
        return jsonify({
            "error": "Please log in first"
        }), 401

    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    content = data.get("content", "")

    if not isinstance(title, str) or not isinstance(content, str):
        return jsonify({
            "error": "Title and content must be text"
        }), 400

    title = title.strip()
    content = content.strip()

    if not title or not content:
        return jsonify({
            "error": "Title and content are required"
        }), 400

    note_ref = notes_ref.document()

    note_ref.set({
        "title": title,
        "content": content
    })

    return jsonify({
        "message": "Note created successfully",
        "id": note_ref.id
    }), 201


# --------------------------------------------------
# NOTES: UPDATE
# --------------------------------------------------

@app.route("/api/notes/<note_id>", methods=["PUT"])
def update_note(note_id):
    notes_ref = get_user_notes()

    if notes_ref is None:
        return jsonify({
            "error": "Please log in first"
        }), 401

    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    content = data.get("content", "")

    if not isinstance(title, str) or not isinstance(content, str):
        return jsonify({
            "error": "Title and content must be text"
        }), 400

    title = title.strip()
    content = content.strip()

    if not title or not content:
        return jsonify({
            "error": "Title and content are required"
        }), 400

    note_ref = notes_ref.document(note_id)

    if not note_ref.get().exists:
        return jsonify({"error": "Note not found"}), 404

    note_ref.update({
        "title": title,
        "content": content
    })

    return jsonify({
        "message": "Note updated successfully"
    }), 200


# --------------------------------------------------
# NOTES: UPDATE PINNED AND FAVORITE STATUS
# --------------------------------------------------

@app.route("/api/notes/<note_id>/preferences", methods=["PATCH"])
def update_note_preferences(note_id):
    notes_ref = get_user_notes()

    if notes_ref is None:
        return jsonify({"error": "Please log in first"}), 401

    data = request.get_json(silent=True) or {}

    updates = {}
    for field in ("pinned", "favorite"):
        if field in data:
            if not isinstance(data[field], bool):
                return jsonify({
                    "error": f"{field} must be true or false"
                }), 400
            updates[field] = data[field]

    if not updates:
        return jsonify({
            "error": "No valid preferences provided"
        }), 400

    note_ref = notes_ref.document(note_id)

    if not note_ref.get().exists:
        return jsonify({"error": "Note not found"}), 404

    note_ref.update(updates)

    return jsonify({
        "message": "Note preferences updated successfully"
    }), 200



# --------------------------------------------------
# NOTES: DELETE
# --------------------------------------------------

@app.route("/api/notes/<note_id>", methods=["DELETE"])
def delete_note(note_id):
    notes_ref = get_user_notes()

    if notes_ref is None:
        return jsonify({
            "error": "Please log in first"
        }), 401

    note_ref = notes_ref.document(note_id)

    if not note_ref.get().exists:
        return jsonify({"error": "Note not found"}), 404

    note_ref.delete()

    return jsonify({
        "message": "Note deleted successfully"
    }), 200


# --------------------------------------------------
# FILE CONFIGURATION
# --------------------------------------------------

ALLOWED_EXTENSIONS = {
    "pdf",
    "txt",
    "csv",
    "png",
    "jpg",
    "jpeg",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


# --------------------------------------------------
# FILES: LIST
# --------------------------------------------------

@app.route("/api/files", methods=["GET"])
def list_files():
    files_ref = get_user_files()

    if files_ref is None:
        return jsonify({
            "error": "Please log in first"
        }), 401

    result = []

    for doc in files_ref.stream():
        item = doc.to_dict() or {}
        item["id"] = doc.id
        result.append(item)

    return jsonify(result), 200


# --------------------------------------------------
# FILES: UPLOAD
# --------------------------------------------------

@app.route("/api/files", methods=["POST"])
def upload_file():
    files_ref = get_user_files()

    if files_ref is None:
        return jsonify({
            "error": "Please log in first"
        }), 401

    uploaded = request.files.get("file")

    if not uploaded or not uploaded.filename:
        return jsonify({
            "error": "Please select a file"
        }), 400

    filename = secure_filename(uploaded.filename)

    if not filename or "." not in filename:
        return jsonify({
            "error": "Invalid filename"
        }), 400

    extension = filename.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": "This file type is not allowed"
        }), 400

    file_data = uploaded.read()

    if not file_data:
        return jsonify({
            "error": "The selected file is empty"
        }), 400

    if len(file_data) > MAX_FILE_SIZE:
        return jsonify({
            "error": "File size must be 10 MB or less"
        }), 413

    file_id = uuid.uuid4().hex

    uid = session["uid"]

    storage_path = (
        f"users/{uid}/files/{file_id}_{filename}"
    )

    storage_uploaded = False

    try:
        # Upload file to the private Supabase bucket.
        supabase.storage.from_(
            SUPABASE_STORAGE_BUCKET
        ).upload(
            path=storage_path,
            file=file_data,
            file_options={
                "content-type": (
                    uploaded.mimetype
                    or "application/octet-stream"
                ),
                "upsert": "false"
            }
        )

        storage_uploaded = True

        # Save metadata under the authenticated user's
        # Firestore files collection.
        files_ref.document(file_id).set({
            "filename": filename,
            "storage_path": storage_path,
            "size": len(file_data)
        })

        return jsonify({
            "message": "File uploaded successfully",
            "id": file_id
        }), 201

    except Exception:
        app.logger.exception("Supabase file upload failed")

        # Clean up the uploaded object if metadata saving
        # failed after the Storage upload succeeded.
        if storage_uploaded:
            try:
                supabase.storage.from_(
                    SUPABASE_STORAGE_BUCKET
                ).remove([storage_path])

            except Exception:
                app.logger.exception(
                    "Supabase upload cleanup failed"
                )
        return jsonify({
            "error": (
                "File upload failed. Check the VS Code terminal."
            )
        }), 500


# --------------------------------------------------
# FILES: DOWNLOAD
# --------------------------------------------------

@app.route(
    "/api/files/<file_id>/download",
    methods=["GET"]
)
def download_file(file_id):
    files_ref = get_user_files()

    if files_ref is None:
        return jsonify({
            "error": "Please log in first"
        }), 401

    doc = files_ref.document(file_id).get()

    if not doc.exists:
        return jsonify({
            "error": "File not found"
        }), 404

    item = doc.to_dict() or {}

    storage_path = item.get("storage_path")
    filename = item.get("filename")

    if not storage_path or not filename:
        return jsonify({
            "error": "File metadata is incomplete"
        }), 500

    try:
        content = supabase.storage.from_(
            SUPABASE_STORAGE_BUCKET
        ).download(storage_path)

        return send_file(
            io.BytesIO(content),
            as_attachment=True,
            download_name=filename,
            mimetype="application/octet-stream"
        )

    except Exception:
        app.logger.exception("Supabase file download failed")

        return jsonify({
            "error": (
                "Could not download the file. "
                "Check the VS Code terminal."
            )
        }), 500


# --------------------------------------------------
# FILES: DELETE
# --------------------------------------------------

@app.route(
    "/api/files/<file_id>",
    methods=["DELETE"]
)
def delete_file(file_id):
    files_ref = get_user_files()

    if files_ref is None:
        return jsonify({
            "error": "Please log in first"
        }), 401

    doc_ref = files_ref.document(file_id)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify({
            "error": "File not found"
        }), 404

    item = doc.to_dict() or {}
    storage_path = item.get("storage_path")

    if not storage_path:
        return jsonify({
            "error": "File metadata is incomplete"
        }), 500

    try:
        # Delete the Storage object first.
        supabase.storage.from_(
            SUPABASE_STORAGE_BUCKET
        ).remove([storage_path])

        # Delete Firestore metadata only after Storage
        # deletion succeeds.
        doc_ref.delete()

        return jsonify({
            "message": "File deleted successfully"
        }), 200

    except Exception:
        app.logger.exception("Supabase file deletion failed")

        return jsonify({
            "error": (
                "Could not delete the file. "
                "Check the VS Code terminal."
            )
        }), 500


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
