from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _add_column_if_missing(engine: Engine, table_name: str, column_name: str, ddl_type: str) -> None:
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing:
        return
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}"))


def run_compat_migrations(engine: Engine) -> None:
    """Apply additive, backwards-compatible changes for existing installations.

    SQLAlchemy metadata.create_all() creates new tables but does not add columns to
    existing ones, so these guarded ALTERs keep deployed databases compatible
    without requiring a separate migration framework yet.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "songs" in tables:
        _add_column_if_missing(engine, "songs", "lyrics_book_hindi", "TEXT")
        _add_column_if_missing(engine, "songs", "lyrics_normalized_hindi", "TEXT")
        _add_column_if_missing(engine, "songs", "lyrics_roman", "TEXT")

    if "recordings" in tables:
        _add_column_if_missing(engine, "recordings", "start_seconds", "INTEGER")
        _add_column_if_missing(engine, "recordings", "end_seconds", "INTEGER")
