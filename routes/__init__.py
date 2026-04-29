from collections import defaultdict


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def build_timetable_grid(entries):
    period_map = defaultdict(dict)
    periods = {}
    for entry in entries:
        period_map[entry["period_number"]][entry["day"]] = entry
        periods[entry["period_number"]] = f"{entry['start_time']}-{entry['end_time']}"
    ordered_periods = sorted(period_map.keys())
    return period_map, ordered_periods, periods


def build_conflict_map(violations):
    conflict_map = defaultdict(list)
    for violation in violations or []:
        slot = violation.get("slot")
        if slot:
            conflict_map[str(slot)].append(violation.get("message", "Conflict detected"))
    return dict(conflict_map)


def compute_faculty_workload(entries, faculty_docs=None):
    faculty_docs = faculty_docs or []
    faculty_meta = {str(item["_id"]): item for item in faculty_docs}
    workload = defaultdict(lambda: {"name": "", "email": "", "hours": 0, "max_hours": 20})
    for entry in entries:
        faculty_id = str(entry["faculty_id"])
        meta = faculty_meta.get(faculty_id, {})
        workload[faculty_id]["name"] = entry["faculty_name"]
        workload[faculty_id]["email"] = meta.get("email", "")
        workload[faculty_id]["hours"] += 1
        workload[faculty_id]["max_hours"] = meta.get("max_hours_per_week", 20)
    return sorted(workload.values(), key=lambda item: item["name"])


def format_recent_activity(variants):
    activity = []
    for item in variants:
        activity.append(
            {
                "department_code": item.get("department_code", ""),
                "semester": item.get("semester"),
                "status": item.get("status", "pending"),
                "fitness_score": round(item.get("fitness_score", 0), 2),
                "created_at": item.get("created_at"),
                "variant_id": str(item["_id"]),
            }
        )
    return activity
