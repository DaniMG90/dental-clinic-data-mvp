SUPPORTED_EXPORT_ENTITIES = {"patients", "appointments", "metrics"}
SUPPORTED_EXPORT_FORMATS = {"csv", "json"}


def validate_export_request(entity: str, export_format: str) -> list[str]:
    errors: list[str] = []
    if entity not in SUPPORTED_EXPORT_ENTITIES:
        errors.append(f"Unsupported export entity: {entity}.")
    if export_format not in SUPPORTED_EXPORT_FORMATS:
        errors.append(f"Unsupported export format: {export_format}.")
    return errors
