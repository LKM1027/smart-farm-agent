import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Database file at project root: smartfarm.db
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_FILE_PATH = os.path.join(ROOT_DIR, "smartfarm.db")
DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy Session, ensuring it's closed after use."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
