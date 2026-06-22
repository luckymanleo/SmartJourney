"""SmartJourney（智旅）FastAPI 入口"""

from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine
from app.models import Base
from app.redis_client import _init_redis
from app.api import auth, search, trips, plan, info, user
from app.api import map_routes
from app.config_loader import cors_debug_origins
from app.logging_config import setup_logging

settings = get_settings()

# 初始化日志
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    if settings.debug:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    await _init_redis()
    # 初始化远程 MCP
    from app.services.mcp_manager import init_remote_mcp
    await init_remote_mcp()
    # 启动行程过期定时任务（多 worker 模式下通过 DISABLE_EXPIRY_TASK=true 关闭，由独立守护进程执行）
    expiry_task = None
    if not settings.disable_expiry_task:
        from app.services.trip_expiry import run_periodic
        expiry_task = asyncio.create_task(run_periodic(1800))
    yield
    # 关闭时
    if expiry_task is not None:
        expiry_task.cancel()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS — debug 模式宽松，生产模式严格
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_debug_origins() if settings.debug else settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(search.router, prefix="/api/v1/search", tags=["搜索"])
app.include_router(trips.router, prefix="/api/v1/trips", tags=["行程"])
app.include_router(plan.router, prefix="/api/v1/plan", tags=["智能规划"])
app.include_router(info.router, prefix="/api/v1/info", tags=["辅助信息"])
app.include_router(user.router, prefix="/api/v1/user", tags=["用户偏好"])
app.include_router(map_routes.router, prefix="/api/v1/map", tags=["地图"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": settings.app_version}
