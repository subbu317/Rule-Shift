from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings


class Base(DeclarativeBase):
    pass


def build_engine(url: str):
    opts = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    engine = create_engine(url, pool_pre_ping=True, **opts)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _pragmas(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
    return engine


engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    if settings.database_url.startswith("sqlite") and ":memory:" not in settings.database_url:
        from sqlalchemy.engine import make_url
        filename = make_url(settings.database_url).database
        if filename:
            __import__("pathlib").Path(filename).parent.mkdir(parents=True, exist_ok=True)
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
