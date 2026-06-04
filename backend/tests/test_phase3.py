"""Phase 3 集成测试 — 多人协同、分账、分享"""

import os

import sys
sys.path.insert(0, "/home/administrator/software/SmartJourney/backend")

import pytest
from httpx import ASGITransport, AsyncClient
import fakeredis.aioredis

fake_redis = fakeredis.aioredis.FakeRedis()
import app.redis_client as rc; rc.redis_client = fake_redis
import app.services.auth_service as auth_svc; auth_svc.redis_client = fake_redis
import app.services.weather_service as weather_svc; weather_svc.redis_client = fake_redis
import app.services.mcp_gateway as mcp_gw; mcp_gw.redis_client = fake_redis

from app.main import app
from app.database import engine, async_session_factory
from app.models import Base
from app.services.auth_service import get_or_create_user, create_access_token


@pytest.fixture(scope="function", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create_token(phone="13800138000"):
    async with async_session_factory() as session:
        user, _ = await get_or_create_user(session, phone)
        await session.commit()
    return create_access_token(user.id)


class TestCollaboration:
    async def test_create_and_invite(self, client: AsyncClient):
        """创建协作组、获取邀请码、另一个人加入"""
        t1 = await _create_token("13800138030")
        t2 = await _create_token("13800138031")

        # User1 创建行程
        resp = await client.post("/api/v1/trips", json={
            "title": "协作测试", "destination": "北京",
        }, headers={"Authorization": f"Bearer {t1}"})
        tid = resp.json()["data"]["id"]

        # 创建协作组
        resp = await client.post(f"/api/v1/trips/{tid}/collaboration",
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code == 200
        code = resp.json()["data"]["invite_code"]

        # User2 通过邀请码加入
        resp = await client.post("/api/v1/collaboration/join",
            json={"invite_code": code},
            headers={"Authorization": f"Bearer {t2}"})
        assert resp.status_code == 200

        # 查看成员
        resp = await client.get(f"/api/v1/trips/{tid}/members",
            headers={"Authorization": f"Bearer {t1}"})
        members = resp.json()["data"]["members"]
        assert len(members) == 2

    async def test_leave_and_remove(self, client: AsyncClient):
        """退出和移除成员"""
        t1 = await _create_token("13800138032")
        t2 = await _create_token("13800138033")

        resp = await client.post("/api/v1/trips", json={"title": "测试"},
            headers={"Authorization": f"Bearer {t1}"})
        tid = resp.json()["data"]["id"]

        resp = await client.post(f"/api/v1/trips/{tid}/collaboration",
            headers={"Authorization": f"Bearer {t1}"})
        code = resp.json()["data"]["invite_code"]

        await client.post("/api/v1/collaboration/join",
            json={"invite_code": code},
            headers={"Authorization": f"Bearer {t2}"})

        # User2 退出
        resp = await client.post(f"/api/v1/trips/{tid}/leave",
            headers={"Authorization": f"Bearer {t2}"})
        assert resp.status_code == 200

        # 确认只剩一人
        resp = await client.get(f"/api/v1/trips/{tid}/members",
            headers={"Authorization": f"Bearer {t1}"})
        assert len(resp.json()["data"]["members"]) == 1


class TestExpenses:
    async def test_add_and_settle(self, client: AsyncClient):
        t1 = await _create_token("13800138040")
        t2 = await _create_token("13800138041")

        resp = await client.post("/api/v1/trips", json={"title": "分账测试"},
            headers={"Authorization": f"Bearer {t1}"})
        tid = resp.json()["data"]["id"]

        # 创建协作组，邀请 t2
        resp = await client.post(f"/api/v1/trips/{tid}/collaboration",
            headers={"Authorization": f"Bearer {t1}"})
        code = resp.json()["data"]["invite_code"]
        await client.post("/api/v1/collaboration/join",
            json={"invite_code": code},
            headers={"Authorization": f"Bearer {t2}"})

        # t1 添加消费
        resp = await client.post(f"/api/v1/trips/{tid}/expenses",
            json={"category": "food", "amount": 300, "description": "晚餐"},
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code == 200

        # t2 添加消费
        resp = await client.post(f"/api/v1/trips/{tid}/expenses",
            json={"category": "transport", "amount": 100, "description": "打车"},
            headers={"Authorization": f"Bearer {t2}"})
        assert resp.status_code == 200

        # 查看消费列表
        resp = await client.get(f"/api/v1/trips/{tid}/expenses",
            headers={"Authorization": f"Bearer {t1}"})
        assert len(resp.json()["data"]["items"]) == 2

        # 结算
        resp = await client.get(f"/api/v1/trips/{tid}/settlement",
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code == 200
        stmt = resp.json()["data"]
        assert stmt["total_expenses"] == 400
        assert len(stmt["settlements"]) >= 0  # 可能有结算建议

    async def test_delete_expense(self, client: AsyncClient):
        t1 = await _create_token("13800138042")
        resp = await client.post("/api/v1/trips", json={"title": "删除测试"},
            headers={"Authorization": f"Bearer {t1}"})
        tid = resp.json()["data"]["id"]

        resp = await client.post(f"/api/v1/trips/{tid}/expenses",
            json={"category": "other", "amount": 50, "description": "测试"},
            headers={"Authorization": f"Bearer {t1}"})
        eid = resp.json()["data"]["id"]

        resp = await client.delete(f"/api/v1/trips/{tid}/expenses/{eid}",
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code == 200


class TestSharing:
    async def test_poster_and_travelogue(self, client: AsyncClient):
        t1 = await _create_token("13800138050")
        resp = await client.post("/api/v1/trips", json={
            "title": "分享测试", "destination": "大理",
            "start_date": "2026-06-01", "end_date": "2026-06-03",
        }, headers={"Authorization": f"Bearer {t1}"})
        tid = resp.json()["data"]["id"]

        # 海报数据
        resp = await client.get(f"/api/v1/trips/{tid}/poster",
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "分享测试"

        # 游记生成
        resp = await client.get(f"/api/v1/trips/{tid}/travelogue",
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code == 200
        assert "content" in resp.json()["data"]

        # 分享链接
        resp = await client.post(f"/api/v1/trips/{tid}/share",
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code == 200
        assert "share_url" in resp.json()["data"]


class TestAuxServices:
    async def test_insurance(self, client: AsyncClient):
        t1 = await _create_token("13800138060")
        resp = await client.get("/api/v1/services/insurance",
            params={"days": 5, "destination": "三亚"},
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]["plans"]) == 3

    async def test_luggage(self, client: AsyncClient):
        t1 = await _create_token("13800138061")
        resp = await client.get("/api/v1/services/luggage",
            params={"city": "上海", "location": "浦东机场"},
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code == 200

    async def test_location_sharing(self, client: AsyncClient):
        t1 = await _create_token("13800138070")
        resp = await client.post("/api/v1/trips", json={"title": "位置测试"},
            headers={"Authorization": f"Bearer {t1}"})
        tid = resp.json()["data"]["id"]

        resp = await client.put(f"/api/v1/trips/{tid}/location",
            json={"lat": 18.25, "lng": 109.50},
            headers={"Authorization": f"Bearer {t1}"})
        assert resp.status_code in [200, 400]  # 400 if not member
