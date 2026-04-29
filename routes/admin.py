from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pandas as pd
from bson import ObjectId
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from core.scheduler import generate_timetables, load_scheduling_data
from core.suggestions import suggest_fixes
from database.db import (
    get_departments_col,
    get_faculty_col,
    get_rooms_col,
    get_slots_col,
    get_subjects_col,
    get_users_col,
    get_variants_col,
)
from routes import DAYS, build_conflict_map, build_timetable_grid, compute_faculty_workload, format_recent_activity
from utils.decorators import role_required
from utils.export import export_to_excel


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _handle_delete(collection, item_id, label):
    try:
        collection.delete_one({"_id": ObjectId(item_id)})
        flash(f"{label} deleted successfully.", "success")
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")


def _allowed_excel(filename):
    return bool(filename) and filename.lower().endswith(".xlsx")


def _normalize_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _parse_list(value):
    return [item.strip() for item in str(value).split(",") if str(item).strip()]


def _bulk_upload_records(data_type, file_storage):
    inserted = 0
    skipped = []
    dataframe = pd.read_excel(BytesIO(file_storage.read()))
    dataframe = dataframe.where(pd.notnull(dataframe), "")

    dept_map = {item["code"].upper(): item for item in get_departments_col().find()}
    subject_map = {item["code"].upper(): item for item in get_subjects_col().find()}
    collection_map = {
        "faculty": get_faculty_col(),
        "rooms": get_rooms_col(),
        "subjects": get_subjects_col(),
    }
    required_columns = {
        "faculty": {
            "name",
            "email",
            "phone",
            "department_code",
            "subject_codes",
            "available_days",
            "max_hours_per_week",
            "avg_leaves_per_month",
        },
        "rooms": {"room_code", "capacity", "room_type", "has_projector", "department_code"},
        "subjects": {
            "name",
            "code",
            "department_code",
            "semester",
            "credits",
            "hours_per_week",
            "is_lab",
            "requires_projector",
        },
    }

    missing_columns = sorted(required_columns[data_type] - {str(col).strip() for col in dataframe.columns})
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    collection = collection_map[data_type]
    for index, row in dataframe.iterrows():
        row_num = index + 2
        try:
            if data_type == "faculty":
                department = dept_map.get(str(row["department_code"]).strip().upper())
                if not department:
                    raise ValueError("invalid department_code")
                subject_codes = [code.upper() for code in _parse_list(row["subject_codes"])]
                subject_ids = []
                for code in subject_codes:
                    subject_doc = subject_map.get(code)
                    if not subject_doc:
                        raise ValueError(f"unknown subject code {code}")
                    subject_ids.append(subject_doc["_id"])
                doc = {
                    "name": str(row["name"]).strip(),
                    "email": str(row["email"]).strip(),
                    "phone": str(row["phone"]).strip(),
                    "department_id": department["_id"],
                    "subject_ids": subject_ids,
                    "available_days": _parse_list(row["available_days"]),
                    "max_hours_per_week": int(row["max_hours_per_week"]),
                    "avg_leaves_per_month": int(row["avg_leaves_per_month"]),
                    "created_at": datetime.utcnow(),
                }
                if not doc["name"] or not doc["email"] or not doc["available_days"]:
                    raise ValueError("required faculty fields are blank")
            elif data_type == "rooms":
                department_code = str(row["department_code"]).strip().upper()
                department = dept_map.get(department_code) if department_code else None
                doc = {
                    "room_code": str(row["room_code"]).strip().upper(),
                    "capacity": int(row["capacity"]),
                    "room_type": str(row["room_type"]).strip().lower(),
                    "has_projector": _normalize_bool(row["has_projector"]),
                    "department_id": department["_id"] if department else None,
                    "created_at": datetime.utcnow(),
                }
                if not doc["room_code"]:
                    raise ValueError("room_code is blank")
                if doc["room_type"] not in {"classroom", "lab"}:
                    raise ValueError("room_type must be classroom or lab")
            else:
                department = dept_map.get(str(row["department_code"]).strip().upper())
                if not department:
                    raise ValueError("invalid department_code")
                doc = {
                    "name": str(row["name"]).strip(),
                    "code": str(row["code"]).strip().upper(),
                    "department_id": department["_id"],
                    "semester": int(row["semester"]),
                    "credits": int(row["credits"]),
                    "hours_per_week": int(row["hours_per_week"]),
                    "is_lab": _normalize_bool(row["is_lab"]),
                    "requires_projector": _normalize_bool(row["requires_projector"]),
                    "created_at": datetime.utcnow(),
                }
                if not doc["name"] or not doc["code"]:
                    raise ValueError("required subject fields are blank")

            collection.insert_one(doc)
            inserted += 1
        except Exception as exc:
            skipped.append(f"Row {row_num}: {str(exc)}")

    return inserted, skipped


def _prevalidate_generation_data(dept_id, semester):
    warnings = []
    try:
        subject_docs = list(get_subjects_col().find({"department_id": ObjectId(dept_id), "semester": int(semester)}))
        faculty_docs = list(get_faculty_col().find({"department_id": ObjectId(dept_id)}))
        room_count = get_rooms_col().count_documents(
            {
                "$or": [
                    {"department_id": ObjectId(dept_id)},
                    {"department_id": None},
                    {"department_id": {"$exists": False}},
                ]
            }
        )
        department = get_departments_col().find_one({"_id": ObjectId(dept_id)})
        shift = department["shift"] if department else "morning"
        slot_count = get_slots_col().count_documents({"shift": shift})
    except Exception as exc:
        return [f"Database error: {str(exc)}"]

    for subject in subject_docs:
        faculty_count = sum(
            1 for faculty in faculty_docs if any(str(subject["_id"]) == str(subject_id) for subject_id in faculty.get("subject_ids", []))
        )
        if faculty_count < 1:
            warnings.append(f"No faculty mapped for subject {subject['code']} - {subject['name']}.")
    if room_count < 1:
        warnings.append("At least one room must be available for the selected department.")
    if slot_count < 5:
        warnings.append("At least 5 time slots must be configured for the department shift.")
    if not subject_docs:
        warnings.append("No subjects found for the selected department and semester.")
    return warnings


def _store_variants(dept_id, semester, variants, batch_id, replace_existing=False):
    if replace_existing:
        get_variants_col().delete_many({"batch_id": batch_id})
    for index, variant in enumerate(variants, start=1):
        get_variants_col().insert_one(
            {
                "batch_id": batch_id,
                "variant_number": index,
                "department_id": ObjectId(dept_id),
                "semester": semester,
                "fitness_score": variant["fitness_score"],
                "clash_count": variant["clash_count"],
                "violations": variant["violations"],
                "status": "pending",
                "selected_by": None,
                "selected_at": None,
                "approved_by": None,
                "approved_at": None,
                "rejection_reason": None,
                "seed_used": variant["seed_used"],
                "created_at": datetime.utcnow(),
                "entries": [
                    {
                        "slot_id": ObjectId(entry["slot_id"]),
                        "day": entry["day"],
                        "period_number": entry["period_number"],
                        "start_time": entry["start_time"],
                        "end_time": entry["end_time"],
                        "subject_id": ObjectId(entry["subject_id"]),
                        "subject_name": entry["subject_name"],
                        "subject_code": entry["subject_code"],
                        "faculty_id": ObjectId(entry["faculty_id"]),
                        "faculty_name": entry["faculty_name"],
                        "room_id": ObjectId(entry["room_id"]),
                        "room_code": entry["room_code"],
                        "is_fixed": entry["is_fixed"],
                        "department_code": entry["department_code"],
                    }
                    for entry in variant["entries"]
                ],
            }
        )


def _build_analytics_payload(variant, faculty_docs, room_docs, slot_count):
    entries = variant.get("entries", []) if variant else []
    faculty_workload = compute_faculty_workload(entries, faculty_docs)
    faculty_chart = {
        "labels": [item["name"] for item in faculty_workload],
        "values": [item["hours"] for item in faculty_workload],
        "limits": [item["max_hours"] for item in faculty_workload],
    }

    room_usage = {}
    relevant_room_codes = set()
    for room in room_docs:
        relevant_room_codes.add(room["room_code"])
        room_usage[room["room_code"]] = 0
    for entry in entries:
        room_usage.setdefault(entry["room_code"], 0)
        room_usage[entry["room_code"]] += 1
        relevant_room_codes.add(entry["room_code"])
    room_labels = []
    room_values = []
    for room in room_docs:
        if room["room_code"] not in relevant_room_codes:
            continue
        room_labels.append(room["room_code"])
        utilization = round((room_usage.get(room["room_code"], 0) / max(slot_count, 1)) * 100, 2)
        room_values.append(utilization)

    subject_counts = {}
    for entry in entries:
        subject_counts[entry["subject_name"]] = subject_counts.get(entry["subject_name"], 0) + 1
    subject_chart = {
        "labels": list(subject_counts.keys()),
        "values": list(subject_counts.values()),
    }

    conflict_slot_ids = {str(item.get("slot")) for item in variant.get("violations", []) if item.get("slot")}
    conflict_assignments = sum(1 for entry in entries if str(entry["slot_id"]) in conflict_slot_ids)
    conflict_free_assignments = max(len(entries) - conflict_assignments, 0)
    conflict_chart = {
        "labels": ["Conflict-free", "Conflicts"],
        "values": [conflict_free_assignments, conflict_assignments],
    }

    return {
        "faculty": faculty_chart,
        "rooms": {"labels": room_labels, "values": room_values},
        "subjects": subject_chart,
        "conflicts": conflict_chart,
        "summary": {
            "entries": len(entries),
            "violations": len(variant.get("violations", [])) if variant else 0,
            "fitness": round(variant.get("fitness_score", 0), 2) if variant else 0,
        },
    }


@admin_bp.route("/dashboard")
@login_required
@role_required("admin", "superadmin")
def dashboard():
    try:
        faculty_count = get_faculty_col().count_documents({})
        room_count = get_rooms_col().count_documents({})
        subject_count = get_subjects_col().count_documents({})
        pending_approvals = get_variants_col().count_documents({"status": "selected"})
        last_variant = get_variants_col().find_one(sort=[("created_at", -1)])
        recent_variants = list(get_variants_col().find().sort("created_at", -1).limit(5))
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        faculty_count = room_count = subject_count = pending_approvals = 0
        last_variant = None
        recent_variants = []

    return render_template(
        "admin/dashboard.html",
        faculty_count=faculty_count,
        room_count=room_count,
        subject_count=subject_count,
        pending_approvals=pending_approvals,
        last_status=last_variant["status"] if last_variant else "Not generated yet",
        recent_activity=format_recent_activity(recent_variants),
    )


@admin_bp.route("/departments", methods=["GET", "POST"])
@login_required
@role_required("admin", "superadmin")
def departments():
    collection = get_departments_col()
    if request.method == "POST":
        if request.form.get("_method") == "delete":
            dept_id = request.form.get("dept_id", "")
            if dept_id:
                _handle_delete(collection, dept_id, "Department")
            return redirect(url_for("admin.departments"))

        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()
        shift = request.form.get("shift", "").strip()
        if not name:
            flash("Department name is required.", "danger")
            return redirect(request.url)
        if not code:
            flash("Department code is required.", "danger")
            return redirect(request.url)
        if shift not in {"morning", "evening"}:
            flash("Shift must be morning or evening.", "danger")
            return redirect(request.url)
        try:
            collection.insert_one({"name": name, "code": code, "shift": shift, "created_at": datetime.utcnow()})
            flash("Department added successfully.", "success")
        except Exception as exc:
            flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("admin.departments"))

    try:
        departments_list = list(collection.find().sort("code", 1))
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        departments_list = []
    return render_template("admin/departments.html", departments=departments_list)


@admin_bp.route("/faculty", methods=["GET", "POST"])
@login_required
@role_required("admin", "superadmin")
def faculty():
    dept_col = get_departments_col()
    subject_col = get_subjects_col()
    fac_col = get_faculty_col()
    if request.method == "POST":
        if request.form.get("_method") == "delete":
            faculty_id = request.form.get("faculty_id", "")
            if faculty_id:
                _handle_delete(fac_col, faculty_id, "Faculty")
            return redirect(url_for("admin.faculty"))

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        department_id = request.form.get("department_id", "").strip()
        subject_ids = request.form.getlist("subject_ids")
        available_days = request.form.getlist("available_days")
        try:
            max_hours = int(request.form.get("max_hours_per_week", 20))
            avg_leaves = int(request.form.get("avg_leaves_per_month", 2))
        except ValueError:
            flash("Max hours and average leaves must be valid numbers.", "danger")
            return redirect(request.url)

        if not name or not email or not phone or not department_id:
            flash("Name, email, phone, and department are required.", "danger")
            return redirect(request.url)
        if not subject_ids:
            flash("Please select at least one subject.", "danger")
            return redirect(request.url)
        if not available_days:
            flash("Please select at least one available day.", "danger")
            return redirect(request.url)
        try:
            fac_col.insert_one(
                {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "department_id": ObjectId(department_id),
                    "subject_ids": [ObjectId(subject_id) for subject_id in subject_ids],
                    "available_days": available_days,
                    "max_hours_per_week": max_hours,
                    "avg_leaves_per_month": avg_leaves,
                    "created_at": datetime.utcnow(),
                }
            )
            flash("Faculty added successfully.", "success")
        except Exception as exc:
            flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("admin.faculty"))

    try:
        departments_list = list(dept_col.find().sort("code", 1))
        subjects = list(subject_col.find().sort("code", 1))
        faculty_list = list(fac_col.find().sort("name", 1))
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        departments_list = subjects = faculty_list = []

    dept_map = {str(item["_id"]): item["code"] for item in departments_list}
    subject_map = {str(item["_id"]): item["name"] for item in subjects}
    return render_template(
        "admin/faculty.html",
        faculty_list=faculty_list,
        departments=departments_list,
        subjects=subjects,
        dept_map=dept_map,
        subject_map=subject_map,
        days=DAYS,
    )


@admin_bp.route("/upload/<data_type>", methods=["POST"])
@login_required
@role_required("admin", "superadmin")
def upload_excel(data_type):
    if data_type not in {"faculty", "rooms", "subjects"}:
        flash("Unsupported upload type.", "danger")
        return redirect(url_for("admin.dashboard"))

    file_storage = request.files.get("excel_file")
    if not file_storage or not file_storage.filename:
        flash("Excel file is required.", "danger")
        return redirect(request.referrer or url_for("admin.dashboard"))
    if not _allowed_excel(file_storage.filename):
        flash("Only .xlsx files are supported.", "danger")
        return redirect(request.referrer or url_for("admin.dashboard"))

    try:
        inserted, skipped = _bulk_upload_records(data_type, file_storage)
        flash(f"{inserted} {data_type} rows inserted successfully.", "success")
        if skipped:
            flash(f"{len(skipped)} rows skipped: {' | '.join(skipped[:5])}", "warning")
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.route("/rooms", methods=["GET", "POST"])
@login_required
@role_required("admin", "superadmin")
def rooms():
    room_col = get_rooms_col()
    dept_col = get_departments_col()
    if request.method == "POST":
        if request.form.get("_method") == "delete":
            room_id = request.form.get("room_id", "")
            if room_id:
                _handle_delete(room_col, room_id, "Room")
            return redirect(url_for("admin.rooms"))

        room_code = request.form.get("room_code", "").strip().upper()
        department_id = request.form.get("department_id", "").strip()
        room_type = request.form.get("room_type", "").strip()
        has_projector = bool(request.form.get("has_projector"))
        try:
            capacity = int(request.form.get("capacity", "0"))
        except ValueError:
            flash("Capacity must be a valid number.", "danger")
            return redirect(request.url)

        if not room_code:
            flash("Room code is required.", "danger")
            return redirect(request.url)
        if capacity <= 0:
            flash("Capacity must be greater than zero.", "danger")
            return redirect(request.url)
        if room_type not in {"classroom", "lab"}:
            flash("Room type must be classroom or lab.", "danger")
            return redirect(request.url)
        room_doc = {
            "room_code": room_code,
            "capacity": capacity,
            "room_type": room_type,
            "has_projector": has_projector,
            "created_at": datetime.utcnow(),
        }
        if department_id:
            room_doc["department_id"] = ObjectId(department_id)
        else:
            room_doc["department_id"] = None
        try:
            room_col.insert_one(room_doc)
            flash("Room added successfully.", "success")
        except Exception as exc:
            flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("admin.rooms"))

    try:
        departments_list = list(dept_col.find().sort("code", 1))
        rooms_list = list(room_col.find().sort("room_code", 1))
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        departments_list = rooms_list = []
    dept_map = {str(item["_id"]): item["code"] for item in departments_list}
    return render_template("admin/rooms.html", rooms_list=rooms_list, departments=departments_list, dept_map=dept_map)


@admin_bp.route("/subjects", methods=["GET", "POST"])
@login_required
@role_required("admin", "superadmin")
def subjects():
    subject_col = get_subjects_col()
    dept_col = get_departments_col()
    if request.method == "POST":
        if request.form.get("_method") == "delete":
            subject_id = request.form.get("subject_id", "")
            if subject_id:
                _handle_delete(subject_col, subject_id, "Subject")
            return redirect(url_for("admin.subjects"))

        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()
        department_id = request.form.get("department_id", "").strip()
        try:
            semester = int(request.form.get("semester", "0"))
            credits = int(request.form.get("credits", "0"))
            hours_per_week = int(request.form.get("hours_per_week", "0"))
        except ValueError:
            flash("Semester, credits, and hours per week must be valid numbers.", "danger")
            return redirect(request.url)
        if not name or not code or not department_id:
            flash("Subject name, code, and department are required.", "danger")
            return redirect(request.url)
        if semester not in range(1, 9):
            flash("Semester must be between 1 and 8.", "danger")
            return redirect(request.url)
        try:
            subject_col.insert_one(
                {
                    "name": name,
                    "code": code,
                    "department_id": ObjectId(department_id),
                    "semester": semester,
                    "credits": credits,
                    "hours_per_week": hours_per_week,
                    "is_lab": bool(request.form.get("is_lab")),
                    "requires_projector": bool(request.form.get("requires_projector")),
                    "created_at": datetime.utcnow(),
                }
            )
            flash("Subject added successfully.", "success")
        except Exception as exc:
            flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("admin.subjects"))

    try:
        departments_list = list(dept_col.find().sort("code", 1))
        subjects_list = list(subject_col.find().sort([("semester", 1), ("code", 1)]))
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        departments_list = subjects_list = []
    dept_map = {str(item["_id"]): item["code"] for item in departments_list}
    return render_template("admin/subjects.html", subjects_list=subjects_list, departments=departments_list, dept_map=dept_map)


@admin_bp.route("/timeslots", methods=["GET", "POST"])
@login_required
@role_required("admin", "superadmin")
def timeslots():
    slot_col = get_slots_col()
    subject_col = get_subjects_col()
    if request.method == "POST":
        if request.form.get("_method") == "delete":
            slot_id = request.form.get("slot_id", "")
            if slot_id:
                _handle_delete(slot_col, slot_id, "Time slot")
            return redirect(url_for("admin.timeslots"))

        day = request.form.get("day", "").strip()
        shift = request.form.get("shift", "").strip()
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()
        fixed_subject_id = request.form.get("fixed_subject_id", "").strip()
        try:
            period_number = int(request.form.get("period_number", "0"))
        except ValueError:
            flash("Period number must be a valid number.", "danger")
            return redirect(request.url)

        if day not in DAYS:
            flash("Please select a valid day.", "danger")
            return redirect(request.url)
        if period_number <= 0:
            flash("Period number must be greater than zero.", "danger")
            return redirect(request.url)
        if not start_time or not end_time:
            flash("Start time and end time are required.", "danger")
            return redirect(request.url)
        if shift not in {"morning", "evening"}:
            flash("Shift must be morning or evening.", "danger")
            return redirect(request.url)

        slot_doc = {
            "day": day,
            "period_number": period_number,
            "start_time": start_time,
            "end_time": end_time,
            "shift": shift,
            "is_fixed": bool(request.form.get("is_fixed")),
            "fixed_subject_id": ObjectId(fixed_subject_id) if fixed_subject_id else None,
            "created_at": datetime.utcnow(),
        }
        try:
            slot_col.insert_one(slot_doc)
            flash("Time slot added successfully.", "success")
        except Exception as exc:
            flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("admin.timeslots"))

    try:
        slots = list(slot_col.find().sort([("day", 1), ("period_number", 1)]))
        subjects = list(subject_col.find().sort("code", 1))
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        slots = subjects = []
    return render_template("admin/timeslots.html", slots=slots, subjects=subjects, days=DAYS)


@admin_bp.route("/generate", methods=["GET", "POST"])
@login_required
@role_required("admin", "superadmin")
def generate():
    try:
        departments = list(get_departments_col().find().sort("code", 1))
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        departments = []

    if request.method == "POST":
        dept_id = request.form.get("dept_id", "").strip()
        semester = request.form.get("semester", "").strip()
        existing_batch_id = request.form.get("batch_id", "").strip()
        if not dept_id or not semester:
            flash("Department and semester are required.", "danger")
            return redirect(request.url)
        try:
            semester = int(semester)
        except ValueError:
            flash("Semester must be a valid number.", "danger")
            return redirect(request.url)

        warnings = _prevalidate_generation_data(dept_id, semester)
        if warnings:
            flash("Cannot generate timetable until validation issues are resolved.", "warning")
            for warning in warnings:
                flash(warning, "warning")
            return redirect(request.referrer or request.url)

        seed_offset = int(datetime.utcnow().timestamp()) % 100000
        current_app.logger.info(
            "Timetable generation requested | dept=%s semester=%s batch=%s",
            dept_id,
            semester,
            existing_batch_id or "new",
        )
        try:
            variants = generate_timetables(
                dept_id,
                semester,
                current_app.config["MAX_TIMETABLE_VARIANTS"],
                seed_offset=seed_offset,
            )
        except Exception as exc:
            current_app.logger.exception("Timetable generation failed | dept=%s semester=%s", dept_id, semester)
            flash(f"Timetable generation failed: {str(exc)}", "danger")
            return redirect(url_for("admin.dashboard"))

        batch_id = existing_batch_id or str(uuid4())
        try:
            _store_variants(dept_id, semester, variants, batch_id, replace_existing=bool(existing_batch_id))
            current_app.logger.info(
                "Timetable generation complete | dept=%s semester=%s scores=%s",
                dept_id,
                semester,
                [round(item["fitness_score"], 2) for item in variants],
            )
            flash(
                "Timetable variants generated successfully." if not existing_batch_id else "Timetable variants regenerated successfully.",
                "success",
            )
        except Exception as exc:
            current_app.logger.exception("Timetable persistence failed | dept=%s semester=%s", dept_id, semester)
            flash(f"Database error: {str(exc)}", "danger")
            return redirect(url_for("admin.generate"))

        return redirect(url_for("admin.variants", batch_id=batch_id))

    return render_template("admin/generate.html", departments=departments)


@admin_bp.route("/validate-data")
@login_required
@role_required("admin", "superadmin")
def validate_data():
    dept_id = request.args.get("dept_id", "").strip()
    semester = request.args.get("semester", "").strip()
    if not dept_id or not semester:
        return jsonify({"valid": False, "warnings": ["Department and semester are required."]})
    try:
        semester = int(semester)
    except ValueError:
        return jsonify({"valid": False, "warnings": ["Semester must be numeric."]})

    warnings = _prevalidate_generation_data(dept_id, semester)
    return jsonify({"valid": len(warnings) == 0, "warnings": warnings})


@admin_bp.route("/variants/<batch_id>")
@login_required
@role_required("admin", "superadmin")
def variants(batch_id):
    try:
        variants_list = list(get_variants_col().find({"batch_id": batch_id}).sort("variant_number", 1))
        departments = list(get_departments_col().find())
        data = None
        suggestions = []
        if variants_list:
            data = load_scheduling_data(str(variants_list[0]["department_id"]), variants_list[0]["semester"])
            data["faculty_docs"] = list(get_faculty_col().find({"department_id": variants_list[0]["department_id"]}))
            data["room_docs"] = list(get_rooms_col().find())
            data["subject_docs"] = list(get_subjects_col().find({"department_id": variants_list[0]["department_id"]}))
            data["slot_docs"] = list(get_slots_col().find())
            if all(item["clash_count"] > 0 for item in variants_list):
                suggestions = suggest_fixes(variants_list[0]["violations"], data)
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        variants_list = []
        departments = []
        suggestions = []

    dept_map = {str(item["_id"]): item for item in departments}
    variant_views = []
    for variant in variants_list:
        grid, periods, period_times = build_timetable_grid(variant["entries"])
        variant_views.append(
            {
                "doc": variant,
                "grid": grid,
                "periods": periods[:3],
                "period_times": period_times,
                "department": dept_map.get(str(variant["department_id"])),
                "conflict_map": build_conflict_map(variant.get("violations", [])),
            }
        )
    batch_meta = variants_list[0] if variants_list else None
    return render_template(
        "admin/variants.html",
        variants=variant_views,
        suggestions=suggestions,
        days=DAYS[:3],
        batch_meta=batch_meta,
    )


@admin_bp.route("/timetable/<variant_id>")
@login_required
@role_required("admin", "superadmin")
def timetable_view(variant_id):
    try:
        variant = get_variants_col().find_one({"_id": ObjectId(variant_id)})
        if not variant:
            flash("Timetable not found.", "danger")
            return redirect(url_for("admin.dashboard"))
        department = get_departments_col().find_one({"_id": variant["department_id"]})
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("admin.dashboard"))

    grid, periods, period_times = build_timetable_grid(variant["entries"])
    conflict_map = build_conflict_map(variant.get("violations", []))
    return render_template(
        "admin/timetable_view.html",
        variant=variant,
        grid=grid,
        periods=periods,
        period_times=period_times,
        days=DAYS,
        department=department,
        conflict_map=conflict_map,
    )


@admin_bp.route("/select/<variant_id>", methods=["POST"])
@login_required
@role_required("admin", "superadmin")
def select_variant(variant_id):
    try:
        get_variants_col().update_one(
            {"_id": ObjectId(variant_id)},
            {
                "$set": {
                    "status": "selected",
                    "selected_by": ObjectId(current_user.id),
                    "selected_at": datetime.utcnow(),
                }
            },
        )
        flash("Sent for HOD approval", "success")
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/export/<variant_id>")
@login_required
@role_required("admin", "superadmin")
def export_variant(variant_id):
    try:
        variant = get_variants_col().find_one({"_id": ObjectId(variant_id)})
        if not variant:
            flash("Timetable not found.", "danger")
            return redirect(url_for("admin.dashboard"))
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("admin.dashboard"))

    try:
        filepath = export_to_excel(variant)
        return send_file(filepath, as_attachment=True)
    except Exception:
        flash("Export failed. Please try again.", "danger")
        return redirect(request.url)


@admin_bp.route("/analytics")
@login_required
@role_required("admin", "superadmin")
def analytics():
    analytics_data = {
        "faculty": {"labels": [], "values": [], "limits": []},
        "rooms": {"labels": [], "values": []},
        "subjects": {"labels": [], "values": []},
        "conflicts": {"labels": ["Conflict-free", "Conflicts"], "values": [0, 0]},
        "summary": {"entries": 0, "violations": 0, "fitness": 0},
    }
    variant = None
    try:
        variant = get_variants_col().find_one({"status": {"$in": ["approved", "selected"]}}, sort=[("created_at", -1)])
        if variant:
            department = get_departments_col().find_one({"_id": variant["department_id"]})
            shift = department["shift"] if department else "morning"
            faculty_docs = list(get_faculty_col().find({"department_id": variant["department_id"]}))
            room_docs = list(
                get_rooms_col().find(
                    {
                        "$or": [
                            {"department_id": variant["department_id"]},
                            {"department_id": None},
                            {"department_id": {"$exists": False}},
                        ]
                    }
                )
            )
            slot_count = get_slots_col().count_documents({"shift": shift})
            analytics_data = _build_analytics_payload(variant, faculty_docs, room_docs, slot_count)
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        current_app.logger.exception("Analytics build failed")

    return render_template(
        "admin/analytics.html",
        analytics_data=analytics_data,
        variant=variant,
    )
