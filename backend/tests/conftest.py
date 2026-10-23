import os
import tempfile

import pytest


@pytest.fixture()
def temp_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("DATABASE_PATH", path)
    from app.database import db

    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass
