import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from product_recommendation import models  # noqa: F401
from product_recommendation.database import get_session
from product_recommendation.main import app


@pytest.fixture
def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'api.sqlite3'}")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def create_tables():
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)

    asyncio.run(create_tables())

    async def override_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_create_and_list_records(client):
    created = client.post("/v1/records", json={"name": "example"})
    listed = client.get("/v1/records")

    assert created.status_code == 201
    assert created.json() == {"id": 1, "name": "example"}
    assert listed.json() == [{"id": 1, "name": "example"}]


def test_create_rejects_unknown_fields(client):
    response = client.post("/v1/records", json={"name": "example", "secret": "hidden"})

    assert response.status_code == 422
