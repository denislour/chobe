from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from product_recommendation.database import get_session
from product_recommendation.models import Record
from product_recommendation.schemas import RecordCreate, RecordRead

router = APIRouter(prefix="/v1/records", tags=["records"])


@router.post("", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
async def create_record(
    payload: RecordCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RecordRead:
    record = Record.model_validate(payload)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return RecordRead.model_validate(record)


@router.get("", response_model=list[RecordRead])
async def list_records(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[RecordRead]:
    result = await session.exec(select(Record).order_by(Record.id))
    return [RecordRead.model_validate(record) for record in result.all()]
