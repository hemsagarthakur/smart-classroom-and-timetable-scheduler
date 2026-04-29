from collections import Counter


def check_faculty_clash(entries, new_entry):
    return any(
        str(entry["faculty_id"]) == str(new_entry["faculty_id"])
        and str(entry["slot_id"]) == str(new_entry["slot_id"])
        for entry in entries
    )


def check_room_clash(entries, new_entry):
    return any(
        str(entry["room_id"]) == str(new_entry["room_id"])
        and str(entry["slot_id"]) == str(new_entry["slot_id"])
        for entry in entries
    )


def check_daily_limit(entries, faculty_id, day, max_per_day):
    count = sum(
        1
        for entry in entries
        if str(entry["faculty_id"]) == str(faculty_id) and entry["day"] == day
    )
    return count <= max_per_day


def check_weekly_limit(entries, faculty_id, max_per_week):
    count = sum(1 for entry in entries if str(entry["faculty_id"]) == str(faculty_id))
    return count <= max_per_week


def check_lab_room_match(subject, room):
    return not subject.is_lab or room.room_type == "lab"


def check_projector_match(subject, room):
    return not subject.requires_projector or room.has_projector


def check_faculty_availability(faculty, slot):
    return slot.day in faculty.available_days


def validate_timetable(entries, all_faculty, all_rooms, all_subjects):
    violations = []
    faculty_map = {str(item.id): item for item in all_faculty}
    room_map = {str(item.id): item for item in all_rooms}
    subject_map = {str(item.id): item for item in all_subjects}

    slot_pairs_faculty = Counter((str(entry["slot_id"]), str(entry["faculty_id"])) for entry in entries)
    slot_pairs_room = Counter((str(entry["slot_id"]), str(entry["room_id"])) for entry in entries)
    faculty_hours = Counter(str(entry["faculty_id"]) for entry in entries)
    subject_hours = Counter(str(entry["subject_id"]) for entry in entries)

    for entry in entries:
        faculty = faculty_map.get(str(entry["faculty_id"]))
        room = room_map.get(str(entry["room_id"]))
        subject = subject_map.get(str(entry["subject_id"]))

        if slot_pairs_faculty[(str(entry["slot_id"]), str(entry["faculty_id"]))] > 1:
            violations.append(
                {
                    "type": "faculty_clash",
                    "message": f"{entry['faculty_name']} is double-booked on {entry['day']} {entry['start_time']}-{entry['end_time']}.",
                    "slot": entry["slot_id"],
                    "severity": "high",
                }
            )
        if slot_pairs_room[(str(entry["slot_id"]), str(entry["room_id"]))] > 1:
            violations.append(
                {
                    "type": "room_clash",
                    "message": f"Room {entry['room_code']} is double-booked on {entry['day']} {entry['start_time']}-{entry['end_time']}.",
                    "slot": entry["slot_id"],
                    "severity": "high",
                }
            )
        if faculty and entry["day"] not in faculty.available_days:
            violations.append(
                {
                    "type": "faculty_availability",
                    "message": f"{faculty.name} is not available on {entry['day']}.",
                    "slot": entry["slot_id"],
                    "severity": "medium",
                }
            )
        if faculty and faculty_hours[str(faculty.id)] > faculty.max_hours_per_week:
            violations.append(
                {
                    "type": "workload_exceeded",
                    "message": f"{faculty.name} exceeds weekly limit of {faculty.max_hours_per_week} hours.",
                    "slot": entry["slot_id"],
                    "severity": "medium",
                }
            )
        if subject and subject_hours[str(subject.id)] > subject.hours_per_week:
            violations.append(
                {
                    "type": "subject_hours_exceeded",
                    "message": f"{subject.name} exceeds required weekly hours of {subject.hours_per_week}.",
                    "slot": entry["slot_id"],
                    "severity": "medium",
                }
            )
        if subject and room and subject.is_lab and room.room_type != "lab":
            violations.append(
                {
                    "type": "lab_mismatch",
                    "message": f"{subject.name} is a lab but assigned to {room.room_code}.",
                    "slot": entry["slot_id"],
                    "severity": "high",
                }
            )
        if subject and room and subject.requires_projector and not room.has_projector:
            violations.append(
                {
                    "type": "projector_mismatch",
                    "message": f"{subject.name} requires projector but {room.room_code} has none.",
                    "slot": entry["slot_id"],
                    "severity": "low",
                }
            )

    seen = set()
    unique_violations = []
    for violation in violations:
        key = (violation["type"], violation["message"], str(violation.get("slot")))
        if key not in seen:
            seen.add(key)
            unique_violations.append(violation)
    return unique_violations
