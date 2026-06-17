"""数据库模型 — SQLAlchemy ORM"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Date, Time, Text, DateTime,
    Boolean, ForeignKey, JSON, DECIMAL, Index, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()


# ==================== 用户 ====================

class User(Base):
    """用户 — 手机号注册登录，支持昵称和头像"""
    __tablename__ = "users"
    __table_args__ = {"comment": "用户表：手机号注册登录，支持昵称和头像"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="用户唯一ID")
    phone: Mapped[str] = mapped_column(String(11), unique=True, nullable=False, index=True, comment="手机号（11位，唯一）")
    nickname: Mapped[str] = mapped_column(String(50), default="旅行者", comment="用户昵称")
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment="头像URL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, comment="注册时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, comment="最后更新时间")

    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")


# ==================== 用户偏好 ====================

class UserPreference(Base):
    """用户偏好 — 键值对形式存储个性化设置"""
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category", "key", name="uq_user_pref"),
        {"comment": "用户偏好表：键值对形式存储个性化设置，按 category+key 分组"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="偏好记录ID")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID")
    category: Mapped[str] = mapped_column(String(50), nullable=False, comment="偏好分类（如 travel_style, budget, display）")
    key: Mapped[str] = mapped_column(String(50), nullable=False, comment="偏好键名")
    value: Mapped[str] = mapped_column(Text, nullable=False, comment="偏好值（JSON字符串）")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, comment="创建时间")

    user = relationship("User", back_populates="preferences")


# ==================== 行程 ====================

class Trip(Base):
    """行程 — 一次完整的旅行计划，包含多天行程安排"""
    __tablename__ = "trips"
    __table_args__ = (
        Index("ix_trips_user_status", "user_id", "status"),
        {"comment": "行程表：一次完整的旅行计划，包含出发地、目的地、日期、人数、预算"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="行程唯一ID")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="行程标题（如：深圳→上海 5人4日游）")
    status: Mapped[str] = mapped_column(String(20), default="planning", index=True, comment="行程状态：planning/active/completed/cancelled/expired")
    origin: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="出发地城市")
    destination: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="目的地城市")
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True, comment="出发日期")
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True, comment="返程日期")
    traveler_count: Mapped[int] = mapped_column(Integer, default=1, comment="出行人数")
    budget_total: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True, comment="总预算（元）")
    cover_image: Mapped[str | None] = mapped_column(Text, nullable=True, comment="封面图URL")
    route_tag: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="路线策略标签（经济/舒适/快速）")
    weather_info: Mapped[str | None] = mapped_column(Text, nullable=True, comment="出行期间天气摘要")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="行程概要（2-3句话）")
    tips: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="出行提示列表")
    special_notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="特殊说明（花粉过敏、素食等）")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, comment="最后更新时间")
    sort_seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("nextval('trips_sort_seq_seq'::regclass)"),
        comment="自增排序序号（BIGSERIAL），替代 updated_at 做可靠的插入顺序排序"
    )

    user = relationship("User", back_populates="trips")
    days = relationship("TripDay", back_populates="trip", cascade="all, delete-orphan", order_by="TripDay.day_number")
    budgets = relationship("Budget", back_populates="trip", cascade="all, delete-orphan")


# ==================== 每日行程 ====================

class TripDay(Base):
    """行程日 — 行程中的每一天安排"""
    __tablename__ = "trip_days"
    __table_args__ = (
        UniqueConstraint("trip_id", "day_number", name="uq_trip_day_number"),
        {"comment": "行程日表：行程中的每一天，包含日期和天气信息"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="行程日ID")
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, comment="所属行程ID")
    day_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="第几天（从1开始）")
    date: Mapped[datetime | None] = mapped_column(Date, nullable=True, comment="具体日期")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="当日备注")
    weather: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="当日天气（如：晴 25°C）")

    trip = relationship("Trip", back_populates="days")
    items = relationship("TripItem", back_populates="day", cascade="all, delete-orphan", order_by="TripItem.sort_order")


# ==================== 行程项 ====================

class TripItem(Base):
    """行程项 — 行程中每一天的具体活动（交通/酒店/景点/餐饮/其他）"""
    __tablename__ = "trip_items"
    __table_args__ = {"comment": "行程项表：行程中每一天的具体活动，支持10种类型（flight/train/hotel/poi/food/transport/bus/car_rental/ferry/other）"}

    ITEM_TYPES = [
        "flight", "train", "hotel", "poi", "food",
        "transport", "bus", "car_rental", "ferry", "other"
    ]

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="行程项ID")
    trip_day_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trip_days.id", ondelete="CASCADE"), nullable=False, comment="所属行程日ID")
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True, comment="类型：flight/train/hotel/poi/food/transport/bus/car_rental/ferry/other")
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="项目标题")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="项目描述")
    start_time: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="开始时间 HH:MM 或 HH:MM(+1)")
    end_time: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="结束时间 HH:MM 或 HH:MM(+1)")
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="持续时长（分钟）")
    location: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="地点地址")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True, comment="纬度")
    lng: Mapped[float | None] = mapped_column(Float, nullable=True, comment="经度")
    price: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True, comment="预估价格（元）")
    currency: Mapped[str] = mapped_column(String(3), default="CNY", comment="货币代码")
    booking_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment="预订链接")
    booking_ref: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="预订编号")
    source: Mapped[str] = mapped_column(String(20), default="fliggy", comment="数据来源：fliggy/meituan/hotel_smart")
    status: Mapped[str] = mapped_column(String(20), default="planned", comment="状态：planned/booked/completed/cancelled")
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="扩展数据（JSON）")
    photos: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="POI 照片 URL 列表")
    amap_poi_id: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="高德地图 POI ID")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="当天排序序号")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, comment="创建时间")

    day = relationship("TripDay", back_populates="items")


# ==================== 预算 ====================

class Budget(Base):
    """预算 — 行程按分类的预算和实际支出"""
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("trip_id", "category", name="uq_budget_category"),
        {"comment": "预算表：行程按分类（transport/lodging/food/tickets/other）的预算和实际支出"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="预算记录ID")
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, comment="所属行程ID")
    category: Mapped[str] = mapped_column(String(20), nullable=False, comment="预算分类：transport/lodging/food/tickets/other")
    estimated: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0, comment="预算金额（元）")
    actual: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0, comment="实际支出（元）")
    currency: Mapped[str] = mapped_column(String(3), default="CNY", comment="货币代码")

    trip = relationship("Trip", back_populates="budgets")
