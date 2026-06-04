"""SmartJourney 测试配置 — PostgreSQL 测试数据库 + 事务回滚隔离"""

import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# pytest-asyncio: auto mode so async fixtures work without @pytest.mark.asyncio
pytest_plugins = ("pytest_asyncio",)

# --- 在所有测试模块导入前强制设置测试数据库 URL ---
# 测试使用独立的 smartjourney_test 数据库
# WSL2 环境：自动检测 Windows 宿主机 IP（Docker Desktop 端口转发到宿主机）
def _detect_pg_host() -> str:
    """检测 PostgreSQL 主机地址 — WSL2 中用 Windows 宿主机 IP"""
    # 如果显式设置了 TEST_DATABASE_URL，直接使用
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    # WSL2：通过 /etc/resolv.conf 的 nameserver 获取 Windows 宿主机 IP
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                if line.startswith("nameserver"):
                    ns = line.split()[1]
                    # 排除 systemd-resolved 的 127.0.0.53
                    if ns != "127.0.0.53":
                        return f"postgresql+asyncpg://smartjourney:smartjourney@{ns}:5432/smartjourney_test"
    except Exception:
        pass
    return "postgresql+asyncpg://postgres:smartjourney_dev@localhost:5432/smartjourney_test"

TEST_DATABASE_URL = _detect_pg_host()
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# 全局测试引擎（session 级别共享）
_test_engine = None


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """创建测试数据库引擎，自动建表"""
    global _test_engine
    if _test_engine is not None:
        yield _test_engine
        return

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # 建表
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _test_engine = engine
    yield engine

    # 清理：删表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    return async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture
async def db_session(test_session_factory):
    """每个测试函数独立事务，结束后回滚（保证测试隔离）"""
    async with test_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ============================================================
# 覆盖 app.database 的 get_db，让所有 FastAPI 路由使用测试数据库
# ============================================================

@pytest_asyncio.fixture(autouse=True)
async def override_get_db(test_session_factory):
    """自动将 FastAPI 的 get_db 替换为测试数据库会话"""
    import app.database
    orig_factory = app.database.async_session_factory
    app.database.async_session_factory = test_session_factory
    yield
    app.database.async_session_factory = orig_factory
