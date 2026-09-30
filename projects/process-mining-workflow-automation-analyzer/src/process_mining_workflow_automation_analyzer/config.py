from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings read from ``PROCESS_MINING_*`` environment variables.

    No credentials have defaults. Leave ``PROCESS_MINING_DATABASE_URL`` unset for the
    in-memory local mode, or set it to a SQLAlchemy URL, for example
    ``sqlite:///./.local/state.sqlite3`` or
    ``postgresql+psycopg2://<user>:<password>@<host>:5432/<database>``.
    """

    model_config = SettingsConfigDict(env_prefix="PROCESS_MINING_", env_file=".env", extra="ignore")

    env: str = "local"
    log_level: str = "INFO"
    database_url: Optional[str] = None


settings = Settings()
