import uuid

from pydantic import BaseModel, ConfigDict, Field


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    symbol: str
    sort_order: int
    children: list["CategoryRead"] = Field(default_factory=list)
