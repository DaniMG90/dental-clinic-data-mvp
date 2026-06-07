from typing import Any

from src.integrations.adapters.base import ImportAdapter


class ApiAdapter(ImportAdapter):
    """Placeholder for future pull-based integrations with external APIs."""

    def read(self, source: Any):
        raise NotImplementedError("External API imports are not implemented in this MVP phase.")

    def validate(self, raw_data):
        raise NotImplementedError("External API imports are not implemented in this MVP phase.")

    def map_to_domain(self, raw_data):
        raise NotImplementedError("External API imports are not implemented in this MVP phase.")

    def import_data(self, repository):
        raise NotImplementedError("External API imports are not implemented in this MVP phase.")
