import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from src.models.appointment import Appointment, AppointmentStatus
from src.models.patient import Patient, PatientStatus
from src.models.treatment import Treatment, TreatmentStatus
from src.models.treatment_event import TreatmentEvent, TreatmentEventType
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.treatment_event_repository import TreatmentEventRepository
from src.repositories.treatment_repository import TreatmentRepository


class FakeInsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeDeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


class FakeUpdateResult:
    def __init__(self, matched_count=0):
        self.matched_count = matched_count


class FakeCursor:
    def __init__(self, documents):
        self._documents = list(documents)

    def sort(self, sort):
        for key, direction in reversed(sort):
            self._documents.sort(
                key=lambda document: (document.get(key) is None, document.get(key)),
                reverse=direction < 0,
            )
        return self

    def limit(self, limit):
        self._documents = self._documents[:limit]
        return self

    def __iter__(self):
        return iter(self._documents)


class FakeCollection:
    def __init__(self):
        self.documents = {}

    def insert_one(self, payload):
        document_id = payload.get("_id") or ObjectId()
        payload["_id"] = document_id
        self.documents[document_id] = dict(payload)
        return FakeInsertOneResult(document_id)

    def find_one(self, filters, projection=None):
        for document in self.documents.values():
            if _matches(document, filters):
                if projection == {"_id": 1}:
                    return {"_id": document["_id"]}
                return dict(document)
        return None

    def find(self, filters):
        return FakeCursor(
            dict(document)
            for document in self.documents.values()
            if _matches(document, filters)
        )

    def update_one(self, filters, update, upsert=False):
        for document in self.documents.values():
            if _matches(document, filters):
                document.update(update["$set"])
                return FakeUpdateResult(matched_count=1)
        return FakeUpdateResult()

    def delete_one(self, filters):
        for document_id, document in list(self.documents.items()):
            if _matches(document, filters):
                del self.documents[document_id]
                return FakeDeleteResult(1)
        return FakeDeleteResult(0)

    def aggregate(self, pipeline):
        documents: list[dict[str, Any]] = [dict(document) for document in self.documents.values()]
        for stage in pipeline:
            if "$match" in stage:
                documents = [document for document in documents if _matches(document, stage["$match"])]
            elif "$group" in stage:
                documents = _group_documents(documents, stage["$group"])
            elif "$project" in stage:
                documents = [_project_document(document, stage["$project"]) for document in documents]
            elif "$sort" in stage:
                for key, direction in reversed(stage["$sort"].items()):
                    documents.sort(key=lambda document: document.get(key), reverse=direction < 0)
            elif "$limit" in stage:
                documents = documents[: stage["$limit"]]
        return documents


class FakeDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        self.collections.setdefault(name, FakeCollection())
        return self.collections[name]


def dt(day: int, hour: int = 9) -> datetime:
    return datetime(2026, 1, day, hour, tzinfo=timezone.utc)


def _matches(document: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if key == "$or":
            if not any(_matches(document, option) for option in expected):
                return False
            continue

        actual = document.get(key)
        if isinstance(expected, dict):
            if not _matches_operator(actual, expected):
                return False
        elif actual != expected:
            return False
    return True


def _matches_operator(actual: Any, expected: dict[str, Any]) -> bool:
    if "$in" in expected and actual not in expected["$in"]:
        return False
    if "$ne" in expected and actual == expected["$ne"]:
        return False
    if "$gte" in expected and (actual is None or actual < expected["$gte"]):
        return False
    if "$gt" in expected and (actual is None or actual <= expected["$gt"]):
        return False
    if "$lt" in expected and (actual is None or actual >= expected["$lt"]):
        return False
    if "$regex" in expected:
        flags = re.IGNORECASE if "i" in expected.get("$options", "") else 0
        if actual is None or re.search(expected["$regex"], str(actual), flags) is None:
            return False
    return True


def _group_documents(documents: list[dict[str, Any]], group_spec: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[Any, dict[str, Any]] = {}
    for document in documents:
        group_id = _resolve_expression(document, group_spec["_id"])
        key = _hashable(group_id)
        grouped.setdefault(key, {"_id": group_id})
        for output_field, expression in group_spec.items():
            if output_field == "_id":
                continue
            if "$sum" in expression:
                value = expression["$sum"]
                grouped[key][output_field] = grouped[key].get(output_field, 0) + (
                    value if isinstance(value, int) else document.get(value.removeprefix("$"), 0)
                )
    return list(grouped.values())


def _project_document(document: dict[str, Any], project_spec: dict[str, Any]) -> dict[str, Any]:
    projected = {}
    for field, expression in project_spec.items():
        if field == "_id" and expression == 0:
            continue
        if expression == 1:
            projected[field] = document.get(field)
        else:
            projected[field] = _resolve_expression(document, expression)
    return projected


def _resolve_expression(document: dict[str, Any], expression: Any) -> Any:
    if isinstance(expression, str) and expression.startswith("$"):
        return _resolve_path(document, expression.removeprefix("$"))
    if isinstance(expression, dict) and "$dateToString" in expression:
        date_spec = expression["$dateToString"]
        value = _resolve_expression(document, date_spec["date"])
        return value.strftime(date_spec["format"])
    if isinstance(expression, dict):
        return {key: _resolve_expression(document, value) for key, value in expression.items()}
    return expression


def _resolve_path(document: dict[str, Any], path: str) -> Any:
    current: Any = document
    for part in path.split("."):
        current = current.get(part)
    return current


def _hashable(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _hashable(item)) for key, item in value.items()))
    return value


def test_patient_repository_crud_and_missing_id():
    repository = PatientRepository(FakeDatabase())
    patient = Patient(patient_code="PAT-REPO", first_name="Repo", last_name="Patient")

    created = repository.create(patient)
    found = repository.get_by_id(str(created.id))
    updated = repository.update(created.id, {"phone": "+34 600 000 000"})
    deleted = repository.delete(created.id)

    assert found == created
    assert updated.phone == "+34 600 000 000"
    assert deleted is True
    assert repository.get_by_id(ObjectId()) is None


def test_patient_repository_domain_queries():
    repository = PatientRepository(FakeDatabase())
    active = repository.create(Patient(patient_code="PAT-A", first_name="Ana", last_name="Lopez"))
    repository.create(
        Patient(
            patient_code="PAT-I",
            first_name="Luis",
            last_name="Perez",
            status=PatientStatus.INACTIVE,
            phone="+34 611 222 333",
        ),
    )

    assert repository.find_active_patients() == [active]
    assert len(repository.find_inactive_patients()) == 1
    assert repository.search_by_name_or_phone("611")[0].first_name == "Luis"
    assert repository.search_by_name_or_phone(" ") == []


def test_appointment_repository_crud_empty_update_and_domain_queries():
    patient_id = ObjectId()
    repository = AppointmentRepository(FakeDatabase())
    created = repository.create(
        Appointment(
            appointment_code="APT-1",
            patient_id=patient_id,
            scheduled_start=dt(1),
            scheduled_end=dt(1, 10),
            duration_minutes=60,
            status=AppointmentStatus.SCHEDULED,
        ),
    )
    repository.create(
        Appointment(
            appointment_code="APT-2",
            patient_id=patient_id,
            scheduled_start=dt(2),
            scheduled_end=dt(2, 10),
            duration_minutes=60,
            status=AppointmentStatus.CANCELLED,
        ),
    )

    assert repository.update(created.id, {}) == created
    assert repository.find_by_patient_id(patient_id)[0].id == created.id
    assert len(repository.find_by_date_range(dt(1, 0), dt(2, 0))) == 1
    assert repository.count_by_status(dt(1, 0), dt(3, 0)) == [
        {"count": 1, "status": AppointmentStatus.CANCELLED},
        {"count": 1, "status": AppointmentStatus.SCHEDULED},
    ]
    assert repository.get_agenda_occupation(dt(1, 0), dt(2, 0)) == [
        {"appointments": 1, "date": "2026-01-01", "minutes": 60, "status": AppointmentStatus.SCHEDULED},
    ]
    assert repository.delete(created.id) is True


def test_treatment_repository_crud_and_domain_queries():
    patient_id = ObjectId()
    repository = TreatmentRepository(FakeDatabase())
    created = repository.create(
        Treatment(
            treatment_code="TR-1",
            patient_id=patient_id,
            treatment_type="implant",
            status=TreatmentStatus.IN_PROGRESS,
            planned_date=dt(1),
        ),
    )
    repository.create(
        Treatment(
            treatment_code="TR-2",
            patient_id=patient_id,
            treatment_type="implant",
            status=TreatmentStatus.COMPLETED,
            completed_at=dt(2),
        ),
    )

    assert repository.get_by_id(created.id).treatment_type == "implant"
    assert repository.update(created.id, {"final_price": 900}).final_price == 900
    assert repository.find_active_treatments()[0].id == created.id
    assert len(repository.find_by_category("implant")) == 2
    assert repository.find_most_used_treatments(dt(1, 0), dt(3, 0)) == [
        {"count": 2, "treatment_type": "implant"},
    ]
    assert repository.delete(ObjectId()) is False


def test_treatment_event_repository_crud_and_domain_queries():
    patient_id = ObjectId()
    treatment_id = ObjectId()
    appointment_id = ObjectId()
    repository = TreatmentEventRepository(FakeDatabase())
    created = repository.create(
        TreatmentEvent(
            treatment_id=treatment_id,
            patient_id=patient_id,
            appointment_id=appointment_id,
            event_type=TreatmentEventType.CREATED,
            event_date=dt(1),
        ),
    )
    repository.create(
        TreatmentEvent(
            treatment_id=treatment_id,
            patient_id=patient_id,
            appointment_id=appointment_id,
            event_type=TreatmentEventType.COMPLETED,
            event_date=dt(2),
        ),
    )

    assert repository.get_by_id(created.id).event_type == TreatmentEventType.CREATED
    assert repository.update(created.id, {"description": "Initial record"}).description == "Initial record"
    assert len(repository.find_by_patient_id(patient_id)) == 2
    assert len(repository.find_by_treatment_id(treatment_id)) == 2
    assert len(repository.find_by_appointment_id(appointment_id)) == 2
    assert repository.get_treatment_activity_evolution(dt(1, 0), dt(3, 0)) == [
        {"count": 1, "date": "2026-01-01", "event_type": TreatmentEventType.CREATED},
        {"count": 1, "date": "2026-01-02", "event_type": TreatmentEventType.COMPLETED},
    ]
    assert repository.get_treatment_frequency(dt(1, 0), dt(3, 0)) == [
        {"count": 1, "event_type": TreatmentEventType.COMPLETED},
        {"count": 1, "event_type": TreatmentEventType.CREATED},
    ]
    assert repository.delete(created.id) is True


def test_repository_rejects_invalid_object_id():
    repository = PatientRepository(FakeDatabase())

    try:
        repository.get_by_id("not-an-object-id")
    except ValueError as exc:
        assert "Invalid MongoDB ObjectId" in str(exc)
    else:
        raise AssertionError("Invalid ObjectId should raise ValueError")
