from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

# --------------------------------------------------
# Project Paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from .detect import detect
except ImportError:  # Supports running this file directly as ``python app.py``.
    from detect import detect

FRONTEND_FOLDER = PROJECT_ROOT / "frontend"
UPLOAD_FOLDER = PROJECT_ROOT / "uploads"

UPLOAD_FOLDER.mkdir(exist_ok=True)

# --------------------------------------------------
# Flask App
# --------------------------------------------------

app = Flask(
    __name__,
    static_folder=str(FRONTEND_FOLDER),
    static_url_path=""
)

# --------------------------------------------------
# Frontend Routes
# --------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(FRONTEND_FOLDER, "index.html")


@app.route("/style.css")
def style():
    return send_from_directory(FRONTEND_FOLDER, "style.css")


@app.route("/script.js")
def script():
    return send_from_directory(FRONTEND_FOLDER, "script.js")


# --------------------------------------------------
# Detect API
# --------------------------------------------------

@app.route("/detect", methods=["POST"])
def detect_qr():

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No file uploaded."
        }), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({
            "success": False,
            "error": "No file selected."
        }), 400

    filename = secure_filename(file.filename)
    filepath = UPLOAD_FOLDER / filename

    file.save(filepath)

    try:

        result = detect(filepath)

        return jsonify(result)

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    finally:

        if filepath.exists():
            filepath.unlink()


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
