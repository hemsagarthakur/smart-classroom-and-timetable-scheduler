from bson import ObjectId
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from database.db import get_variants_col
from routes import DAYS, build_conflict_map, build_timetable_grid
from utils.decorators import role_required


faculty_bp = Blueprint("faculty_portal", __name__, url_prefix="/faculty")


@faculty_bp.route("/timetable")
@login_required
@role_required("faculty")
def timetable():
    if not current_user.faculty_id:
        flash("Faculty account is not linked to a faculty record.", "danger")
        return redirect(url_for("auth.login"))

    try:
        variant = get_variants_col().find_one(
            {"status": "approved", "entries.faculty_id": ObjectId(current_user.faculty_id)},
            sort=[("approved_at", -1)],
        )
        if not variant:
            flash("No approved timetable is available yet.", "warning")
            return render_template(
                "faculty/timetable.html",
                variant=None,
                grid={},
                periods=[],
                period_times={},
                days=DAYS,
                conflict_map={},
            )
        faculty_entries = [entry for entry in variant["entries"] if str(entry["faculty_id"]) == str(current_user.faculty_id)]
    except Exception as exc:
        flash(f"Database error: {str(exc)}", "danger")
        return redirect(url_for("auth.login"))

    grid, periods, period_times = build_timetable_grid(faculty_entries)
    conflict_map = build_conflict_map(variant.get("violations", []))
    return render_template(
        "faculty/timetable.html",
        variant=variant,
        grid=grid,
        periods=periods,
        period_times=period_times,
        days=DAYS,
        conflict_map=conflict_map,
    )
