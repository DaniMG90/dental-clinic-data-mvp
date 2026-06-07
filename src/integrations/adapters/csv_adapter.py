import csv
from pathlib import Path
from typing import Any, Iterable

from src.integrations.adapters.base import ExportAdapter, ImportAdapter


class CsvImportAdapter(ImportAdapter):
    def __init__(self) -> None:
        self.raw_data: list[dict[str, Any]] = []
        self.domain_data: list[Any] = []

    def read(self, source: Any) -> list[dict[str, Any]]:
        if hasattr(source, "read"):
            content = source.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            rows = csv.DictReader(content.splitlines())
        else:
            with Path(source).open(encoding="utf-8", newline="") as file:
                rows = csv.DictReader(file)
                self.raw_data = [dict(row) for row in rows]
                return self.raw_data

        self.raw_data = [dict(row) for row in rows]
        return self.raw_data

    def validate(self, raw_data: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(raw_data)

    def map_to_domain(self, raw_data: Iterable[dict[str, Any]]) -> list[Any]:
        self.domain_data = list(raw_data)
        return self.domain_data

    def import_data(self, repository: Any) -> list[Any]:
        return [repository.create(item) for item in self.domain_data]


class CsvExportAdapter(ExportAdapter):
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
        rows = list(data)
        fieldnames = sorted({field for row in rows for field in row})

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return path
