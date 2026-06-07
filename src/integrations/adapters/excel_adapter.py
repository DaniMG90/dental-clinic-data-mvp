from typing import Any

from src.integrations.adapters.base import ExportAdapter, ImportAdapter


class ExcelImportAdapter(ImportAdapter):
    def read(self, source: Any):
        raise NotImplementedError("Excel import is reserved for a future adapter.")

    def validate(self, raw_data):
        raise NotImplementedError("Excel import is reserved for a future adapter.")

    def map_to_domain(self, raw_data):
        raise NotImplementedError("Excel import is reserved for a future adapter.")

    def import_data(self, repository):
        raise NotImplementedError("Excel import is reserved for a future adapter.")


class ExcelExportAdapter(ExportAdapter):
    def collect_data(self, repository_or_service):
        raise NotImplementedError("Excel export is reserved for a future adapter.")

    def map_from_domain(self, data):
        raise NotImplementedError("Excel export is reserved for a future adapter.")

    def write(self, destination, data):
        raise NotImplementedError("Excel export is reserved for a future adapter.")
