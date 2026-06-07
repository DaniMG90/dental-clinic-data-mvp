import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from bson import ObjectId

from src.integrations.adapters.base import ExportAdapter, ImportAdapter


class JsonImportAdapter(ImportAdapter):
    def __init__(self) -> None:
        self.raw_data: list[dict[str, Any]] = []
        self.domain_data: list[Any] = []

    def read(self, source: Any) -> list[dict[str, Any]]:
        if hasattr(source, "read"):
            content = source.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            payload = json.loads(content)
        else:
            with Path(source).open(encoding="utf-8") as file:
                payload = json.load(file)

        if isinstance(payload, dict):
            payload = payload.get("records", payload.get("data", []))
        if not isinstance(payload, list):
            raise ValueError("JSON import source must contain a list of records.")

        self.raw_data = [dict(item) for item in payload]
        return self.raw_data

    def validate(self, raw_data: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(raw_data)

    def map_to_domain(self, raw_data: Iterable[dict[str, Any]]) -> list[Any]:
        self.domain_data = list(raw_data)
        return self.domain_data

    def import_data(self, repository: Any) -> list[Any]:
        return [repository.create(item) for item in self.domain_data]


class JsonExportAdapter(ExportAdapter):
    def collect_data(self, repository_or_service: Any) -> list[Any]:
        if hasattr(repository_or_service, "find_many"):
            return repository_or_service.find_many(limit=0)
        if callable(repository_or_service):
            return list(repository_or_service())
        return list(repository_or_service)

    def map_from_domain(self, data: Iterable[Any]) -> list[dict[str, Any]]:
        return [dict(item) for item in data]

    def write(self, destination: str | Path, data: Iterable[dict[str, Any]]) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(list(data), file, ensure_ascii=False, indent=2, default=_json_default)

        return path


def _json_default(value: Any) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)
