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
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, comment="最后更新时间")

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


# ==================== 系统配置（数据库中的运行时可变配置） ====================

class SystemConfig(Base):
    """系统配置 — 运行时可变配置，存储在数据库中，无需重启即可修改"""
    __tablename__ = "system_configs"
    __table_args__ = {"comment": "系统配置表：运行时可变配置（功能开关、缓存策略等），存储在数据库中无需重启修改"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="配置记录ID")
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, comment="配置键名")
    value: Mapped[str] = mapped_column(Text, nullable=False, comment="配置值（JSON字符串）")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="配置说明")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, comment="最后更新时间")


# ==================== Phase 3: 多人协同 ====================

class TripMember(Base):
    """行程成员 — 多人协同编辑行程的成员管理"""
    __tablename__ = "trip_members"
    __table_args__ = (
        UniqueConstraint("trip_id", "user_id", name="uq_trip_member"),
        {"comment": "行程成员表：多人协作编辑行程，支持 owner/editor/viewer 三种角色"},
    )

    ROLES = ["owner", "editor", "viewer"]

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="成员记录ID")
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, comment="所属行程ID")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="成员用户ID")
    role: Mapped[str] = mapped_column(String(20), default="editor", comment="角色：owner/editor/viewer")
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="成员昵称（冗余）")
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment="成员头像URL")
    share_location: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否共享实时位置")
    last_lat: Mapped[float | None] = mapped_column(Float, nullable=True, comment="最后纬度")
    last_lng: Mapped[float | None] = mapped_column(Float, nullable=True, comment="最后经度")
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="位置更新时间")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, comment="加入时间")
    invite_code: Mapped[str | None] = mapped_column(String(8), nullable=True, unique=True, index=True, comment="邀请码（8位，唯一）")

    trip = relationship("Trip", backref="members")
    user = relationship("User", backref="trip_memberships")


class TripExpense(Base):
    """行程消费 — 行程中的消费记录，支持多人分账"""
    __tablename__ = "trip_expenses"
    __table_args__ = {"comment": "行程消费表：行程中的消费记录，支持均分/自定义/百分比三种分账方式"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="消费记录ID")
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, comment="所属行程ID")
    paid_by_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, comment="支付人用户ID")
    category: Mapped[str] = mapped_column(String(20), nullable=False, comment="消费分类")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="消费描述")
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False, comment="消费金额（元）")
    currency: Mapped[str] = mapped_column(String(3), default="CNY", comment="货币代码")
    split_type: Mapped[str] = mapped_column(String(20), default="equal", comment="分账方式：equal/custom/percentage")
    split_details: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="分账明细（{user_id: amount}）")
    expense_date: Mapped[datetime | None] = mapped_column(Date, nullable=True, comment="消费日期")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, comment="创建时间")

    trip = relationship("Trip", backref="expenses")
    paid_by = relationship("User", backref="paid_expenses")


# ==================== Phase 4+: 钱包 & 交易 ====================

class Wallet(Base):
    """钱包 — 用户虚拟钱包，支持余额和冻结金额"""
    __tablename__ = "wallets"
    __table_args__ = {"comment": "钱包表：用户虚拟钱包，支持余额、冻结金额，一人一钱包"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="钱包ID")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, comment="所属用户ID（一对一）")
    balance: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0, comment="可用余额（元）")
    frozen_balance: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0, comment="冻结金额（元）")
    currency: Mapped[str] = mapped_column(String(3), default="CNY", comment="货币代码")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, comment="最后更新时间")

    user = relationship("User", backref="wallet", uselist=False)


class Transaction(Base):
    """交易 — 钱包交易记录（充值/支付/退款/提现/奖励）"""
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_created", "user_id", "created_at"),
        {"comment": "交易记录表：钱包交易流水，支持充值/支付/退款/提现/奖励五种类型"},
    )

    TYPE_CHARGE = "charge"       # 充值
    TYPE_PAYMENT = "payment"     # 支付
    TYPE_REFUND = "refund"       # 退款
    TYPE_WITHDRAW = "withdraw"   # 提现
    TYPE_REWARD = "reward"       # 奖励

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid, comment="交易记录ID")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True, comment="所属用户ID")
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="交易类型：charge/payment/refund/withdraw/reward")
    amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False, comment="交易金额（元）")
    balance_after: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False, comment="交易后余额（元）")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="交易描述")
    related_trip_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, comment="关联行程ID")
    status: Mapped[str] = mapped_column(String(20), default="completed", comment="状态：pending/completed/failed/cancelled")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, comment="交易时间")
