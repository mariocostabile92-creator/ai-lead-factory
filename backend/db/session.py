from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.db.base import Base

if settings.database_url.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    from backend.models.activity import Activity
    from backend.models.conversation import Conversation, ConversationMessage
    from backend.models.lead import Lead

    Base.metadata.create_all(bind=engine)

    if settings.database_url.startswith("sqlite"):
        with engine.begin() as connection:
            columns = {
                row[1]
                for row in connection.exec_driver_sql("PRAGMA table_info(conversations)").all()
            }
            if "openai_response_id" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE conversations ADD COLUMN openai_response_id VARCHAR(120) DEFAULT ''"
                )
