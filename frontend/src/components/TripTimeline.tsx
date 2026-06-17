interface TripItem {
  id: string
  type: string
  title: string
  description?: string | null
  start_time?: string | null
  end_time?: string | null
  price?: number | null
  booking_url?: string | null
  extra_data?: any
}

interface TripDay {
  day_number: number
  date?: string | null
  items: TripItem[]
}

const typeConfig: Record<string, { icon: string; color: string }> = {
  flight: { icon: '✈️', color: 'bg-blue-100 text-blue-700' },
  train: { icon: '🚄', color: 'bg-green-100 text-green-700' },
  hotel: { icon: '🏨', color: 'bg-purple-100 text-purple-700' },
  poi: { icon: '🎫', color: 'bg-orange-100 text-orange-700' },
  food: { icon: '🍽️', color: 'bg-red-100 text-red-700' },
  transport: { icon: '🚗', color: 'bg-gray-100 text-gray-700' },
}

export default function TripTimeline({ days, travelerCount, onItemClick }: { days: TripDay[]; travelerCount?: number; onItemClick?: (title: string) => void }) {
  const showUnit = travelerCount && travelerCount > 1

  return (
    <div className="space-y-6">
      {days.map((day) => (
        <div key={day.day_number}>
          <div className="flex items-center mb-3">
            <div className="bg-primary-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">
              {day.day_number}
            </div>
            <div className="ml-3">
              <div className="font-semibold text-gray-800">第 {day.day_number} 天</div>
              {day.date && <div className="text-xs text-gray-500">{day.date}</div>}
            </div>
          </div>

          <div className="ml-4 border-l-2 border-primary-200 pl-4 space-y-3">
            {day.items?.map((item, i) => {
              const cfg = typeConfig[item.type] || { icon: '📍', color: 'bg-gray-100' }
              const unitPrice = showUnit && item.price ? item.price / travelerCount! : null
              const isInt = unitPrice && unitPrice === Math.floor(unitPrice)
              // 节点截止时间已过 → 不再显示"去预订"
              const itemExpired = !!(day.date && item.end_time && new Date() > new Date(`${day.date}T${item.end_time}:00`))
              return (
                <div key={item.id} className={`relative ${onItemClick ? 'cursor-pointer hover:bg-gray-50 rounded-lg -mx-1 px-1' : ''}`}
                  onClick={() => onItemClick?.(item.title)}>
                  <div className="absolute -left-[30px] top-2 w-3 h-3 bg-primary-400 rounded-full border-2 border-white" />
                  <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs mb-1 ${cfg.color}`}>
                    <span>{cfg.icon}</span>
                    <span>{item.type}</span>
                  </div>
                  <div className="font-medium text-gray-800 text-sm">
                    {item.title}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                    {item.start_time && <span>🕐 {item.start_time}{item.end_time ? ` - ${item.end_time}` : ''}</span>}
                    {item.price && (
                      <span className="text-primary-600 font-medium">
                        {showUnit && unitPrice ? (
                          <>
                            <span className="text-gray-400 font-normal">¥</span>
                            {isInt ? unitPrice.toLocaleString() : unitPrice.toFixed(2)}
                            <span className="text-gray-400 font-normal">/人</span>
                            <span className="text-gray-300 mx-0.5">·</span>
                            <span className="text-gray-400 font-normal">共</span>
                            ¥{item.price.toLocaleString()}
                          </>
                        ) : (
                          <>¥{item.price.toLocaleString()}</>
                        )}
                      </span>
                    )}
                  </div>
                  {item.description && (
                    <div className="text-xs text-gray-400 mt-1">{item.description}</div>
                  )}
                  {item.booking_url && !itemExpired && (
                    <a
                      href={item.booking_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary-500 mt-1 inline-block hover:underline"
                    >
                      去预订 →
                    </a>
                  )}
                  {item.extra_data && !item.booking_url && (
                    <div className="text-xs text-gray-400 mt-1">
                      {item.extra_data.highlight || item.extra_data.note || item.extra_data.recommend || ''}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
