from pathlib import Path
import logging

from .interface import DatastoreInterface
from .local_json import LocalJSONDatastore
from .postgres import PostgresDatastore
from ..config import settings

logger = logging.getLogger(__name__)


def create_datastore() -> DatastoreInterface:
    """Factory function to create the appropriate datastore based on config."""
    logger.info(f"Initializing datastore: type={settings.DATASTORE_TYPE}")

    if settings.DATASTORE_TYPE == "postgres":
        if not settings.DATABASE_URL:
            logger.error("PostgreSQL selected but DATABASE_URL is empty")
            raise ValueError("DATABASE_URL must be set when using postgres datastore")

        # Extract host from URL for logging (hide credentials)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(settings.DATABASE_URL)
            host_info = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
            logger.info(f"Creating PostgreSQL datastore (host={host_info})")
        except Exception:
            logger.info("Creating PostgreSQL datastore")

        return PostgresDatastore(settings.DATABASE_URL)
    else:
        data_dir = Path(settings.LOCAL_DATA_DIR)
        logger.info(f"Creating local JSON datastore (path={data_dir})")
        return LocalJSONDatastore(data_dir)
