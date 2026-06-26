import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import ROOT

load_dotenv(ROOT / ".env")

DEFAULT_DATABASE_URL = f"sqlite:///{ROOT / 'data' / 'job_platform.db'}"


class Base(DeclarativeBase):
    pass


@lru_cache
def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip()


def get_engine():
    url = get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
