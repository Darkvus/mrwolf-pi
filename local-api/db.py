import os
from sqlmodel import SQLModel, create_engine, Session

DB_PATH = os.environ.get("DATABASE_PATH", "./data/mrwolf.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
