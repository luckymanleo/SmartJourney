"""
SmartJourney（智旅）配置管理

分层配置：
1. .env 环境变量 — 启动必须配置（数据库连接、API密钥等）
2. 数据库 system_configs 表 — 运行时可变配置（功能开关、缓存策略等）
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 绝对路径 — 多 worker 模式下 CWD 可能变
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """启动必须配置 — 全部来自环境变量 (.env)，无硬编码默认值"""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 应用 ----
    app_name: str
    app_version: str
    debug: bool = False
    log_level: str = "INFO"
    disable_expiry_task: bool = False  # 多 worker 模式下设为 true，由独立守护进程执行

    # ---- 数据库 ----
    database_url: str
    redis_url: str
    redis_username: str = ""
    redis_password: str = ""

    @property
    def redis_connection_url(self) -> str:
        """构建带认证的 Redis 连接 URL"""
        if self.redis_username or self.redis_password:
            from urllib.parse import urlparse, urlunparse

            parts = urlparse(self.redis_url)
            userinfo = ""
            if self.redis_username:
                userinfo = self.redis_username
            if self.redis_password:
                userinfo += f":{self.redis_password}"
            netloc = f"{userinfo}@{parts.hostname}"
            if parts.port:
                netloc += f":{parts.port}"
            return urlunparse(
                (parts.scheme, netloc, parts.path, parts.params, parts.query, parts.fragment)
            )
        return self.redis_url

    # ---- 安全 ----
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 604800  # 7 天

    # ---- 飞猪 FlyAI MCP ----
    flyai_api_key: str = ""
    flyai_sign_secret: str = ""

    # ---- 远程 MCP ----
    mcp_fliggy_url: str = ""

    # ---- 高德地图 ----
    gaode_api_key: str = ""

    # ---- LLM API ----
    llm_api_key: str = ""
    llm_base_url: str
    llm_model: str

    # ---- 短信 ----
    sms_provider: str = "mock"
    sms_access_key_id: str = ""
    sms_access_key_secret: str = ""
    sms_sign_name: str = ""
    sms_template_code: str = ""
    sms_region: str

    # ---- CORS ----
    cors_origins: str

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
