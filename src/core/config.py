from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str
    mongo_username: str
    mongo_password: str
    mongo_host: str
    mongo_port: int
    mongo_dev_db: str
    mongo_demo_db: str
    mongo_active_db: str
    mongo_connect_max_retries: int
    mongo_retry_delay_seconds: int
    mongo_timeout_ms: int

    @property
    def mongo_uri(self) -> str:
        return (
            f"mongodb://{self.mongo_username}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}/?authSource=admin"
        )


def get_settings() -> Settings:
    dev_db = getenv("MONGO_DATABASE") or getenv("MONGO_DEV_DB", "dental_crm_dev")
    demo_db = getenv("MONGO_DEMO_DATABASE") or getenv("MONGO_DEMO_DB", "dental_crm_demo")

    return Settings(
        app_env=getenv("APP_ENV", "development"),
        mongo_username=getenv("MONGO_INITDB_ROOT_USERNAME", "admin"),
        mongo_password=getenv("MONGO_INITDB_ROOT_PASSWORD", "dev_password"),
        mongo_host=getenv("MONGO_HOST", "localhost"),
        mongo_port=int(getenv("MONGO_PORT", "27017")),
        mongo_dev_db=dev_db,
        mongo_demo_db=demo_db,
        mongo_active_db=getenv("MONGO_ACTIVE_DB") or dev_db,
        mongo_connect_max_retries=int(getenv("MONGO_CONNECT_MAX_RETRIES", "5")),
        mongo_retry_delay_seconds=int(getenv("MONGO_RETRY_DELAY_SECONDS", "2")),
        mongo_timeout_ms=int(getenv("MONGO_TIMEOUT_MS", "3000")),
    )
