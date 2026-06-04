"""数据库模型 — SQLAlchemy ORM"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Date, Time, Text, DateTime,
    Boolean, ForeignKey, JSON, DECIMAL, Index, UniqueConstraint,
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
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    phone: Mapped[str] = mapped_column(String(11), unique=True, nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(50), default="旅行者")
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")


# ==================== 用户偏好 ====================

class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category", "key", name="uq_user_pref"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="preferences")


# ==================== 行程 ====================

class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        Index("ix_trips_user_status", "user_id", "status"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="planning", index=True)
    origin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    traveler_count: Mapped[int] = mapped_column(Integer, default=1)
    budget_total: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    cover_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)    # 路线策略标签
    weather_info: Mapped[str | None] = mapped_column(Text, nullable=True)       # 天气摘要
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="trips")
    days = relationship("TripDay", back_populates="trip", cascade="all, delete-orphan", order_by="TripDay.day_number")
    budgets = relationship("Budget", back_populates="trip", cascade="all, delete-orphan")


# ==================== 每日行程 ====================

class TripDay(Base):
    __tablename__ = "trip_days"
    __table_args__ = (
        UniqueConstraint("trip_id", "day_number", name="uq_trip_day_number"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    weather: Mapped[str | None] = mapped_column(String(50), nullable=True)

    trip = relationship("Trip", back_populates="days")
    items = relationship("TripItem", back_populates="day", cascade="all, delete-orphan", order_by="TripItem.sort_order")


# ==================== 行程项 ====================

class TripItem(Base):
    __tablename__ = "trip_items"

    ITEM_TYPES = [
        "flight", "train", "hotel", "poi", "food",
        "transport", "bus", "car_rental", "ferry", "other"
    ]

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    trip_day_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trip_days.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # HH:MM
    end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    booking_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    booking_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="fliggy")
    status: Mapped[str] = mapped_column(String(20), default="planned")
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    day = relationship("TripDay", back_populates="items")


# ==================== 预算 ====================

class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("trip_id", "category", name="uq_budget_category"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    estimated: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0)
    actual: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")

    trip = relationship("Trip", back_populates="budgets")


# ==================== 系统配置（数据库中的运行时可变配置） ====================

class SystemConfig(Base):
    """运行时可变配置 — 存储在数据库中，无需重启即可修改"""
    __tablename__ = "system_configs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ==================== Phase 3: 多人协同 ====================

class TripMember(Base):
    """行程组成员"""
    __tablename__ = "trip_members"
    __table_args__ = (
        UniqueConstraint("trip_id", "user_id", name="uq_trip_member"),
    )

    ROLES = ["owner", "editor", "viewer"]

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), default="editor")
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    share_location: Mapped[bool] = mapped_column(Boolean, default=False)
    last_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    invite_code: Mapped[str | None] = mapped_column(String(8), nullable=True, unique=True, index=True)

    trip = relationship("Trip", backref="members")
    user = relationship("User", backref="trip_memberships")


class TripExpense(Base):
    """行程消费记录（用于分账）"""
    __tablename__ = "trip_expenses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    paid_by_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    split_type: Mapped[str] = mapped_column(String(20), default="equal")  # equal / custom / percentage
    split_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {user_id: amount} for custom split
    expense_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    trip = relationship("Trip", backref="expenses")
    paid_by = relationship("User", backref="paid_expenses")


# ==================== Phase 4+: 钱包 & 交易 ====================

class Wallet(Base):
    """用户钱包"""
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    balance: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    frozen_balance: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", backref="wallet", uselist=False)


class Transaction(Base):
    """交易记录"""
    __tablename__ = "transactions"

    TYPE_CHARGE = "charge"       # 充值
    TYPE_PAYMENT = "payment"     # 支付
    TYPE_REFUND = "refund"       # 退款
    TYPE_WITHDRAW = "withdraw"   # 提现
    TYPE_REWARD = "reward"       # 奖励

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    balance_after: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    related_trip_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
