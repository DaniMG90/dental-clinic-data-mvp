from datetime import date, datetime
from typing import Any


def metrics_to_export(metrics: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(metrics, list):
        return [_serialize_row(row) for row in metrics]

    rows: list[dict[str, Any]] = []
    for metric_name, value in metrics.items():
        if isinstance(value, list):
            for item in value:
                row = {"metric": metric_name}
                row.update(_serialize_row(item))
                rows.append(row)
        else:
            rows.append({"metric": metric_name, "value": _serialize_value(value)})
    return rows


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _serialize_value(value) for key, value in row.items()}


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value
