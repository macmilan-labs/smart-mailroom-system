from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base # Updated for SQLAlchemy 2.0 readiness
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./mailroom.db"
# check_same_thread: False is needed for SQLite in FastAPI as one request might interact with db in a different thread than the one it was initialized in.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def run_migrations():
    """
    Lightweight Alembic-free migration shim.
    Adds new columns to the 'users' table if they don't already exist.
    Each ALTER TABLE is wrapped in try/except so it is a safe no-op on both
    a fresh DB (create_all already created the column) and an upgraded one
    (column already exists → OperationalError is swallowed).
    """
    with engine.connect() as conn:
        for col_ddl in [
            "ALTER TABLE users ADD COLUMN face_encoding  TEXT",
            "ALTER TABLE users ADD COLUMN fingerprint_id VARCHAR",
        ]:
            try:
                conn.execute(text(col_ddl))
                conn.commit()
            except Exception:
                # Column already exists — safe to ignore
                pass


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
