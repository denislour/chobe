from sqlmodel import Field, SQLModel


class Record(SQLModel, table=True):
    __tablename__ = "records"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=120)
