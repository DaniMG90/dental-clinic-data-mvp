from src.models.import_source import ImportSource
from src.repositories.base_repository import BaseMongoRepository


class ImportSourceRepository(BaseMongoRepository[ImportSource]):
    collection_name = "import_sources"
    model_class = ImportSource
