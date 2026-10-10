from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class RecordCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)


class RecordRead(SQLModel):
    id: int
    name: str
