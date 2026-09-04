import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Geo3D Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://geo3d:geo3dpass@localhost:5432/geo3d"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # API
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    # Storage
    DATA_DIR: str = os.environ.get(
        "DATA_DIR",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    )
    RAW_DIR: str = ""
    PROCESSED_DIR: str = ""
    TERRAIN_DIR: str = ""
    TILES_DIR: str = ""

    # Cesium
    CESIUM_ION_TOKEN: str = ""

    # Processing
    MAX_UPLOAD_SIZE_MB: int = 2048
    PROCESSING_WORKERS: int = 2

    # ODM/WebODM
    WEBODM_URL: str = ""
    WEBODM_USERNAME: str = ""
    WEBODM_PASSWORD: str = ""

    # AI
    AI_ENABLED: bool = True
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def model_post_init(self, __context):
        if not self.RAW_DIR:
            self.RAW_DIR = os.path.join(self.DATA_DIR, "raw")
        if not self.PROCESSED_DIR:
            self.PROCESSED_DIR = os.path.join(self.DATA_DIR, "processed")
        if not self.TERRAIN_DIR:
            self.TERRAIN_DIR = os.path.join(self.DATA_DIR, "terrain")
        if not self.TILES_DIR:
            self.TILES_DIR = os.path.join(self.DATA_DIR, "tiles")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
