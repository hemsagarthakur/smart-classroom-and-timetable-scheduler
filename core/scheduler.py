import random
from collections import Counter

from bson import ObjectId
from deap import algorithms, base, creator, tools
from flask import current_app

from core.constraints import validate_timetable
from core.models import Faculty, Room, Subject, TimeSlot
from database.db import get_departments_col, get_faculty_col, get_rooms_col, get_slots_col, get_subjects_col


if not hasattr(creator, "FitnessMax"):
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
if not hasattr(creator, "Individual"):
    creator.create("Individual", list, fitness=creator.FitnessMax)


def load_scheduling_data(dept_id, semester):
    faculty_docs = list(get_faculty_col().find({"department_id": ObjectId(dept_id)}))
    room_docs = list(
        get_rooms_col().find(
            {
                "$or": [
                    {"department_id": ObjectId(dept_id)},
                    {"department_id": None},
                    {"department_id": {"$exists": False}},
                ]
            }
        )
    )
    subject_docs = list(get_subjects_col().find({"department_id": ObjectId(dept_id), "semester": int(semester)}))
    department_doc = get_departments_col().find_one({"_id": ObjectId(dept_id)})
    shift = department_doc["shift"] if department_doc else "morning"
    slot_docs = list(get_slots_col().find({"shift": shift}).sort([("day", 1), ("period_number", 1)]))

    faculty = [Faculty.from_mongo(doc) for doc in faculty_docs]
    rooms = [Room.from_mongo(doc) for doc in room_docs]
    subjects = [Subject.from_mongo(doc) for doc in subject_docs]
    slots = [TimeSlot.from_mongo(doc) for doc in slot_docs]

    subject_map = {subject.id: subject for subject in subjects}
    faculty_by_subject = {}
    for fac in faculty:
        for subject_id in fac.subject_ids:
            faculty_by_subject.setdefault(subject_id, []).append(fac)

    requirements = []
    for subject in subjects:
        for _ in range(subject.hours_per_week):
            requirements.append(subject.id)

    return {
        "department": department_doc,
        "faculty": faculty,
        "rooms": rooms,
        "subjects": subjects,
        "slots": slots,
        "subject_map": subject_map,
        "faculty_by_subject": faculty_by_subject,
        "requirements": requirements,
    }


def _build_entry(subject, faculty, room, slot, department_code):
    return {
        "slot_id": slot.id,
        "subject_id": subject.id,
        "faculty_id": faculty.id,
        "room_id": room.id,
        "day": slot.day,
        "period_number": slot.period_number,
        "start_time": slot.start_time,
        "end_time": slot.end_time,
        "subject_name": subject.name,
        "subject_code": subject.code,
        "faculty_name": faculty.name,
        "room_code": room.room_code,
        "is_fixed": slot.is_fixed,
        "department_code": department_code,
    }


def _eligible_rooms(subject, rooms, department_id):
    eligible = []
    for room in rooms:
        same_dept = room.department_id is None or str(room.department_id) == str(department_id)
        if not same_dept:
            continue
        if subject.is_lab and room.room_type != "lab":
            continue
        if not subject.is_lab and room.room_type not in {"classroom", "lab"}:
            continue
        eligible.append(room)
    return eligible or rooms


def _build_individual(data, rng):
    entries = []
    department_code = data["department"]["code"] if data["department"] else ""
    slots = [slot for slot in data["slots"] if slot.period_number != 4]
    rng.shuffle(slots)
    slot_cursor = 0

    for subject_id in data["requirements"]:
        subject = data["subject_map"][subject_id]
        faculty_options = data["faculty_by_subject"].get(subject_id) or data["faculty"]
        if not faculty_options:
            continue
        if slot_cursor >= len(slots):
            slot_cursor = 0
            rng.shuffle(slots)
        slot = slots[slot_cursor]
        slot_cursor += 1
        faculty = rng.choice(faculty_options)
        room = rng.choice(_eligible_rooms(subject, data["rooms"], data["department"]["_id"]))
        entries.append(_build_entry(subject, faculty, room, slot, department_code))
    return creator.Individual(entries)


def evaluate(individual, data):
    score = 1000
    faculty_slot_counter = Counter((entry["faculty_id"], entry["slot_id"]) for entry in individual)
    room_slot_counter = Counter((entry["room_id"], entry["slot_id"]) for entry in individual)
    faculty_hours = Counter(entry["faculty_id"] for entry in individual)
    subject_hours = Counter(entry["subject_id"] for entry in individual)
    faculty_map = {item.id: item for item in data["faculty"]}
    room_map = {item.id: item for item in data["rooms"]}
    subject_map = data["subject_map"]
    slot_map = {item.id: item for item in data["slots"]}

    for entry in individual:
        faculty = faculty_map.get(entry["faculty_id"])
        room = room_map.get(entry["room_id"])
        subject = subject_map.get(entry["subject_id"])
        slot = slot_map.get(entry["slot_id"])

        if faculty_slot_counter[(entry["faculty_id"], entry["slot_id"])] > 1:
            score -= 50
        if room_slot_counter[(entry["room_id"], entry["slot_id"])] > 1:
            score -= 50
        if faculty and slot and slot.day not in faculty.available_days:
            score -= 30
        if subject and subject_hours[entry["subject_id"]] > subject.hours_per_week:
            score -= 30
        if faculty and faculty_hours[entry["faculty_id"]] > faculty.max_hours_per_week:
            score -= 20
        if subject and room and subject.is_lab and room.room_type != "lab":
            score -= 20
        if subject and room and subject.requires_projector and not room.has_projector:
            score -= 10
        if faculty:
            leave_adjusted_capacity = max(
                1,
                round(faculty.max_hours_per_week - ((faculty.avg_leaves_per_month / 20) * faculty.max_hours_per_week)),
            )
            if faculty_hours[entry["faculty_id"]] > leave_adjusted_capacity:
                score -= 15
        if slot and slot.is_fixed and slot.fixed_subject_id and str(slot.fixed_subject_id) == str(entry["subject_id"]):
            score += 10

    return (score,)


def _mutate_individual(individual, data, rng):
    tools.mutShuffleIndexes(individual, indpb=0.05)
    for entry in individual:
        if rng.random() < 0.08:
            subject = data["subject_map"].get(entry["subject_id"])
            if subject:
                entry["room_id"] = rng.choice(_eligible_rooms(subject, data["rooms"], data["department"]["_id"])).id
                room_map = {room.id: room for room in data["rooms"]}
                entry["room_code"] = room_map[entry["room_id"]].room_code
        if rng.random() < 0.08:
            faculty_options = data["faculty_by_subject"].get(entry["subject_id"]) or data["faculty"]
            faculty = rng.choice(faculty_options)
            entry["faculty_id"] = faculty.id
            entry["faculty_name"] = faculty.name
    return (individual,)


def generate_timetables(dept_id, semester, n=5, seed_offset=0):
    try:
        data = load_scheduling_data(dept_id, semester)
        if not data["subjects"] or not data["faculty"] or not data["rooms"] or not data["slots"]:
            raise RuntimeError("Insufficient scheduling data. Please add faculty, rooms, subjects, and time slots.")

        variants = []
        for i in range(1, n + 1):
            seed = (i * 42) + seed_offset
            rng = random.Random(seed)
            toolbox = base.Toolbox()
            toolbox.register("individual", _build_individual, data=data, rng=rng)
            toolbox.register("population", tools.initRepeat, list, toolbox.individual)
            toolbox.register("evaluate", evaluate, data=data)
            toolbox.register("mate", tools.cxTwoPoint)
            toolbox.register("mutate", _mutate_individual, data=data, rng=rng)
            toolbox.register("select", tools.selTournament, tournsize=3)

            pop = toolbox.population(n=current_app.config["GA_POPULATION"])
            algorithms.eaSimple(
                pop,
                toolbox,
                cxpb=current_app.config["GA_CROSSOVER_PROB"],
                mutpb=current_app.config["GA_MUTATION_PROB"],
                ngen=current_app.config["GA_GENERATIONS"],
                verbose=False,
            )
            best = tools.selBest(pop, k=1)[0]
            score = toolbox.evaluate(best)[0]
            violations = validate_timetable(best, data["faculty"], data["rooms"], data["subjects"])
            variants.append(
                {
                    "entries": list(best),
                    "fitness_score": float(score),
                    "clash_count": len(violations),
                    "violations": [
                        {
                            "type": item["type"],
                            "message": item["message"],
                            "slot": item.get("slot"),
                            "severity": item["severity"],
                        }
                        for item in violations
                    ],
                    "dept_id": dept_id,
                    "semester": int(semester),
                    "seed_used": seed,
                }
            )

        return sorted(variants, key=lambda item: item["fitness_score"], reverse=True)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc
