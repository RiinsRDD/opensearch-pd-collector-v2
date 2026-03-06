from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "PDN Collector V2"
    VERSION: str = "2.0.0"
    
    # OpenSearch Settings
    OPENSEARCH_URL: str = "https://es-od.usvc.global.bcs"
    OS_USERNAME: str = ""
    OS_PASSWORD: str = ""
    OS_VERIFY_CERTS: bool = False
    
    # PostgreSQL Database
    POSTGRES_USER: str = "pdn_user"
    POSTGRES_PASSWORD: str = "pdn_password"
    POSTGRES_DB: str = "pdn_collector"
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: int = 5432
    
    # Log files
    LOG_DIR: Path = Path("logs")
    RUN_LOG_NAME: str = "run.log"
    ERR_LOG_NAME: str = "errors.log"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def DATABASE_URL_ASYNC(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
