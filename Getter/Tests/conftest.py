import os
import tempfile
from pathlib import Path

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Data_Ingestion.database import Base


TEST_DATABASE_URL = "sqlite:///:memory:"


_local_tmp_root = Path(__file__).resolve().parent.parent / "pytest_tmp"
_local_tmp_root.mkdir(exist_ok=True)
os.environ.setdefault("TMP", str(_local_tmp_root))
os.environ.setdefault("TEMP", str(_local_tmp_root))
os.environ.setdefault("TMPDIR", str(_local_tmp_root))
tempfile.tempdir = str(_local_tmp_root)


engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


@pytest.fixture
def db():

    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()

    try:
        yield session

    finally:
        session.close()

    Base.metadata.drop_all(bind=engine)
