"""
行程过期定时任务 — 每30分钟检查一次，将 end_date 已过的行程状态更新为 "expired"

SQLite 兼容：使用 SQLAlchemy Core，避免 ORM 关系加载问题
"""

import asyncio
import logging
from datetime import datetime, date

from sqlalchemy import text

from app.database import async_session_factory

logger = logging.getLogger(__name__)


async def expire_past_trips():
    """将 end_date < 今天的行程状态设为 expired"""
    today = date.today()
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE trips SET status = 'expired', updated_at = :now "
                    "WHERE status = 'active' AND end_date IS NOT NULL AND end_date < :today"
                ),
                {"now": datetime.utcnow(), "today": today},
            )
            await session.commit()
            count = result.rowcount
            if count:
                logger.info(f"Trip expiration: {count} trips set to expired")
            return count
    except Exception as e:
        logger.error(f"Trip expiration job failed: {e}")
        return 0


async def run_periodic(interval_seconds: int = 1800):
    """后台循环：每 N 秒执行一次过期检查"""
    logger.info(f"Trip expiration scheduler started (interval={interval_seconds}s)")
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await expire_past_trips()
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
