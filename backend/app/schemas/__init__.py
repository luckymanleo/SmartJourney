"""Pydantic 请求/响应模型"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 认证 ====================

class SendCodeRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    platform: str = Field(default="mobile", description="平台标识: pc / mobile")


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=4, max_length=6)
    platform: str = Field(default="mobile", description="平台标识: pc / mobile")


class UserResponse(BaseModel):
    id: str
    phone: str
    nickname: str
    avatar_url: Optional[str] = None
    is_new: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


# ==================== 搜索 ====================

class FlightSearchParams(BaseModel):
    from_city: str = Field(..., alias="from")
    to: str
    date_city: str = Field(..., alias="date")
    source: str = "fliggy"
    cabin: Optional[str] = None
    sort_by: Optional[str] = "price"
    direct_only: bool = False


class TrainSearchParams(BaseModel):
    from_city: str = Field(..., alias="from")
    to: str
    date_city: str = Field(..., alias="date")
    source: str = "fliggy"
    train_type: Optional[str] = None
    seat_type: Optional[str] = None


class HotelSearchParams(BaseModel):
    city: str
    keyword: Optional[str] = None
    source: str = "fliggy"
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    star_min: Optional[int] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    brand: Optional[str] = None
    sort_by: Optional[str] = "rating"


class POISearchParams(BaseModel):
    city: str
    keyword: Optional[str] = None
    source: str = "fliggy"


class FoodSearchParams(BaseModel):
    city: str
    keyword: Optional[str] = None
    source: str = "fliggy"
    price_min: Optional[float] = None
    price_max: Optional[float] = None


class TransportSearchParams(BaseModel):
    from_location: str = Field(..., alias="from")
    to: str
    city: Optional[str] = None
    source: str = "fliggy"


# ==================== 行程 ====================

class TripCreateRequest(BaseModel):
    title: str = Field(..., max_length=200)
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    traveler_count: int = Field(default=1, ge=1)
    budget_total: Optional[float] = None


class TripUpdateRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    traveler_count: Optional[int] = None
    budget_total: Optional[float] = None
    notes: Optional[str] = None


class TripItemCreateRequest(BaseModel):
    day_id: str
    type: str
    title: str = Field(..., max_length=300)
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    price: Optional[float] = None
    currency: str = "CNY"
    booking_url: Optional[str] = None
    booking_ref: Optional[str] = None
    source: str = "fliggy"
    extra_data: Optional[dict] = None
    sort_order: int = 0


class TripItemResponse(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    price: Optional[float] = None
    currency: str = "CNY"
    booking_url: Optional[str] = None
    booking_ref: Optional[str] = None
    source: str = "fliggy"
    status: str = "planned"
    extra_data: Optional[dict] = None
    photos: Optional[list] = None
    amap_poi_id: Optional[str] = None
    sort_order: int = 0

    model_config = {"from_attributes": True}


class TripDayResponse(BaseModel):
    id: str
    day_number: int
    date: Optional[date] = None
    notes: Optional[str] = None
    weather: Optional[str] = None
    items: list[TripItemResponse] = []

    model_config = {"from_attributes": True}


class BudgetCategoryResponse(BaseModel):
    category: str
    estimated: float
    actual: float
    currency: str = "CNY"

    model_config = {"from_attributes": True}


class TripResponse(BaseModel):
    id: str
    title: str
    status: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    traveler_count: int
    budget_total: Optional[float] = None
    cover_image: Optional[str] = None
    route_tag: Optional[str] = None      # 路线策略标签
    weather_info: Optional[str] = None   # 天气摘要
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    days: list[TripDayResponse] = []

    model_config = {"from_attributes": True}


class TripListResponse(BaseModel):
    items: list[TripResponse]
    total: int


# ==================== AI 规划 ====================

class GeneratePlanRequest(BaseModel):
    query: str = Field(..., description="自然语言出行需求")
    origin: Optional[str] = None     # 出发地
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    traveler_count: int = Field(default=1, ge=1)
    budget_total: Optional[float] = None
    preferences: Optional[dict] = None
    save_as_trip: bool = True
    use_weather: bool = True         # 是否参考天气因素（默认开启）
    route_count: int = Field(default=1, ge=1, le=3)  # 生成路线数量（默认1条）
    route_strategy: int = Field(default=-1, ge=-1, le=2)  # -1=全部, 0=经济, 1=舒适, 2=最快
    special_notes: Optional[str] = None  # 特殊说明（花粉过敏、素食等）


class OptimizePlanRequest(BaseModel):
    trip_id: str
    instruction: str


# ==================== 用户偏好 ====================

class UserPreferencesResponse(BaseModel):
    use_weather: bool = True
    route_strategy: int = -1


# ==================== 通用响应 ====================

class APIResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[dict | list] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    code: int
    message: str
    error: ErrorDetail
