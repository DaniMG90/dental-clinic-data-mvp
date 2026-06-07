from typing import Any, Generic, TypeVar

from bson import ObjectId
from pydantic import BaseModel
from pymongo.collection import Collection

from src.models.base import utc_now

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseMongoRepository(Generic[ModelT]):
    collection_name: str
    model_class: type[ModelT]

    def __init__(self, database: Any):
        self._collection: Collection = database[self.collection_name]

    def find_by_id(self, document_id: ObjectId | str) -> ModelT | None:
        document = self._collection.find_one({"_id": self._as_object_id(document_id)})
        return self._to_model(document) if document else None

    def get_by_id(self, document_id: ObjectId | str) -> ModelT | None:
        return self.find_by_id(document_id)

    def find_many(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[ModelT]:
        cursor = self._collection.find(filters or {})
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return [self._to_model(document) for document in cursor]

    def create(self, model: ModelT | dict[str, Any]) -> ModelT:
        payload = self._to_payload(model)
        result = self._collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return self._to_model(payload)

    def update(self, document_id: ObjectId | str, changes: dict[str, Any]) -> ModelT | None:
        clean_changes = {key: value for key, value in changes.items() if value is not None}
        if not clean_changes:
            return self.find_by_id(document_id)
        if "updated_at" in self.model_class.model_fields and "updated_at" not in clean_changes:
            clean_changes["updated_at"] = utc_now()

        self._collection.update_one(
            {"_id": self._as_object_id(document_id)},
            {"$set": clean_changes},
        )
        return self.find_by_id(document_id)

    def delete(self, document_id: ObjectId | str) -> bool:
        result = self._collection.delete_one({"_id": self._as_object_id(document_id)})
        return result.deleted_count == 1

    def _to_model(self, document: dict[str, Any]) -> ModelT:
        return self.model_class.model_validate(document)

    def _to_payload(self, model: ModelT | dict[str, Any]) -> dict[str, Any]:
        if isinstance(model, BaseModel):
            return model.model_dump(by_alias=True, exclude_none=True)
        return dict(model)

    def _as_object_id(self, document_id: ObjectId | str) -> ObjectId:
        if isinstance(document_id, ObjectId):
            return document_id
        if ObjectId.is_valid(document_id):
            return ObjectId(document_id)
        raise ValueError("Invalid MongoDB ObjectId")
