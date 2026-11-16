from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/ruleshift.db"
    data_dir: Path = Path("./data")
    frontend_origin: str = "http://localhost:5173"
    max_upload_mb: int = 12
    max_pdf_pages: int = 80
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
