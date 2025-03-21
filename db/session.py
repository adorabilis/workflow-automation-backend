from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from core.config import DATABASE_URL

engine = create_engine(DATABASE_URL)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
