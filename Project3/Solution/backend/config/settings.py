import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Azure Configuration
    KEY_VAULT_NAME: str = "temp-project-vault"
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    
    # API Configuration
    API_VERSION: str = "v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # CORS Configuration
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:3001"]
    
    # Cache Configuration
    CACHE_TTL: int = 3600
    
    # Vector Store Collections
    ACTIVE_TICKETS_COLLECTION: str = "ActiveTickets"
    HISTORIC_TICKETS_COLLECTION: str = "HistoricTickets"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()