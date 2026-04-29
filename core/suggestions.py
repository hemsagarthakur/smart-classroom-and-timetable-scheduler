from collections import defaultdict


def analyze_violations(violations, data):
    grouped = defaultdict(list)
    for violation in violations:
        grouped[violation["type"]].append(violation)
    return dict(grouped)


def suggest_fixes(violations, data):
    suggestions = []
    grouped = analyze_violations(violations, data)
    faculty_map = {str(item["_id"]): item for item in data.get("faculty_docs", [])}
    room_map = {str(item["_id"]): item for item in data.get("room_docs", [])}
    subject_map = {str(item["_id"]): item for item in data.get("subject_docs", [])}
    slot_map = {str(item["_id"]): item for item in data.get("slot_docs", [])}

    for violation in grouped.get("faculty_clash", []):
        slot = slot_map.get(str(violation.get("slot")))
        if slot:
            suggestions.append(
                f"Faculty clash: A faculty member is double-booked on {slot['day']} at {slot['start_time']}-{slot['end_time']}. Consider moving one class to another free slot for that teacher."
            )

    for violation in grouped.get("room_clash", []):
        slot = slot_map.get(str(violation.get("slot")))
        available_room = next(
            (room for room in room_map.values() if room["room_code"] not in violation["message"]),
            None,
        )
        if slot and available_room:
            suggestions.append(
                f"Room clash: Room conflict on {slot['day']} {slot['start_time']}-{slot['end_time']}. Room {available_room['room_code']} (capacity {available_room['capacity']}) may be available at this time."
            )

    for violation in grouped.get("workload_exceeded", []):
        overloaded = next((faculty for faculty in faculty_map.values() if faculty["name"] in violation["message"]), None)
        alternate_subject = next(iter(subject_map.values()), None)
        alternate_faculty = next(
            (
                faculty
                for faculty in faculty_map.values()
                if overloaded and str(faculty["_id"]) != str(overloaded["_id"])
            ),
            None,
        )
        if overloaded and alternate_faculty and alternate_subject:
            suggestions.append(
                f"Workload exceeded: {overloaded['name']} has more scheduled hours than allowed. Consider reassigning {alternate_subject['name']} to {alternate_faculty['name']}."
            )

    for violation in grouped.get("lab_mismatch", []):
        subject = next((item for item in subject_map.values() if item["name"] in violation["message"]), None)
        labs = [room["room_code"] for room in room_map.values() if room.get("room_type") == "lab"]
        if subject and labs:
            suggestions.append(
                f"Lab mismatch: {subject['name']} is a lab but assigned to a classroom. Available labs: {', '.join(labs)}."
            )

    if not suggestions and violations:
        suggestions.append("Review faculty availability, room assignment, and subject hour requirements before generating again.")
    return suggestions
