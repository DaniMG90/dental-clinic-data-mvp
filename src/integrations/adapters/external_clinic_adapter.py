from typing import Any

from src.integrations.adapters.base import ImportAdapter


class ExternalClinicAdapter(ImportAdapter):
    """Reserved boundary for future clinical software adapters."""

    def read(self, source: Any):
        raise NotImplementedError("Clinical software integrations are intentionally out of scope.")

    def validate(self, raw_data):
        raise NotImplementedError("Clinical software integrations are intentionally out of scope.")

    def map_to_domain(self, raw_data):
        raise NotImplementedError("Clinical software integrations are intentionally out of scope.")

    def import_data(self, repository):
        raise NotImplementedError("Clinical software integrations are intentionally out of scope.")
