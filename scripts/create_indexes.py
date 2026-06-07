import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_database
from src.database.indexes import create_indexes
from src.database.schema import apply_collection_validators


def main() -> None:
    database = get_database()
    apply_collection_validators(database)
    create_indexes(database)
    print(f"MongoDB validators and indexes created for database: {database.name}")


if __name__ == "__main__":
    main()
