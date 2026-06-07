from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable


class ImportAdapter(ABC):
    """Contract for adapters that bring external data into the domain layer."""

    @abstractmethod
    def read(self, source: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def validate(self, raw_data: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def map_to_domain(self, raw_data: Iterable[dict[str, Any]]) -> list[Any]:
        raise NotImplementedError

    @abstractmethod
    def import_data(self, repository: Any) -> list[Any]:
        raise NotImplementedError


class ExportAdapter(ABC):
    """Contract for adapters that serialize domain data to an external format."""

    @abstractmethod
    def collect_data(self, repository_or_service: Any) -> list[Any]:
        raise NotImplementedError

    @abstractmethod
    def map_from_domain(self, data: Iterable[Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def write(self, destination: str | Path, data: Iterable[dict[str, Any]]) -> Path:
        raise NotImplementedError
