import { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Trash2, MapPin, Calendar, Users } from 'lucide-react'
import { useTripStore } from '../stores/tripStore'
import TripTimeline from '../components/TripTimeline'
import BudgetPanel from '../components/BudgetPanel'

export default function TripDetailPagePC() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentTrip, loading, fetchTrip, deleteTrip } = useTripStore()
  const [budget, setBudget] = useState<any>(null)

  useEffect(() => {
    if (id) {
      fetchTrip(id)
      import('../api').then(({ getBudget }) => {
        getBudget(id).then((res) => setBudget(res.data.data)).catch(() => {})
      })
    }
  }, [id])

  const handleDelete = async () => {
    if (!id || !confirm('确定删除这个行程吗？')) return
    await deleteTrip(id)
    navigate('/trips')
  }

  const parseWeather = (info: string | null) => {
    if (!info) return []
    const parts: { city: string; data: string }[] = []
    const lines = info.split('\n')
    let current: { city: string; lines: string[] } | null = null
    for (const line of lines) {
      // Match: "## 🌤️ 深圳" or "## 🌤️ 出发地天气（深圳）" or just "深圳："
      let m = line.match(/^##\s*🌤️\s*(?:出发地天气|目的地天气)?[（(]?([\u4e00-\u9fa5]{2,})[）)]?/)
      if (!m) m = line.match(/^([\u4e00-\u9fa5]{2,})[：:]/)
      if (m) {
        if (current) parts.push({ city: current.city, data: current.lines.join('\n') })
        current = { city: m[1], lines: [] }
      } else if (current && line.trim()) {
        current.lines.push(line.trim())
      }
    }
    if (current) parts.push({ city: current.city, data: current.lines.join('\n') })
    return parts
  }

  const weatherParts = useMemo(() => parseWeather(currentTrip?.weather_info || null), [currentTrip])
  const originCity = useMemo(() => {
    const wp = weatherParts.find(wp => wp.city !== currentTrip?.destination)
    if (wp) return wp.city
    // fallback: parse raw weather_info for origin
    if (currentTrip?.weather_info && currentTrip.destination) {
      const lines = currentTrip.weather_info.split('\n').filter(l => l.trim())
      for (const line of lines) {
        const m = line.match(/^([\u4e00-\u9fa5]{2,})[：:]/)
        if (m && m[1] !== currentTrip.destination) return m[1]
      }
    }
    return null
  }, [weatherParts, currentTrip])

  if (loading || !currentTrip) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-gray-400 text-base">加载中...</span>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 shrink-0">
        <div>
          <button onClick={() => navigate('/trips')} className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-1 mb-1.5 transition-colors">
            <ArrowLeft size={14} />返回行程列表
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-800">{currentTrip.title}</h1>
            {currentTrip.route_tag && (
              <span className="text-xs bg-primary-50 text-primary-600 px-2.5 py-0.5 rounded-full font-medium">
                {currentTrip.route_tag}
              </span>
            )}
          </div>
        </div>
        <button onClick={handleDelete} className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
          <Trash2 size={20} />
        </button>
      </div>

      {/* Two-column layout */}
      <div className="flex-1 flex gap-8 min-h-0">
        {/* Left: Timeline */}
        <div className="flex-1 min-w-0 overflow-y-auto">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            {currentTrip.days && currentTrip.days.length > 0 ? (
              <TripTimeline days={currentTrip.days} />
            ) : (
              <div className="flex items-center justify-center py-16 text-gray-400 text-base">
                还没有安排行程项
              </div>
            )}
          </div>
        </div>

        {/* Right: Info panels */}
        <div className="flex-1 min-w-0 overflow-y-auto space-y-5">
          {/* Weather */}
          {(weatherParts.length > 0 || currentTrip.weather_info) && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-base font-semibold text-gray-700 mb-3">🌤️ 天气</h3>
              {weatherParts.length > 0 ? (
                <div className="space-y-3">
                  {weatherParts.map((wp, i) => {
                    const isOrigin = wp.city === originCity
                    const isDest = wp.city === currentTrip.destination
                    return (
                      <div key={i} className={i > 0 ? 'pt-3 border-t border-gray-100' : ''}>
                        <div className="text-[12px] font-semibold text-gray-700 mb-1">
                          {wp.city}
                          {isOrigin && <span className="text-gray-400 font-normal ml-1">出发地</span>}
                          {isDest && <span className="text-gray-400 font-normal ml-1">目的地</span>}
                        </div>
                        <div className="text-[12px] text-gray-500 leading-relaxed whitespace-pre-line">{wp.data}</div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-sm text-gray-600 whitespace-pre-line leading-relaxed">{currentTrip.weather_info}</div>
              )}
            </div>
          )}

          {/* Trip Info */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-base font-semibold text-gray-700 mb-4">行程信息</h3>
            <div className="space-y-4">
              {originCity && (
                <div className="flex items-center gap-3 text-gray-600">
                  <MapPin size={18} className="text-gray-400 flex-shrink-0" />
                  <span className="text-base">{originCity}（出发地）</span>
                </div>
              )}
              {currentTrip.destination && (
                <div className="flex items-center gap-3 text-gray-600">
                  <MapPin size={18} className="text-primary-400 flex-shrink-0" />
                  <span className="text-base">{currentTrip.destination}（目的地）</span>
                </div>
              )}
              {currentTrip.start_date && (
                <div className="flex items-center gap-3 text-gray-600">
                  <Calendar size={18} className="text-gray-400 flex-shrink-0" />
                  <span className="text-base">{currentTrip.start_date} - {currentTrip.end_date}</span>
                </div>
              )}
              <div className="flex items-center gap-3 text-gray-600">
                <Users size={18} className="text-gray-400 flex-shrink-0" />
                <span className="text-base">{currentTrip.traveler_count}人</span>
              </div>
              {currentTrip.budget_total && (
                <div className="pt-4 border-t border-gray-100">
                  <span className="text-xs text-gray-400">总预算</span>
                  <div className="text-2xl font-bold text-primary-600 mt-1">¥{currentTrip.budget_total.toLocaleString()}</div>
                </div>
              )}
            </div>
          </div>

          {/* Budget */}
          {budget && <BudgetPanel budget={budget} />}
        </div>
      </div>
    </div>
  )
}
