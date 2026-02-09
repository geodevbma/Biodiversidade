import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Em produção, configure via variável de ambiente.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://bio_user:aMb!secv3c%40@69.64.32.23/biodiversidade",
)


def _make_engine(url: str):
    # SQLite precisa de check_same_thread=False quando usado com TestClient.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


engine = _make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
