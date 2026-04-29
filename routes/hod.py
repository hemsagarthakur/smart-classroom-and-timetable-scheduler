from datetime import datetime

from bson import ObjectId
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database.db import get_departments_col, get_faculty_col, get_variants_col
from routes import DAYS, build_conflict_map, build_timetable_grid, compute_faculty_workload
from utils.decorators import role_required


hod_bp = Blueprint("hod", __name__, url_prefix="/hod")


def _hod_variant_filter():
    if current_user.role == "superadmin":
        return {}
    if current_user.department_id:
        return {"department_id": ObjectId(current_user.department_id)}
    return {"_id": None}


@hod_bp.route("/dashboard")
@login_required
@role_required("hod", "superadmin")
def dashboard():
    base_filter = _hod_variant_filter()
    try:
        pending_filter = dict(base_filter)
        pending_filter["status"] = "selected"
        past_filter = dict(base_filter)
        past_filter["status"] = {"$in": ["approved", "rejected"]}
        pending = list(get_variants_col().find(pending_filter).sort("created_at", -1))
        decisions = list(get_variants_col().find(past_filter).sort("created_at", -1))
        departments = {str(item["_id"]): item for item in get_departments_col().find()}
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        pending = decisions = []
        departments = {}
    return render_template("hod/dashboard.html", pending=pending, decisions=decisions, departments=departments)


@hod_bp.route("/review/<variant_id>")
@login_required
@role_required("hod", "superadmin")
def review(variant_id):
    try:
        variant = get_variants_col().find_one({"_id": ObjectId(variant_id)})
        if not variant:
            flash("Timetable not found.", "danger")
            return redirect(url_for("hod.dashboard"))
        if current_user.role == "hod" and str(variant["department_id"]) != str(current_user.department_id):
            flash("You are not authorized to review this timetable.", "danger")
            return redirect(url_for("hod.dashboard"))
        faculty_docs = list(get_faculty_col().find({"department_id": variant["department_id"]}))
        department = get_departments_col().find_one({"_id": variant["department_id"]})
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("hod.dashboard"))

    grid, periods, period_times = build_timetable_grid(variant["entries"])
    workload = compute_faculty_workload(variant["entries"], faculty_docs)
    conflict_map = build_conflict_map(variant.get("violations", []))
    return render_template(
        "hod/review.html",
        variant=variant,
        grid=grid,
        periods=periods,
        period_times=period_times,
        days=DAYS,
        workload=workload,
        department=department,
        conflict_map=conflict_map,
    )


@hod_bp.route("/approve/<variant_id>", methods=["POST"])
@login_required
@role_required("hod", "superadmin")
def approve(variant_id):
    try:
        get_variants_col().update_one(
            {"_id": ObjectId(variant_id)},
            {
                "$set": {
                    "status": "approved",
                    "approved_by": ObjectId(current_user.id),
                    "approved_at": datetime.utcnow(),
                }
            },
        )
        flash("Timetable approved successfully.", "success")
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
    return redirect(url_for("hod.dashboard"))


@hod_bp.route("/reject/<variant_id>", methods=["POST"])
@login_required
@role_required("hod", "superadmin")
def reject(variant_id):
    reason = request.form.get("rejection_reason", "").strip()
    if not reason:
        flash("Rejection reason is required.", "danger")
        return redirect(url_for("hod.review", variant_id=variant_id))
    try:
        get_variants_col().update_one(
            {"_id": ObjectId(variant_id)},
            {"$set": {"status": "rejected", "rejection_reason": reason, "approved_at": datetime.utcnow()}},
        )
        flash("Timetable rejected successfully.", "warning")
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
    return redirect(url_for("hod.dashboard"))


@hod_bp.route("/rejected")
@login_required
@role_required("hod", "superadmin")
def rejected():
    query = _hod_variant_filter()
    query["status"] = "rejected"
    try:
        variants = list(get_variants_col().find(query).sort("created_at", -1))
        departments = {str(item["_id"]): item for item in get_departments_col().find()}
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        variants = []
        departments = {}
    return render_template("hod/rejected.html", variants=variants, departments=departments)
