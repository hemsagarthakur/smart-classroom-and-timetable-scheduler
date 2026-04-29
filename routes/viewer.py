from bson import ObjectId
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from database.db import get_departments_col, get_variants_col
from routes import DAYS, build_conflict_map, build_timetable_grid
from utils.decorators import role_required


viewer_bp = Blueprint("viewer", __name__, url_prefix="/viewer")


@viewer_bp.route("/timetables")
@login_required
@role_required("viewer", "admin", "hod", "superadmin")
def timetables():
    try:
        variants = list(get_variants_col().find({"status": "approved"}).sort("approved_at", -1))
        departments = {str(item["_id"]): item for item in get_departments_col().find()}
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        variants = []
        departments = {}
    return render_template("viewer/timetables.html", variants=variants, departments=departments)


@viewer_bp.route("/timetable/<variant_id>")
@login_required
@role_required("viewer", "admin", "hod", "superadmin")
def timetable_view(variant_id):
    try:
        variant = get_variants_col().find_one({"_id": ObjectId(variant_id), "status": "approved"})
        if not variant:
            flash("Approved timetable not found.", "danger")
            return redirect(url_for("viewer.timetables"))
        department = get_departments_col().find_one({"_id": variant["department_id"]})
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("viewer.timetables"))

    grid, periods, period_times = build_timetable_grid(variant["entries"])
    conflict_map = build_conflict_map(variant.get("violations", []))
    return render_template(
        "viewer/timetable_view.html",
        variant=variant,
        grid=grid,
        periods=periods,
        period_times=period_times,
        days=DAYS,
        department=department,
        conflict_map=conflict_map,
    )
