from pathlib import Path

from .interface import DatastoreInterface
from .local_json import LocalJSONDatastore
from .postgres import PostgresDatastore
from ..config import settings


def create_datastore() -> DatastoreInterface:
    """Factory function to create the appropriate datastore based on config."""
    if settings.DATASTORE_TYPE == "postgres":
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL must be set when using postgres datastore")
        return PostgresDatastore(settings.DATABASE_URL)
    else:
        data_dir = Path(settings.LOCAL_DATA_DIR)
        return LocalJSONDatastore(data_dir)
