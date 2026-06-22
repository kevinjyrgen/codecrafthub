"""
CodeCraftHub — Personalized Learning Platform (Backend API)
Flask REST API with full CRUD over /api/courses, backed by a JSON text file.
No database, no authentication.
"""

import json
import os
from datetime import datetime
from threading import Lock

from flask import Flask, jsonify, request
from flask_cors import CORS

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
DATA_FILE = os.path.join(os.path.dirname(__file__), "courses.json")
VALID_STATUSES = ("Not Started", "In Progress", "Completed")

app = Flask(__name__)
CORS(app)  # Allow the browser-based Bolt dashboard (Part 2) to call the API.

_file_lock = Lock()  # Serialize writes to the JSON file.


# --------------------------------------------------------------------------- #
# Storage helpers
# --------------------------------------------------------------------------- #
def load_courses():
    """Read all courses from the JSON file. Returns [] if missing/empty."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_courses(courses):
    """Persist the full course list (atomic write)."""
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(courses, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)


def get_next_id(courses):
    """Auto-increment integer ID (max existing + 1, starting at 1)."""
    return max((c.get("id", 0) for c in courses), default=0) + 1


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------- #
# Response + validation helpers
# --------------------------------------------------------------------------- #
def ok(data, status=200):
    return jsonify({"success": True, "data": data}), status


def err(message, status=400, details=None):
    body = {"success": False, "error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def validate_payload(payload, partial=False):
    """
    Validate a course payload. Returns (cleaned_dict, errors_list).
    partial=True (PUT) allows omitting required fields.
    """
    if not isinstance(payload, dict):
        return {}, ["Request body must be a JSON object."]

    errors, cleaned = [], {}

    # Required: name
    if "name" in payload:
        if not isinstance(payload["name"], str) or not payload["name"].strip():
            errors.append("'name' must be a non-empty string.")
        else:
            cleaned["name"] = payload["name"].strip()
    elif not partial:
        errors.append("'name' is required.")

    # Optional: description
    if "description" in payload:
        if not isinstance(payload["description"], str):
            errors.append("'description' must be a string.")
        else:
            cleaned["description"] = payload["description"].strip()

    # Optional: target_date (YYYY-MM-DD)
    if "target_date" in payload:
        value = payload["target_date"]
        if value in (None, ""):
            cleaned["target_date"] = ""
        elif not isinstance(value, str):
            errors.append("'target_date' must be a string (YYYY-MM-DD).")
        else:
            try:
                datetime.strptime(value, "%Y-%m-%d")
                cleaned["target_date"] = value
            except ValueError:
                errors.append("'target_date' must be in YYYY-MM-DD format.")

    # Optional: status enum
    if "status" in payload:
        if payload["status"] not in VALID_STATUSES:
            errors.append(f"'status' must be one of {list(VALID_STATUSES)}.")
        else:
            cleaned["status"] = payload["status"]

    return cleaned, errors


# --------------------------------------------------------------------------- #
# Routes — static sub-paths declared before the <int:id> route
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return ok({"status": "up", "time": now()})


@app.get("/api/courses/stats")
def stats():
    courses = load_courses()
    by_status = {s: 0 for s in VALID_STATUSES}
    for c in courses:
        s = c.get("status", "Not Started")
        by_status[s] = by_status.get(s, 0) + 1
    return ok({"total_courses": len(courses), "by_status": by_status})


@app.get("/api/courses/search")
def search_courses():
    term = (request.args.get("q") or "").strip().lower()
    courses = load_courses()
    if term:
        courses = [
            c for c in courses
            if term in c.get("name", "").lower()
            or term in c.get("description", "").lower()
        ]
    return ok(courses)


@app.get("/api/courses")
def list_courses():
    return ok(load_courses())


@app.get("/api/courses/<int:course_id>")
def get_course(course_id):
    course = next((c for c in load_courses() if c.get("id") == course_id), None)
    if course is None:
        return err("Course not found.", 404)
    return ok(course)


@app.post("/api/courses")
def create_course():
    payload = request.get_json(silent=True)
    if payload is None:
        return err("Request body must be valid JSON.", 400)

    cleaned, errors = validate_payload(payload, partial=False)
    if errors:
        return err("Validation failed.", 422, errors)

    with _file_lock:
        courses = load_courses()
        course = {
            "id": get_next_id(courses),
            "name": cleaned["name"],
            "description": cleaned.get("description", ""),
            "target_date": cleaned.get("target_date", ""),
            "status": cleaned.get("status", "Not Started"),
            "created_at": now(),
        }
        courses.append(course)
        save_courses(courses)

    return ok(course, 201)


@app.put("/api/courses/<int:course_id>")
def update_course(course_id):
    payload = request.get_json(silent=True)
    if payload is None:
        return err("Request body must be valid JSON.", 400)

    cleaned, errors = validate_payload(payload, partial=True)
    if errors:
        return err("Validation failed.", 422, errors)
    if not cleaned:
        return err("No valid fields provided to update.", 422)

    with _file_lock:
        courses = load_courses()
        idx = next(
            (i for i, c in enumerate(courses) if c.get("id") == course_id), None
        )
        if idx is None:
            return err("Course not found.", 404)
        courses[idx].update(cleaned)
        updated = courses[idx]
        save_courses(courses)

    return ok(updated)


@app.delete("/api/courses/<int:course_id>")
def delete_course(course_id):
    with _file_lock:
        courses = load_courses()
        remaining = [c for c in courses if c.get("id") != course_id]
        if len(remaining) == len(courses):
            return err("Course not found.", 404)
        save_courses(remaining)

    return ok({"deleted": course_id})


# --------------------------------------------------------------------------- #
# Error handlers — consistent JSON even on framework errors
# --------------------------------------------------------------------------- #
@app.errorhandler(404)
def not_found(_):
    return err("Resource not found.", 404)


@app.errorhandler(405)
def method_not_allowed(_):
    return err("Method not allowed.", 405)


@app.errorhandler(500)
def server_error(_):
    return err("Internal server error.", 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
