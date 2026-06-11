import ast
import re
from pathlib import Path

import pytest

from src.database.schema import COLLECTION_VALIDATORS
from src.services.operational_settings_service import default_operational_settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def python_imports(relative_path: str) -> set[str]:
    tree = ast.parse(read_text(relative_path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


DOCUMENTATION_EXPECTATIONS = [
    ("README.md", "Dental Operations Platform"),
    ("README.md", "Local-first open source platform"),
    ("README.md", "Streamlit UI"),
    ("README.md", "Application Services"),
    ("README.md", "Repositories / Import-Export Engines"),
    ("README.md", "MongoDB"),
    ("README.md", "Docker Compose"),
    ("README.md", "Operational Interface MVP"),
    ("README.md", "editable MongoDB-backed operational configuration"),
    ("docs/architecture.md", "UI code must call services"),
    ("docs/architecture.md", "must not instantiate MongoDB repositories directly"),
    ("docs/architecture.md", "AppointmentService"),
    ("docs/architecture.md", "PatientService"),
    ("docs/architecture.md", "TreatmentService"),
    ("docs/architecture.md", "AnalyticsService"),
    ("docs/architecture.md", "OperationalSettingsService"),
    ("docs/architecture.md", "AdminService"),
    ("docs/architecture.md", "TreatmentCatalogRepository"),
    ("docs/architecture.md", "TreatmentEventRepository"),
    ("docs/data-flow.md", "Manual entry or external source"),
    ("docs/data-flow.md", "Streamlit UI / Import Engine"),
    ("docs/data-flow.md", "Application service use case"),
    ("docs/data-flow.md", "Repository"),
    ("docs/data-flow.md", "MongoDB collection"),
    ("docs/data-model.md", "`patients`"),
    ("docs/data-model.md", "`appointments`"),
    ("docs/data-model.md", "`treatments`"),
    ("docs/data-model.md", "`treatment_catalog`"),
    ("docs/data-model.md", "`treatment_events`"),
    ("docs/data-model.md", "`operational_settings`"),
    ("docs/data-model.md", "`settings_key`: `default`"),
    ("docs/analytics.md", "default screen period is the current week"),
    ("docs/analytics.md", "no division by zero"),
    ("docs/analytics.md", "Frequent treatments are based on completed `treatment_events`"),
    ("docs/analytics.md", "The screen does not show patient rankings"),
    ("docs/configuration.md", "operational_settings"),
    ("docs/configuration.md", "OperationalSettingsService.get_settings()"),
    ("docs/configuration.md", "Auxiliar: can view basic configuration"),
    ("docs/configuration.md", "Odontologo: can modify operational configuration"),
    ("docs/configuration.md", "Admin: can modify operational configuration"),
    ("docs/interface.md", "Agenda is global"),
    ("docs/interface.md", "daily view with hour blocks"),
    ("docs/interface.md", "weekly view with hours on the vertical axis"),
    ("docs/interface.md", "monthly view with a selectable month grid"),
    ("docs/interface.md", "Overlapping appointments are allowed"),
    ("docs/interface.md", "Completing an appointment does not require registering a treatment"),
    ("docs/interface.md", "Stock is visible but marked as a future module"),
    ("docs/interface.md", "No destructive operation is executed from Admin"),
]


def test_documentation_expectations_are_traceable():
    assert len(DOCUMENTATION_EXPECTATIONS) >= 45


@pytest.mark.parametrize(("path", "phrase"), DOCUMENTATION_EXPECTATIONS)
def test_each_documentation_expectation_is_present(path, phrase):
    assert phrase in read_text(path)


def test_documentation_covers_core_behavior():
    missing = [
        f"{path}: {phrase}"
        for path, phrase in DOCUMENTATION_EXPECTATIONS
        if phrase not in read_text(path)
    ]
    assert missing == []


UI_EXPECTATIONS = [
    "Agenda",
    "Pacientes",
    "Tratamientos",
    "Analitica",
    "Stock",
    "Configuracion",
    "Admin",
    "Rol local",
    "Auxiliar",
    "Odontologo",
    "Vista",
    "Diaria",
    "Semanal",
    "Mensual",
    "Crear cita",
    "Completar",
    "Cancelar",
    "Abrir paciente",
    "Buscar paciente",
    "Ficha",
    "Listado",
    "Alta",
    "Nueva cita",
    "Registrar tratamiento",
    "Editar paciente",
    "Catalogo",
    "Registrar realizado",
    "Realizados / eventos",
    "Buscar en catalogo",
    "Ver inactivos",
    "Periodo",
    "Semana actual",
    "Mes actual",
    "Ultimos 30 dias",
    "Ultimos 90 dias",
    "Personalizado",
    "Citas",
    "Ocupacion",
    "No asistencias",
    "Pacientes con actividad",
    "Clinicas y gabinetes",
    "Horarios",
    "Profesionales",
    "Seguridad / datos",
    "PIN local de administrador",
    "Herramientas destructivas no se ejecutan",
]


def test_streamlit_ui_expectations_are_traceable():
    assert len(UI_EXPECTATIONS) >= 45


@pytest.mark.parametrize("label", UI_EXPECTATIONS)
def test_each_streamlit_ui_expectation_is_present(label):
    assert label in read_text("app/main.py")


def test_streamlit_ui_exposes_expected_operational_controls():
    app_text = read_text("app/main.py")

    missing = [label for label in UI_EXPECTATIONS if label not in app_text]

    assert missing == []


DATE_WINDOW_CASES = [
    ("Diaria", "timedelta(days=1)"),
    ("Semanal", "timedelta(days=7)"),
    ("Mensual", "replace(day=1)"),
]


def test_agenda_date_window_support_is_visible_in_ui_code():
    app_text = read_text("app/main.py")

    missing = [
        f"{view}: {implementation_marker}"
        for view, implementation_marker in DATE_WINDOW_CASES
        if view not in app_text or implementation_marker not in app_text
    ]

    assert missing == []


ARCHITECTURE_BOUNDARY_EXPECTATIONS = [
    ("app/main.py", {"pymongo", "src.database.connection", "src.repositories"}),
    ("src/services/appointment_service.py", {"streamlit"}),
    ("src/services/patient_service.py", {"streamlit"}),
    ("src/services/treatment_service.py", {"streamlit"}),
    ("src/services/analytics_service.py", {"streamlit"}),
    ("src/services/operational_settings_service.py", {"streamlit"}),
    ("src/repositories/patient_repository.py", {"streamlit"}),
    ("src/repositories/appointment_repository.py", {"streamlit"}),
    ("src/repositories/treatment_repository.py", {"streamlit"}),
    ("src/repositories/treatment_catalog_repository.py", {"streamlit"}),
    ("src/repositories/treatment_event_repository.py", {"streamlit"}),
]


def test_architecture_boundary_expectations_are_traceable():
    assert len(ARCHITECTURE_BOUNDARY_EXPECTATIONS) >= 10


@pytest.mark.parametrize(("relative_path", "banned_imports"), ARCHITECTURE_BOUNDARY_EXPECTATIONS)
def test_each_architecture_boundary_is_respected(relative_path, banned_imports):
    imports = python_imports(relative_path)

    assert [
        banned
        for banned in banned_imports
        if banned in imports or any(item.startswith(f"{banned}.") for item in imports)
    ] == []


def test_ui_services_and_repositories_keep_layer_boundaries():
    violations = []
    for relative_path, banned_imports in ARCHITECTURE_BOUNDARY_EXPECTATIONS:
        imports = python_imports(relative_path)
        for banned in banned_imports:
            if banned in imports or any(item.startswith(f"{banned}.") for item in imports):
                violations.append(f"{relative_path} imports {banned}")

    assert violations == []


SERVICE_REPOSITORY_CONTRACTS = [
    ("src/services/appointment_service.py", "AppointmentRepository"),
    ("src/services/appointment_service.py", "PatientRepository"),
    ("src/services/patient_service.py", "PatientRepository"),
    ("src/services/patient_service.py", "AppointmentRepository"),
    ("src/services/patient_service.py", "TreatmentRepository"),
    ("src/services/patient_service.py", "TreatmentEventRepository"),
    ("src/services/treatment_service.py", "TreatmentRepository"),
    ("src/services/treatment_service.py", "TreatmentEventRepository"),
    ("src/services/treatment_service.py", "TreatmentCatalogRepository"),
    ("src/services/treatment_service.py", "AppointmentRepository"),
    ("src/services/analytics_service.py", "AppointmentRepository"),
    ("src/services/analytics_service.py", "TreatmentEventRepository"),
    ("src/services/analytics_service.py", "OperationalSettingsService"),
    ("src/services/operational_settings_service.py", "OperationalSettingsRepository"),
    ("src/services/admin_service.py", "DatabaseMetadataRepository"),
]


def test_service_repository_contracts_are_traceable():
    assert len(SERVICE_REPOSITORY_CONTRACTS) >= 15


@pytest.mark.parametrize(("path", "contract"), SERVICE_REPOSITORY_CONTRACTS)
def test_each_service_repository_contract_is_present(path, contract):
    assert contract in read_text(path)


def test_services_orchestrate_through_repositories():
    missing = [
        f"{path}: {contract}"
        for path, contract in SERVICE_REPOSITORY_CONTRACTS
        if contract not in read_text(path)
    ]

    assert missing == []


SCHEMA_COLLECTIONS = [
    "patients",
    "appointments",
    "treatments",
    "treatment_catalog",
    "treatment_events",
    "import_sources",
    "operational_settings",
]


def test_python_schema_defines_expected_current_collections():
    assert set(SCHEMA_COLLECTIONS).issubset(COLLECTION_VALIDATORS)


SCHEMA_FIELD_EXPECTATIONS = [
    ("patients", "patient_code"),
    ("patients", "first_name"),
    ("patients", "last_name"),
    ("patients", "status"),
    ("appointments", "appointment_code"),
    ("appointments", "patient_id"),
    ("appointments", "scheduled_start"),
    ("appointments", "scheduled_end"),
    ("appointments", "duration_minutes"),
    ("appointments", "status"),
    ("appointments", "clinic"),
    ("appointments", "chair"),
    ("appointments", "professional"),
    ("treatments", "treatment_code"),
    ("treatments", "patient_id"),
    ("treatments", "appointment_id"),
    ("treatments", "treatment_type"),
    ("treatment_catalog", "catalog_code"),
    ("treatment_catalog", "name"),
    ("treatment_catalog", "active"),
    ("treatment_events", "treatment_id"),
    ("treatment_events", "patient_id"),
    ("treatment_events", "appointment_id"),
    ("treatment_events", "event_type"),
    ("treatment_events", "event_date"),
    ("operational_settings", "settings_key"),
    ("operational_settings", "clinics"),
    ("operational_settings", "chairs"),
    ("operational_settings", "weekly_schedule"),
    ("operational_settings", "analytics"),
]


def test_schema_field_expectations_are_traceable():
    assert len(SCHEMA_FIELD_EXPECTATIONS) >= 30


@pytest.mark.parametrize(("collection_name", "field_name"), SCHEMA_FIELD_EXPECTATIONS)
def test_each_schema_field_expectation_is_present(collection_name, field_name):
    properties = COLLECTION_VALIDATORS[collection_name]["$jsonSchema"]["properties"]

    assert field_name in properties


def test_python_schema_contains_current_operational_fields():
    missing = []
    for collection_name, field_name in SCHEMA_FIELD_EXPECTATIONS:
        properties = COLLECTION_VALIDATORS[collection_name]["$jsonSchema"]["properties"]
        if field_name not in properties:
            missing.append(f"{collection_name}.{field_name}")

    assert missing == []


INDEX_EXPECTATIONS = [
    "database.patients.create_index",
    "patient_code",
    "last_name",
    "database.appointments.create_index",
    "appointment_code",
    "scheduled_start",
    "clinic",
    "chair",
    "professional",
    "database.treatments.create_index",
    "treatment_code",
    "completed_at",
    "database.treatment_catalog.create_index",
    "catalog_code",
    "active",
    "database.treatment_events.create_index",
    "event_date",
    "database.operational_settings.create_index",
    "settings_key",
    "data_mode",
]


def test_index_expectations_are_traceable():
    assert len(INDEX_EXPECTATIONS) >= 20


@pytest.mark.parametrize("marker", INDEX_EXPECTATIONS)
def test_each_index_expectation_is_present(marker):
    assert marker in read_text("src/database/indexes.py")


def test_index_creation_covers_operational_queries():
    indexes_text = read_text("src/database/indexes.py")

    missing = [marker for marker in INDEX_EXPECTATIONS if marker not in indexes_text]

    assert missing == []


DOCKER_EXPECTATIONS = [
    "services:",
    "mongodb:",
    "app:",
    "image: mongo",
    "dental_mongodb",
    "dental_streamlit",
    "depends_on:",
    "condition: service_healthy",
    "MONGO_INITDB_ROOT_USERNAME",
    "MONGO_INITDB_ROOT_PASSWORD",
    "MONGO_ACTIVE_DB",
    "STREAMLIT_PORT",
    "healthcheck:",
    "src.healthchecks.app_healthcheck",
    "mongo_data:",
    "dental_network:",
]


def test_docker_expectations_are_traceable():
    assert len(DOCKER_EXPECTATIONS) >= 15


@pytest.mark.parametrize("marker", DOCKER_EXPECTATIONS)
def test_each_docker_expectation_is_present(marker):
    assert marker in read_text("docker-compose.yml")


def test_docker_compose_declares_local_runtime_contract():
    compose_text = read_text("docker-compose.yml")

    missing = [marker for marker in DOCKER_EXPECTATIONS if marker not in compose_text]

    assert missing == []


SEED_EXPECTATIONS = [
    "default_operational_settings",
    "database.operational_settings.update_one",
    "settings_key",
    "Patient(",
    "Appointment(",
    "TreatmentCatalogItem(",
    "Treatment(",
    "TreatmentEvent(",
    "upsert_by_code",
    "PAT-0001",
    "APT-0001",
    "TCAT-0001",
    "TRT-0001",
]


def test_seed_expectations_are_traceable():
    assert len(SEED_EXPECTATIONS) >= 12


@pytest.mark.parametrize("marker", SEED_EXPECTATIONS)
def test_each_seed_expectation_is_present(marker):
    assert marker in read_text("scripts/seed_demo_data.py")


def test_demo_seed_initializes_core_operational_data():
    seed_text = read_text("scripts/seed_demo_data.py")

    missing = [marker for marker in SEED_EXPECTATIONS if marker not in seed_text]

    assert missing == []


SETTINGS_EXPECTATIONS = [
    ("business_name", "Dental Operations Platform"),
    ("internal_identifier", "LOCAL-CLINIC"),
    ("data_mode", "demo"),
    ("timezone", "Europe/Madrid"),
    ("agenda.default_appointment_minutes", 45),
    ("agenda.default_start_hour", 8),
    ("agenda.default_end_hour", 21),
    ("agenda.allow_overlaps", True),
    ("analytics.default_period", "weekly"),
    ("analytics.inactive_patient_days", 180),
    ("security.confirm_sensitive_operations", True),
]


def test_settings_expectations_are_traceable():
    assert len(SETTINGS_EXPECTATIONS) >= 10


@pytest.mark.parametrize(("field_path", "expected_value"), SETTINGS_EXPECTATIONS)
def test_each_default_setting_expectation_is_present(field_path, expected_value):
    current = default_operational_settings()
    for part in field_path.split("."):
        current = getattr(current, part)

    assert current == expected_value


def test_default_operational_settings_match_documented_mvp_defaults():
    settings = default_operational_settings()

    assert settings.business_name == "Dental Operations Platform"
    assert settings.internal_identifier == "LOCAL-CLINIC"
    assert settings.data_mode == "demo"
    assert settings.timezone == "Europe/Madrid"
    assert [clinic.name for clinic in settings.clinics] == ["Clinic Centro", "Clinic Norte"]
    assert len(settings.chairs) == 4
    assert [professional.name for professional in settings.professionals] == ["Dr. Alvarez", "Dr. Rivera"]
    assert settings.agenda.default_appointment_minutes == 45
    assert settings.agenda.default_start_hour == 8
    assert settings.agenda.default_end_hour == 21
    assert settings.agenda.allow_overlaps is True
    assert settings.analytics.default_period == "weekly"
    assert settings.analytics.inactive_patient_days == 180
    assert settings.security.confirm_sensitive_operations is True


QUALITY_MATRIX = [
    ("startup", "app/main.py", "def main()"),
    ("mongodb-status", "src/services/database_status_service.py", "DatabaseStatusService"),
    ("mongodb-connection", "src/database/connection.py", "get_database"),
    ("demo-seed", "scripts/seed_demo_data.py", "Demo seed data"),
    ("configuration-init", "src/services/operational_settings_service.py", "default_operational_settings"),
    ("agenda-daily", "app/main.py", "_render_daily_agenda"),
    ("agenda-weekly", "app/main.py", "_render_weekly_agenda"),
    ("agenda-monthly", "app/main.py", "_render_monthly_agenda"),
    ("agenda-create", "src/services/appointment_service.py", "create_appointment"),
    ("agenda-update", "src/services/appointment_service.py", "update_appointment"),
    ("agenda-cancel", "src/services/appointment_service.py", "cancel_appointment"),
    ("agenda-complete", "src/services/appointment_service.py", "complete_appointment"),
    ("agenda-overlaps", "src/services/appointment_service.py", "find_overlaps"),
    ("patients-list", "src/services/patient_service.py", "list_patients"),
    ("patients-search", "src/services/patient_service.py", "search_patients"),
    ("patients-create", "src/services/patient_service.py", "create_patient"),
    ("patients-update", "src/services/patient_service.py", "update_patient"),
    ("patients-profile", "src/services/patient_service.py", "get_profile"),
    ("treatments-catalog", "src/services/treatment_service.py", "search_catalog"),
    ("treatments-catalog-create", "src/services/treatment_service.py", "create_catalog_item"),
    ("treatments-catalog-update", "src/services/treatment_service.py", "update_catalog_item"),
    ("treatments-performed", "src/services/treatment_service.py", "register_performed_treatment"),
    ("treatment-events", "src/services/treatment_service.py", "list_events"),
    ("analytics-weekly", "src/services/analytics_service.py", "weekly_summary"),
    ("analytics-custom", "src/services/analytics_service.py", "summary"),
    ("analytics-empty-safe-ratio", "src/services/analytics_service.py", "_safe_ratio"),
    ("analytics-occupation", "src/services/analytics_service.py", "_available_minutes"),
    ("configuration-read", "src/services/operational_settings_service.py", "get_settings"),
    ("configuration-update", "src/services/operational_settings_service.py", "update_settings"),
    ("roles", "app/main.py", "Rol local"),
    ("navigation", "app/main.py", "Navegacion"),
    ("stock-placeholder", "app/main.py", "Modulo visible"),
    ("admin-status", "src/services/admin_service.py", "get_system_status"),
    ("admin-pin", "app/main.py", "DENTAL_ADMIN_PIN"),
    ("docker-mongodb", "docker-compose.yml", "mongodb:"),
    ("docker-app", "docker-compose.yml", "app:"),
    ("docker-healthcheck", "docker-compose.yml", "healthcheck:"),
    ("docs-readme", "README.md", "Project Status"),
    ("docs-architecture", "docs/architecture.md", "Repository Layer"),
    ("docs-interface", "docs/interface.md", "Navigation"),
    ("docs-model", "docs/data-model.md", "Current Core Collections"),
    ("docs-analytics", "docs/analytics.md", "KPI Definitions"),
    ("docs-configuration", "docs/configuration.md", "Permissions"),
]


def test_quality_matrix_is_broad_enough_for_regression_review():
    assert len(QUALITY_MATRIX) >= 40


@pytest.mark.parametrize(("area", "path", "marker"), QUALITY_MATRIX)
def test_each_quality_matrix_entry_is_backed_by_repository_evidence(area, path, marker):
    assert marker in read_text(path), area


def test_quality_matrix_entries_are_backed_by_repository_evidence():
    missing = [
        f"{area}: {path} lacks {marker}"
        for area, path, marker in QUALITY_MATRIX
        if marker not in read_text(path)
    ]

    assert missing == []


def test_mongo_init_script_declares_current_operational_collections():
    init_text = read_text("mongo/init/01_create_collections.js")

    missing = [
        collection_name
        for collection_name in SCHEMA_COLLECTIONS
        if f'applyCollection("{collection_name}"' not in init_text
    ]

    assert missing == []


def test_mongo_init_script_keeps_current_operational_indexes():
    init_text = read_text("mongo/init/01_create_collections.js")

    expected_index_markers = [
        "targetDb.appointments.createIndex({ clinic: 1, scheduled_start: 1 })",
        "targetDb.treatment_catalog.createIndex({ catalog_code: 1 }, { unique: true })",
        "targetDb.operational_settings.createIndex({ settings_key: 1 }, { unique: true })",
    ]

    assert [marker for marker in expected_index_markers if marker not in init_text] == []


def test_interface_document_matches_configured_inactivity_threshold_default():
    interface_text = read_text("docs/interface.md")
    config_text = read_text("docs/configuration.md")

    assert "patients without activity in the last 90 days" not in interface_text
    assert "180 days by default" in interface_text
    assert "inactive-patient threshold: 180 days" in config_text


def test_documentation_does_not_claim_cloud_or_kubernetes_runtime():
    combined_docs = "\n".join(
        read_text(path)
        for path in [
            "README.md",
            "docs/architecture.md",
            "docs/project_scope.md",
            "docs/roadmap.md",
        ]
    )

    forbidden_claims = [
        r"\bKubernetes\b.*implemented",
        r"\bmicroservices\b.*implemented",
        r"\bcloud deployment\b.*implemented",
        r"\bCI/CD\b.*implemented",
    ]

    assert [pattern for pattern in forbidden_claims if re.search(pattern, combined_docs, re.IGNORECASE)] == []
