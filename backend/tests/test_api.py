import os

import sys
sys.path.insert(0, "/home/administrator/software/SmartJourney/backend")

import pytest
from httpx import ASGITransport, AsyncClient
import fakeredis.aioredis

# Must mock BEFORE importing app modules that use Redis
fake_redis = fakeredis.aioredis.FakeRedis()

# Patch redis in all modules that import it
import app.redis_client as rc
rc.redis_client = fake_redis

import app.services.auth_service as auth_svc
auth_svc.redis_client = fake_redis

import app.services.weather_service as weather_svc
weather_svc.redis_client = fake_redis

import app.services.mcp_gateway as mcp_gw
mcp_gw.redis_client = fake_redis

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


class TestHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAuth:
    async def test_send_code_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/send-code", json={"phone": "13800138000"})
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_send_code_invalid_phone(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/send-code", json={"phone": "12345"})
        assert resp.status_code == 422

    async def test_send_code_rate_limit(self, client: AsyncClient):
        await client.post("/api/v1/auth/send-code", json={"phone": "13800138001"})
        resp = await client.post("/api/v1/auth/send-code", json={"phone": "13800138001"})
        assert resp.status_code == 429

    async def test_login_wrong_code(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000", "code": "000000",
        })
        assert resp.status_code == 400

    async def test_me_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestTrips:
    async def test_create_trip(self, client: AsyncClient):
        token = await _create_token("13800138002")
        resp = await client.post(
            "/api/v1/trips",
            json={
                "title": "三亚亲子游", "destination": "三亚",
                "start_date": "2026-06-01", "end_date": "2026-06-05",
                "traveler_count": 3, "budget_total": 10000,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["title"] == "三亚亲子游"
        assert len(data["data"]["days"]) == 5

    async def test_list_trips(self, client: AsyncClient):
        token = await _create_token("13800138003")
        await client.post("/api/v1/trips", json={"title": "测试"}, headers={"Authorization": f"Bearer {token}"})
        resp = await client.get("/api/v1/trips", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]["items"]) >= 1

    async def test_get_trip_404(self, client: AsyncClient):
        token = await _create_token("13800138004")
        resp = await client.get("/api/v1/trips/nonexistent", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    async def test_delete_trip(self, client: AsyncClient):
        token = await _create_token("13800138005")
        resp = await client.post("/api/v1/trips", json={"title": "待删"}, headers={"Authorization": f"Bearer {token}"})
        tid = resp.json()["data"]["id"]
        resp = await client.delete(f"/api/v1/trips/{tid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_add_and_remove_item(self, client: AsyncClient):
        token = await _create_token("13800138010")
        resp = await client.post("/api/v1/trips", json={
            "title": "含项目", "start_date": "2026-06-01", "end_date": "2026-06-01",
        }, headers={"Authorization": f"Bearer {token}"})
        trip = resp.json()["data"]
        day_id = trip["days"][0]["id"]

        resp = await client.post(f"/api/v1/trips/{trip['id']}/items", json={
            "day_id": day_id, "type": "flight",
            "title": "MU5678 上海→三亚", "start_time": "08:30", "end_time": "11:45",
            "price": 890, "extra_data": {"flight_no": "MU5678"},
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        item_id = resp.json()["data"]["id"]

        resp = await client.delete(
            f"/api/v1/trips/{trip['id']}/items/{item_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_budget(self, client: AsyncClient):
        token = await _create_token("13800138011")
        resp = await client.post("/api/v1/trips", json={
            "title": "预算测试", "budget_total": 5000,
        }, headers={"Authorization": f"Bearer {token}"})
        tid = resp.json()["data"]["id"]
        resp = await client.get(f"/api/v1/trips/{tid}/budget", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["categories"]) == 5


class TestInfo:
    async def test_weather(self, client: AsyncClient):
        token = await _create_token("13800138006")
        resp = await client.get("/api/v1/info/weather", params={"city": "三亚"}, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_destination(self, client: AsyncClient):
        token = await _create_token("13800138007")
        resp = await client.get("/api/v1/info/destination/三亚", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "三亚"


class TestPreferences:
    async def test_get_empty(self, client: AsyncClient):
        token = await _create_token("13800138008")
        resp = await client.get("/api/v1/user/preferences", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "flight" in resp.json()["data"]

    async def test_save_and_get(self, client: AsyncClient):
        token = await _create_token("13800138009")
        prefs = {
            "flight": {"cabin": "business", "seat": "aisle"},
            "train": {"type_preference": "G", "seat": "一等座"},
            "hotel": {"min_stars": "5", "max_price_per_night": "1500"},
            "food": {"cuisines": "川菜", "max_price_per_person": "200"},
            "travel_pace": "relaxed",
            "interests": ["beach", "nature"],
        }
        resp = await client.put("/api/v1/user/preferences", json=prefs, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        resp = await client.get("/api/v1/user/preferences", headers={"Authorization": f"Bearer {token}"})
        assert resp.json()["data"]["flight"]["cabin"] == "business"
