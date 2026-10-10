import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command


def test_alembic_upgrade_creates_service_schema(tmp_path, monkeypatch):
    database = tmp_path / "migration.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database}")
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))

    command.upgrade(config, "head")
    command.check(config)

    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
        current = connection.execute("SELECT version_num FROM alembic_version").fetchall()
    assert {"alembic_version", "records"} <= tables
    assert current == [("0001",)]
    with sqlite3.connect(database) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(records)")]
    assert columns == ["id", "name"]

    command.downgrade(config, "base")
    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert "records" not in tables

    command.upgrade(config, "head")
    command.check(config)
