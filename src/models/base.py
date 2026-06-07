from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import core_schema


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Any,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, value: Any) -> ObjectId:
        if isinstance(value, ObjectId):
            return value
        if isinstance(value, str) and ObjectId.is_valid(value):
            return ObjectId(value)
        raise ValueError("Invalid MongoDB ObjectId")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MongoModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: PyObjectId | None = Field(default=None, alias="_id")

    def to_mongo(self, exclude_none: bool = True) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=exclude_none)
