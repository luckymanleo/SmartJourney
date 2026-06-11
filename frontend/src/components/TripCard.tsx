import { Calendar, MapPin, Users, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface TripCardProps {
  trip: {
    id: string
    title: string
    status: string
    destination: string | null
    start_date: string | null
    end_date: string | null
    traveler_count: number
    budget_total: number | null
    route_tag: string | null
    weather_info: string | null
    summary: string | null
    created_at: string | null
  }
  onDelete?: (id: string) => void
  onRequestDelete?: (id: string, title: string) => void
}

const statusLabels: Record<string, string> = {
  planning: '规划中',
  active: '进行中',
  completed: '已完成',
  cancelled: '已取消',
  expired: '已过期',
}

const statusColors: Record<string, string> = {
  planning: 'bg-yellow-100 text-yellow-700',
  active: 'bg-green-100 text-green-700',
  completed: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-500',
  expired: 'bg-gray-100 text-gray-400 line-through',
}

export default function TripCard({ trip, onDelete, onRequestDelete }: TripCardProps) {
  const navigate = useNavigate()

  const weatherLabel = (() => {
    if (!trip.weather_info) return null
    const cities: string[] = []
    const lines = trip.weather_info.split('\n')
    for (const line of lines) {
      const m = line.match(/^##\s*🌤️\s*(?:出发地天气|目的地天气)?[（(]?([\u4e00-\u9fa5]{2,})[）)]?/)
      if (m) cities.push(m[1])
    }
    if (cities.length === 0) {
      // fallback: strip markdown from first line
      return trip.weather_info.split('\n')[0].replace(/^##\s*🌤️\s*/, '').replace(/^##\s*/, '')
    }
    if (cities.length === 2) return `🌤️ ${cities[0]}（出发地） · ${cities[1]}（目的地）`
    return `🌤️ ${cities[0]}`
  })()

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onRequestDelete) {
      onRequestDelete(trip.id, trip.title)
    } else if (onDelete) {
      if (confirm(`确定删除「${trip.title}」？此操作不可撤销。`)) {
        onDelete(trip.id)
      }
    }
  }

  return (
    <div
      onClick={() => navigate(`/trips/${trip.id}`)}
      className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-gray-800 pr-6">{trip.title}</h3>
          {trip.route_tag && (
            <span className="inline-block mt-1 text-[10px] bg-primary-50 text-primary-600 px-1.5 py-0.5 rounded">
              {trip.route_tag}
            </span>
          )}
          {weatherLabel && (
            <span className="inline-block mt-1 ml-1 text-[10px] text-gray-400 truncate max-w-[220px]">
              {weatherLabel}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${statusColors[trip.status] || ''}`}>
            {statusLabels[trip.status] || trip.status}
          </span>
          <button
            onClick={handleDelete}
            className="text-gray-400 hover:text-red-500 active:bg-red-50 p-1.5 rounded-lg transition-colors flex-shrink-0"
            title="删除行程"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs text-gray-500">
        {trip.start_date && (
          <span className="flex items-center gap-1">
            <Calendar size={12} /> {trip.start_date}{trip.end_date ? ` - ${trip.end_date}` : ''}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Users size={12} /> {trip.traveler_count}人
        </span>
      </div>

      {trip.summary && (
        <p className="text-[11px] text-gray-400 leading-relaxed mt-1.5 line-clamp-2">{trip.summary}</p>
      )}

      <div className="flex items-end justify-between mt-2">
        <div>
          {trip.created_at && (
            <div className="text-[10px] text-gray-400">
              创建于 {new Date(trip.created_at).toLocaleDateString('zh-CN')}
            </div>
          )}
        </div>
        {trip.budget_total && (
          <div className="text-sm text-primary-600 font-semibold">
            ¥{trip.budget_total.toLocaleString()}
          </div>
        )}
      </div>
    </div>
  )
}
