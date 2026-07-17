"""Configuration management for SOLVENS CORE.

Handles environment variables and settings with Pydantic.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from solvens.core.types import ProviderType


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables.
    See .env.example for available options.
    
    Attributes:
        app_name: Application name
        app_version: Application version
        debug: Enable debug mode
        log_level: Logging level
        data_dir: Directory for data storage
        providers: Enabled provider types
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SOLVENS CORE"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Paths
    data_dir: Path = Path.home() / ".solvens"
    cache_dir: Path = Path.home() / ".cache" / "solvens"
    
    # Providers
    enabled_providers: list[ProviderType] = Field(default_factory=list)
    
    # API Keys (loaded from environment, never stored)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    deepseek_api_key: str | None = None
    grok_api_key: str | None = None
    sakana_api_key: str | None = None
    pollo_ai_api_key: str | None = None
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    
    # Agent Configuration
    max_concurrent_agents: int = 10
    task_timeout: int = 300  # seconds
    max_retries: int = 3
    
    # Memory Configuration
    memory_backend: Literal["sqlite", "redis", "memory"] = "memory"
    redis_url: str | None = None
    
    # Router Configuration
    default_provider: ProviderType = ProviderType.OPENAI
    fallback_provider: ProviderType = ProviderType.OLLAMA
    cost_optimization: bool = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_provider_api_key(self, provider_type: ProviderType) -> str | None:
        """Get API key for a specific provider.
        
        Args:
            provider_type: The provider type
            
        Returns:
            API key if configured, None otherwise
        """
        key_map = {
            ProviderType.OPENAI: self.openai_api_key,
            ProviderType.ANTHROPIC: self.anthropic_api_key,
            ProviderType.GOOGLE: self.google_api_key,
            ProviderType.DEEPSEEK: self.deepseek_api_key,
            ProviderType.GROK: self.grok_api_key,
            ProviderType.SAKANA: self.sakana_api_key,
            ProviderType.POLLO_AI: self.pollo_ai_api_key,
        }
        return key_map.get(provider_type)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Singleton settings instance
    """
    return Settings()
