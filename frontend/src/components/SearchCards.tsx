/**
 * SearchCards.tsx — 6 类搜索结果专属卡片组件
 * 所有卡片直接使用结构化字段渲染，不写正则
 */
import React from 'react'

// ── 通用工具 ────────────────────────────────────────────

function formatDuration(minutes: number | null | undefined): string {
  if (minutes == null) return ''
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h > 0 && m > 0) return `${h}h${m}m`
  if (h > 0) return `${h}h`
  return `${m}min`
}

function BookingLink({ url }: { url?: string }) {
  if (!url) return null
  return (
    <button onClick={() => window.open(url, '_blank')}
      className="text-xs bg-primary-50 text-primary-600 px-3 py-1.5 rounded-lg mt-2 inline-block hover:bg-primary-100 transition-colors">
      去预订 →
    </button>
  )
}

function SectionTag({ label }: { label?: string | null }) {
  if (!label) return null
  return (
    <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full ml-1.5 align-middle">
      {label}
    </span>
  )
}

function FreeBadge() {
  return <span className="text-[10px] bg-green-100 text-green-600 px-1.5 py-0.5 rounded-full ml-1">免费</span>
}

// ── 1. 机票卡片 ──────────────────────────────────────────

export function FlightCard({ item }: { item: any }) {
  const f = item.flight
  if (!f) return null

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4 hover:shadow-sm transition-shadow">
      {/* 第一行：✈ 航司 🛩 机型 航班号   ¥价格 */}
      <div className="flex items-center gap-2 text-sm flex-wrap">
        {f.airline && <span className="text-blue-600 font-medium">✈ {f.airline}</span>}
        {f.aircraft && <span className="text-gray-500">🛩 {f.aircraft}</span>}
        <span className="text-gray-800 font-semibold">{f.flight_no}</span>
        {f.section && <SectionTag label={f.section} />}
        {item.price != null && item.price > 0 && (
          <span className="text-primary-600 font-bold text-sm ml-auto">¥{item.price}</span>
        )}
      </div>

      {/* 第二行：🕐 时间 ⏱ 时长 🛫 航线 */}
      {(f.depart_time || f.depart_airport) && (
        <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500 flex-wrap">
          {f.depart_time && f.arrive_time && (
            <span>🕐 {f.depart_time}→{f.arrive_time}</span>
          )}
          {f.duration_min != null && (
            <span>⏱ {formatDuration(f.duration_min)}</span>
          )}
          {(f.depart_airport || f.arrive_airport) && (
            <span>🛫 {f.depart_airport}{f.depart_airport && f.arrive_airport ? '→' : ''}{f.arrive_airport}</span>
          )}
        </div>
      )}

      {/* 第三行：亮点/推荐 */}
      {f.highlight && (
        <div className="text-[11px] text-gray-500 mt-1.5 leading-relaxed">{f.highlight}</div>
      )}

      {/* 第四行：权衡（如果有） */}
      {f.tradeoff && (
        <div className="text-[11px] text-gray-400 mt-0.5">⚠ {f.tradeoff}</div>
      )}

      {/* 预订按钮 */}
      <BookingLink url={item.booking_url} />
    </div>
  )
}

// ── 2. 火车票卡片 ────────────────────────────────────────

export function TrainCard({ item }: { item: any }) {
  const t = item.train
  if (!t) return null

  const typeEmoji: Record<string, string> = {
    '高铁': '🚄', '动车': '🚄', '城际': '🚄',
    '直达特快': '🚃', '特快': '🚃', '普快': '🚃', '普速': '🚃',
    '夜间列车': '🛏️',
  }

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4 hover:shadow-sm transition-shadow">
      {/* 第一行：🚄 车次 类型 */}
      <div className="flex items-center gap-2 text-sm">
        <span>{typeEmoji[t.train_type] || '🚄'}</span>
        <span className="text-gray-800 font-semibold">{t.train_no}</span>
        {t.train_type && (
          <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-full">{t.train_type}</span>
        )}
        {t.section && <SectionTag label={t.section} />}
        {item.price != null && item.price > 0 && (
          <span className="text-primary-600 font-bold text-sm ml-auto">¥{item.price}</span>
        )}
      </div>

      {/* 第二行：出发站 → 到达站 */}
      {(t.depart_station || t.arrive_station) && (
        <div className="flex items-center gap-1.5 mt-1.5 text-xs text-gray-600">
          <span>🚉 {t.depart_station}</span>
          <span className="text-gray-400">→</span>
          <span>{t.arrive_station}</span>
        </div>
      )}

      {/* 第三行：时间 + 时长 */}
      {(t.depart_time || t.duration_min != null) && (
        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
          {t.depart_time && t.arrive_time && (
            <span>🕐 {t.depart_time}→{t.arrive_time}</span>
          )}
          {t.duration_min != null && (
            <span>⏱ {formatDuration(t.duration_min)}</span>
          )}
        </div>
      )}

      {/* 第四行：亮点 */}
      {t.highlight && (
        <div className="text-[11px] text-gray-500 mt-1.5 leading-relaxed">{t.highlight}</div>
      )}

      {/* 权衡 */}
      {t.tradeoff && (
        <div className="text-[11px] text-gray-400 mt-0.5">⚠ {t.tradeoff}</div>
      )}

      <BookingLink url={item.booking_url} />
    </div>
  )
}

// ── 3. 酒店卡片 ──────────────────────────────────────────

export function HotelCard({ item }: { item: any }) {
  const h = item.hotel
  if (!h) return null

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4 hover:shadow-sm transition-shadow">
      {/* 名称 */}
      <div className="flex items-center gap-2">
        <span className="font-medium text-gray-800">🏨 {item.name || item.title}</span>
        {h.section && <SectionTag label={h.section} />}
        {item.price != null && item.price > 0 && (
          <span className="text-primary-600 font-bold text-sm ml-auto">¥{item.price}/晚</span>
        )}
      </div>

      {/* 亮点 */}
      {h.highlight && (
        <div className="text-xs text-gray-600 mt-1.5 leading-relaxed line-clamp-2">
          ✨ {h.highlight}
        </div>
      )}

      {/* 推荐理由 */}
      {h.recommendation && (
        <div className="text-xs text-gray-500 mt-1 leading-relaxed line-clamp-2">
          💡 {h.recommendation}
        </div>
      )}

      {/* 权衡 */}
      {h.tradeoff && (
        <div className="text-[11px] text-gray-400 mt-1">⚠ {h.tradeoff}</div>
      )}

      <BookingLink url={item.booking_url} />
    </div>
  )
}

// ── 4. 景点卡片 ──────────────────────────────────────────

export function POICard({ item }: { item: any }) {
  const p = item.poi
  if (!p) return null

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4 hover:shadow-sm transition-shadow">
      {/* 名称 */}
      <div className="flex items-center gap-2">
        <span className="font-medium text-gray-800">🎫 {item.name || item.title}</span>
        {p.is_free && <FreeBadge />}
        {p.section && <SectionTag label={p.section} />}
        {item.price != null && item.price > 0 && !p.is_free && (
          <span className="text-primary-600 font-bold text-sm ml-auto">¥{item.price}</span>
        )}
      </div>

      {/* 标签行：建议游玩 / 开放时间 */}
      <div className="flex flex-wrap gap-1.5 mt-1.5">
        {p.suggested_duration && (
          <span className="text-[10px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
            🕐 {p.suggested_duration}
          </span>
        )}
        {p.hours && (
          <span className="text-[10px] bg-green-50 text-green-600 px-2 py-0.5 rounded-full">
            ⏰ {p.hours}
          </span>
        )}
      </div>

      {/* 亮点 */}
      {p.highlight && (
        <div className="text-xs text-gray-600 mt-1.5 leading-relaxed line-clamp-2">
          ✨ {p.highlight}
        </div>
      )}

      {/* 推荐理由 */}
      {p.recommendation && (
        <div className="text-xs text-gray-500 mt-1 leading-relaxed line-clamp-2">
          💡 {p.recommendation}
        </div>
      )}

      <BookingLink url={item.booking_url} />
    </div>
  )
}

// ── 5. 美食卡片 ──────────────────────────────────────────

export function FoodCard({ item }: { item: any }) {
  const fd = item.food
  if (!fd) return null

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4 hover:shadow-sm transition-shadow">
      {/* 名称 + 品类 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-medium text-gray-800 truncate">🍜 {item.name || item.title}</span>
          {fd.category && (
            <span className="text-[10px] bg-orange-50 text-orange-600 px-1.5 py-0.5 rounded-full flex-shrink-0">
              {fd.category}
            </span>
          )}
        </div>
        {fd.price_per_person != null && (
          <span className="text-primary-600 font-bold text-sm flex-shrink-0 ml-2">
            ¥{fd.price_per_person}<span className="text-[10px] text-gray-400 font-normal">/人</span>
          </span>
        )}
      </div>

      {/* 评分 + 地址 */}
      <div className="flex flex-wrap gap-1.5 mt-1.5">
        {fd.rating != null && (
          <span className="text-[10px] bg-yellow-50 text-yellow-600 px-2 py-0.5 rounded-full">
            ⭐{fd.rating}
          </span>
        )}
        {fd.address && (
          <span className="text-[10px] bg-gray-50 text-gray-500 px-2 py-0.5 rounded-full truncate max-w-[200px]">
            📍 {fd.address}
          </span>
        )}
      </div>
    </div>
  )
}

// ── 6. 交通卡片 ──────────────────────────────────────────

export function TransportCard({ item }: { item: any }) {
  const tp = item.transport
  if (!tp) return null

  const modeEmoji: Record<string, string> = {
    '打车/驾车': '🚗', '出租车': '🚕',
    '地铁/城轨': '🚇', '公交': '🚌',
    '铁路': '🚄', '电动车': '🛵', '自行车': '🚲',
  }

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4 hover:shadow-sm transition-shadow">
      {/* 标题行 */}
      <div className="flex items-center gap-2">
        <span>{modeEmoji[tp.mode] || '🚗'}</span>
        <span className="font-medium text-gray-800 text-sm">{tp.mode}</span>
        {item.price != null && item.price > 0 && (
          <span className="text-primary-600 font-bold text-sm ml-auto">¥{tp.cost ?? item.price}</span>
        )}
      </div>

      {/* 距离/时长/费用标签 */}
      <div className="flex flex-wrap gap-1.5 mt-1.5">
        {tp.distance_km != null && (
          <span className="text-[10px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
            📏 {tp.distance_km}km
          </span>
        )}
        {tp.duration_min != null && (
          <span className="text-[10px] bg-purple-50 text-purple-600 px-2 py-0.5 rounded-full">
            ⏱ {tp.duration_min}分钟
          </span>
        )}
        {tp.cost != null && (
          <span className="text-[10px] bg-green-50 text-green-600 px-2 py-0.5 rounded-full">
            💰 ¥{tp.cost}
          </span>
        )}
      </div>

      {/* 路线详情（公交方案等） */}
      {tp.route_detail && (
        <div className="text-xs text-gray-500 mt-1.5 line-clamp-2">{tp.route_detail}</div>
      )}
    </div>
  )
}

// ── 提示/错误横幅 ────────────────────────────────────────

export function InfoBanner({ item }: { item: any }) {
  const desc = (item.description || '').replace(/💡.*$/s, '').trim()
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
      <div className="flex items-start gap-2">
        <span className="text-lg">ℹ️</span>
        <div>
          <div className="text-sm font-medium text-blue-700 mb-1">{item.title}</div>
          <div className="text-xs text-blue-600 whitespace-pre-line">{desc}</div>
        </div>
      </div>
    </div>
  )
}

export function ErrorBanner({ item }: { item: any }) {
  const desc = (item.description || '').replace(/💡.*$/s, '').trim()
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
      <div className="flex items-start gap-2">
        <span className="text-lg">💡</span>
        <div>
          <div className="text-sm font-medium text-amber-700 mb-1">需要更具体的地点</div>
          <div className="text-xs text-amber-600">{desc}</div>
          <div className="text-xs text-amber-500 mt-2">尝试输入具体地点，如"深圳宝安机场到深圳北站"</div>
        </div>
      </div>
    </div>
  )
}

// ── 结果分派函数 ─────────────────────────────────────────

/**
 * 根据 item 的专属字段自动选择卡片组件渲染
 */
export function renderSearchCard(item: any, idx: number) {
  const edata = item.extra_data || {}
  if (edata.is_info || item.is_info) return <InfoBanner key={idx} item={item} />
  if (edata.is_error || item.is_error) return <ErrorBanner key={idx} item={item} />
  if (item.flight)    return <FlightCard key={idx} item={item} />
  if (item.train)     return <TrainCard key={idx} item={item} />
  if (item.hotel)     return <HotelCard key={idx} item={item} />
  if (item.poi)       return <POICard key={idx} item={item} />
  if (item.food)      return <FoodCard key={idx} item={item} />
  if (item.transport) return <TransportCard key={idx} item={item} />
  return null
}
