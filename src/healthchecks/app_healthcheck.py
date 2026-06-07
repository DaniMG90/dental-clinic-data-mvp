import sys
import urllib.request

from src.core.config import get_settings
from src.database.mongo_client import get_mongo_client


def main() -> int:
    try:
        urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=3)

        settings = get_settings()
        client = get_mongo_client(
            settings=settings,
            max_retries=1,
            retry_delay_seconds=0,
        )
        client[settings.mongo_active_db].client.admin.command("ping")
    except Exception as exc:
        print(f"[App healthcheck] unhealthy: {exc}", file=sys.stderr)
        return 1

    print("[App healthcheck] healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
