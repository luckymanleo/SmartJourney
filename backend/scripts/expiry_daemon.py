#!/usr/bin/env python3
"""行程过期守护进程 — 分布式安全的单实例定时任务

特性:
  - AsyncIOScheduler: 替代裸 while sleep，支持 coalesce / misfire_grace_time
  - Redis 分布式锁: 多实例部署时只有持锁者执行任务
  - 跨平台: Linux / macOS / Windows

用法:
    python scripts/expiry_daemon.py
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.config import get_settings
from app.redis_client import _init_redis, redis_client
from app.logging_config import setup_logging
from app.services.trip_expiry import expire_past_trips

logger = logging.getLogger("expiry_daemon")

# Redis 分布式锁配置
LOCK_KEY = "lock:trip_expiry"
LOCK_TTL = 1800  # 30 分钟，与定时器间隔一致


async def acquire_lock() -> bool:
    """获取 Redis 分布式锁，TTL=30min"""
    try:
        r = await redis_client._ensure()
        got = await r.set(LOCK_KEY, str(os.getpid()), ex=LOCK_TTL, nx=True)  # type: ignore
        return bool(got)
    except Exception:
        return False


async def release_lock():
    """释放锁（仅当锁属于当前进程时）"""
    try:
        r = await redis_client._ensure()
        pid = await r.get(LOCK_KEY)
        if pid == str(os.getpid()):
            await r.delete(LOCK_KEY)
    except Exception:
        pass


async def expire_with_lock():
    """带分布式锁的过期检查 —— 只有持锁进程执行"""
    if not await acquire_lock():
        logger.debug("Lock not acquired, another instance is running")
        return
    try:
        await expire_past_trips()
    except Exception as e:
        logger.error(f"Expiry check failed: {e}")


async def main():
    settings = get_settings()
    setup_logging(settings.log_level)
    await _init_redis()

    scheduler = AsyncIOScheduler()

    # 注册监听器（执行结果日志）
    def job_listener(event):
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} completed, retval={event.retval}")

    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    scheduler.add_job(
        expire_with_lock,
        "interval",
        minutes=30,
        id="trip_expiry",
        name="行程过期检查（Redis 分布式锁）",
        coalesce=True,              # 堆积时合并，只执行最新一次
        max_instances=1,            # 同一时刻最多 1 个实例运行
        misfire_grace_time=300,     # 错过 5 分钟内仍补偿执行
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Expiry daemon started: PID={os.getpid()}, interval=30min, lock_key={LOCK_KEY}")

    # 优雅退出
    stop_event = asyncio.Event()

    def shutdown(sig=None, frame=None):
        logger.info(f"Received signal {sig}, shutting down...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, shutdown)
        except (ValueError, OSError):
            pass  # Windows 不支持 SIGTERM

    await stop_event.wait()
    scheduler.shutdown(wait=False)
    await release_lock()
    logger.info("Expiry daemon stopped")


if __name__ == "__main__":
    asyncio.run(main())
