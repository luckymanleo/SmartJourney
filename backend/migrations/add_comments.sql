-- SmartJourney 数据库表/列注释
-- 执行: psql -U smartjourney -d smartjourney -f add_comments.sql

-- ==================== users ====================
COMMENT ON TABLE users IS '用户表：手机号注册登录，支持昵称和头像';
COMMENT ON COLUMN users.id IS '用户唯一ID';
COMMENT ON COLUMN users.phone IS '手机号（11位，唯一）';
COMMENT ON COLUMN users.nickname IS '用户昵称';
COMMENT ON COLUMN users.avatar_url IS '头像URL';
COMMENT ON COLUMN users.created_at IS '注册时间';
COMMENT ON COLUMN users.updated_at IS '最后更新时间';

-- ==================== user_preferences ====================
COMMENT ON TABLE user_preferences IS '用户偏好表：键值对形式存储个性化设置，按 category+key 分组';
COMMENT ON COLUMN user_preferences.id IS '偏好记录ID';
COMMENT ON COLUMN user_preferences.user_id IS '所属用户ID';
COMMENT ON COLUMN user_preferences.category IS '偏好分类（如 travel_style, budget, display）';
COMMENT ON COLUMN user_preferences.key IS '偏好键名';
COMMENT ON COLUMN user_preferences.value IS '偏好值（JSON字符串）';
COMMENT ON COLUMN user_preferences.created_at IS '创建时间';

-- ==================== trips ====================
COMMENT ON TABLE trips IS '行程表：一次完整的旅行计划，包含出发地、目的地、日期、人数、预算';
COMMENT ON COLUMN trips.id IS '行程唯一ID';
COMMENT ON COLUMN trips.user_id IS '所属用户ID';
COMMENT ON COLUMN trips.title IS '行程标题（如：深圳→上海 5人4日游）';
COMMENT ON COLUMN trips.status IS '行程状态：planning/active/completed/cancelled/expired';
COMMENT ON COLUMN trips.origin IS '出发地城市';
COMMENT ON COLUMN trips.destination IS '目的地城市';
COMMENT ON COLUMN trips.start_date IS '出发日期';
COMMENT ON COLUMN trips.end_date IS '返程日期';
COMMENT ON COLUMN trips.traveler_count IS '出行人数';
COMMENT ON COLUMN trips.budget_total IS '总预算（元）';
COMMENT ON COLUMN trips.cover_image IS '封面图URL';
COMMENT ON COLUMN trips.route_tag IS '路线策略标签（经济/舒适/快速）';
COMMENT ON COLUMN trips.weather_info IS '出行期间天气摘要';
COMMENT ON COLUMN trips.notes IS '备注';
COMMENT ON COLUMN trips.created_at IS '创建时间';
COMMENT ON COLUMN trips.updated_at IS '最后更新时间';

-- ==================== trip_days ====================
COMMENT ON TABLE trip_days IS '行程日表：行程中的每一天，包含日期和天气信息';
COMMENT ON COLUMN trip_days.id IS '行程日ID';
COMMENT ON COLUMN trip_days.trip_id IS '所属行程ID';
COMMENT ON COLUMN trip_days.day_number IS '第几天（从1开始）';
COMMENT ON COLUMN trip_days.date IS '具体日期';
COMMENT ON COLUMN trip_days.notes IS '当日备注';
COMMENT ON COLUMN trip_days.weather IS '当日天气（如：晴 25°C）';

-- ==================== trip_items ====================
COMMENT ON TABLE trip_items IS '行程项表：行程中每一天的具体活动，支持10种类型（flight/train/hotel/poi/food/transport/bus/car_rental/ferry/other）';
COMMENT ON COLUMN trip_items.id IS '行程项ID';
COMMENT ON COLUMN trip_items.trip_day_id IS '所属行程日ID';
COMMENT ON COLUMN trip_items.type IS '类型：flight/train/hotel/poi/food/transport/bus/car_rental/ferry/other';
COMMENT ON COLUMN trip_items.title IS '项目标题';
COMMENT ON COLUMN trip_items.description IS '项目描述';
COMMENT ON COLUMN trip_items.start_time IS '开始时间 HH:MM';
COMMENT ON COLUMN trip_items.end_time IS '结束时间 HH:MM';
COMMENT ON COLUMN trip_items.duration_minutes IS '持续时长（分钟）';
COMMENT ON COLUMN trip_items.location IS '地点地址';
COMMENT ON COLUMN trip_items.lat IS '纬度';
COMMENT ON COLUMN trip_items.lng IS '经度';
COMMENT ON COLUMN trip_items.price IS '预估价格（元）';
COMMENT ON COLUMN trip_items.currency IS '货币代码';
COMMENT ON COLUMN trip_items.booking_url IS '预订链接';
COMMENT ON COLUMN trip_items.booking_ref IS '预订编号';
COMMENT ON COLUMN trip_items.source IS '数据来源：fliggy/meituan/hotel_smart';
COMMENT ON COLUMN trip_items.status IS '状态：planned/booked/completed/cancelled';
COMMENT ON COLUMN trip_items.extra_data IS '扩展数据（JSON）';
COMMENT ON COLUMN trip_items.sort_order IS '当天排序序号';
COMMENT ON COLUMN trip_items.created_at IS '创建时间';

-- ==================== budgets ====================
COMMENT ON TABLE budgets IS '预算表：行程按分类（transport/lodging/food/tickets/other）的预算和实际支出';
COMMENT ON COLUMN budgets.id IS '预算记录ID';
COMMENT ON COLUMN budgets.trip_id IS '所属行程ID';
COMMENT ON COLUMN budgets.category IS '预算分类：transport/lodging/food/tickets/other';
COMMENT ON COLUMN budgets.estimated IS '预算金额（元）';
COMMENT ON COLUMN budgets.actual IS '实际支出（元）';
COMMENT ON COLUMN budgets.currency IS '货币代码';

-- ==================== system_configs ====================
COMMENT ON TABLE system_configs IS '系统配置表：运行时可变配置（功能开关、缓存策略等），存储在数据库中无需重启修改';
COMMENT ON COLUMN system_configs.id IS '配置记录ID';
COMMENT ON COLUMN system_configs.key IS '配置键名';
COMMENT ON COLUMN system_configs.value IS '配置值（JSON字符串）';
COMMENT ON COLUMN system_configs.description IS '配置说明';
COMMENT ON COLUMN system_configs.updated_at IS '最后更新时间';

-- ==================== trip_members ====================
COMMENT ON TABLE trip_members IS '行程成员表：多人协作编辑行程，支持 owner/editor/viewer 三种角色';
COMMENT ON COLUMN trip_members.id IS '成员记录ID';
COMMENT ON COLUMN trip_members.trip_id IS '所属行程ID';
COMMENT ON COLUMN trip_members.user_id IS '成员用户ID';
COMMENT ON COLUMN trip_members.role IS '角色：owner/editor/viewer';
COMMENT ON COLUMN trip_members.nickname IS '成员昵称（冗余）';
COMMENT ON COLUMN trip_members.avatar_url IS '成员头像URL';
COMMENT ON COLUMN trip_members.share_location IS '是否共享实时位置';
COMMENT ON COLUMN trip_members.last_lat IS '最后纬度';
COMMENT ON COLUMN trip_members.last_lng IS '最后经度';
COMMENT ON COLUMN trip_members.location_updated_at IS '位置更新时间';
COMMENT ON COLUMN trip_members.joined_at IS '加入时间';
COMMENT ON COLUMN trip_members.invite_code IS '邀请码（8位，唯一）';

-- ==================== trip_expenses ====================
COMMENT ON TABLE trip_expenses IS '行程消费表：行程中的消费记录，支持均分/自定义/百分比三种分账方式';
COMMENT ON COLUMN trip_expenses.id IS '消费记录ID';
COMMENT ON COLUMN trip_expenses.trip_id IS '所属行程ID';
COMMENT ON COLUMN trip_expenses.paid_by_user_id IS '支付人用户ID';
COMMENT ON COLUMN trip_expenses.category IS '消费分类';
COMMENT ON COLUMN trip_expenses.description IS '消费描述';
COMMENT ON COLUMN trip_expenses.amount IS '消费金额（元）';
COMMENT ON COLUMN trip_expenses.currency IS '货币代码';
COMMENT ON COLUMN trip_expenses.split_type IS '分账方式：equal/custom/percentage';
COMMENT ON COLUMN trip_expenses.split_details IS '分账明细（{user_id: amount}）';
COMMENT ON COLUMN trip_expenses.expense_date IS '消费日期';
COMMENT ON COLUMN trip_expenses.created_at IS '创建时间';

-- ==================== wallets ====================
COMMENT ON TABLE wallets IS '钱包表：用户虚拟钱包，支持余额、冻结金额，一人一钱包';
COMMENT ON COLUMN wallets.id IS '钱包ID';
COMMENT ON COLUMN wallets.user_id IS '所属用户ID（一对一）';
COMMENT ON COLUMN wallets.balance IS '可用余额（元）';
COMMENT ON COLUMN wallets.frozen_balance IS '冻结金额（元）';
COMMENT ON COLUMN wallets.currency IS '货币代码';
COMMENT ON COLUMN wallets.created_at IS '创建时间';
COMMENT ON COLUMN wallets.updated_at IS '最后更新时间';

-- ==================== transactions ====================
COMMENT ON TABLE transactions IS '交易记录表：钱包交易流水，支持充值/支付/退款/提现/奖励五种类型';
COMMENT ON COLUMN transactions.id IS '交易记录ID';
COMMENT ON COLUMN transactions.user_id IS '所属用户ID';
COMMENT ON COLUMN transactions.type IS '交易类型：charge/payment/refund/withdraw/reward';
COMMENT ON COLUMN transactions.amount IS '交易金额（元）';
COMMENT ON COLUMN transactions.balance_after IS '交易后余额（元）';
COMMENT ON COLUMN transactions.description IS '交易描述';
COMMENT ON COLUMN transactions.related_trip_id IS '关联行程ID';
COMMENT ON COLUMN transactions.status IS '状态：pending/completed/failed/cancelled';
COMMENT ON COLUMN transactions.created_at IS '交易时间';
