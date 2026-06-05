"""
SmartJourney（智旅）配置管理

分层配置：
1. .env 环境变量 — 启动必须配置（数据库连接、API密钥等）
2. 数据库 system_configs 表 — 运行时可变配置（功能开关、缓存策略等）
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """启动必须配置 — 全部来自环境变量 (.env)"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 应用 ----
    app_name: str = "SmartJourney（智旅）"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ---- 数据库 ----
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smartjourney"
    redis_url: str = "redis://localhost:6379/0"

    # ---- 安全 ----
    secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 604800  # 7 天

    # ---- 飞猪 FlyAI MCP ----
    flyai_api_key: str = ""
    flyai_sign_secret: str = ""

    # ---- 高德地图 ----
    gaode_api_key: str = ""

    # ---- LLM API ----
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"

    # ---- 短信 ----
    sms_provider: str = "mock"  # mock / aliyun / tencent
    sms_access_key_id: str = ""
    sms_access_key_secret: str = ""
    sms_sign_name: str = "智旅"
    sms_template_code: str = ""
    sms_region: str = "cn-shenzhen"  # 阿里云短信服务区域

    # ---- CORS ----
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost"

    # ---- MCP ----
    mcp_timeout_seconds: int = 15
    mcp_max_retries: int = 3
    mcp_cache_ttl_seconds: int = 300

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
