import { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Trash2, MapPin, Calendar, Users, AlertTriangle, X } from 'lucide-react'
import { useTripStore } from '../stores/tripStore'
import TripTimeline from '../components/TripTimeline'
import TripMap from '../components/TripMap'
import BudgetPanel from '../components/BudgetPanel'

type Tab = 'itinerary' | 'map'

export default function TripDetailPagePC() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentTrip, loading, fetchTrip, deleteTrip } = useTripStore()
  const [budget, setBudget] = useState<any>(null)
  const [tab, setTab] = useState<Tab>('itinerary')
  const [mapDay, setMapDay] = useState(1)
  const [focusPoiId, setFocusPoiId] = useState<string | null>(null)
  const [showDelete, setShowDelete] = useState(false)

  useEffect(() => {
    if (id) {
      fetchTrip(id)
      import('../api').then(({ getBudget }) => {
        getBudget(id).then((res) => setBudget(res.data.data)).catch(() => {})
      })
    }
  }, [id])

  const handleDelete = async () => {
    if (!id) return
    await deleteTrip(id)
    navigate('/trips')
  }

  const parseWeather = (info: string | null) => {
    if (!info) return []
    const parts: { city: string; data: string }[] = []
    const lines = info.split('\n')
    let current: { city: string; lines: string[] } | null = null
    for (const line of lines) {
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
    if (currentTrip?.weather_info && currentTrip.destination) {
      const lines = currentTrip.weather_info.split('\n').filter(l => l.trim())
      for (const line of lines) {
        const m = line.match(/^([\u4e00-\u9fa5]{2,})[：:]/)
        if (m && m[1] !== currentTrip.destination) return m[1]
      }
    }
    return null
  }, [weatherParts, currentTrip])

  const selectedDay = useMemo(() => {
    return currentTrip?.days?.find(d => d.day_number === mapDay)
  }, [currentTrip, mapDay])

  if (loading || !currentTrip) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-gray-400 text-sm">加载中...</span>
      </div>
    )
  }

  const totalDays = currentTrip.days?.length || 1
  const typeEmoji: Record<string, string> = { flight: '✈️', train: '🚄', hotel: '🏨', poi: '🎫', food: '🍽️', transport: '🚗', bus: '🚌', other: '📍' }

  return (
    <div className="h-full flex flex-col">
      {/* Header — clean single row */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <button onClick={() => navigate('/trips')} className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-1 transition-colors">
            <ArrowLeft size={14} />返回行程列表
          </button>
          <div className="flex items-center gap-2.5 mt-1">
            <h1 className="text-lg font-bold text-gray-800">{currentTrip.title}</h1>
            {currentTrip.route_tag && (
              <span className="text-xs bg-primary-50 text-primary-600 px-2 py-0.5 rounded-full font-medium">
                {currentTrip.route_tag}
              </span>
            )}
          </div>
        </div>
        <button onClick={() => setShowDelete(true)} className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
          <Trash2 size={18} />
        </button>
      </div>

      {/* Tab bar — standalone row below header */}
      <div className="flex bg-gray-100 rounded-lg p-1 mb-4 w-fit">
        <button
          onClick={() => setTab('itinerary')}
          className={`px-5 py-1.5 text-sm font-medium rounded-md transition-colors ${tab === 'itinerary' ? 'bg-white text-primary-600 shadow-sm' : 'text-gray-500'}`}
        >
          行程
        </button>
        <button
          onClick={() => setTab('map')}
          className={`px-5 py-1.5 text-sm font-medium rounded-md transition-colors ${tab === 'map' ? 'bg-white text-primary-600 shadow-sm' : 'text-gray-500'}`}
        >
          🗺️ 地图
        </button>
      </div>

      {/* ── Itinerary Tab ── */}
      {tab === 'itinerary' && (
        <div className="flex-1 flex gap-6 min-h-0">
          {/* Left: Timeline 58% */}
          <div className="overflow-y-auto" style={{ flex: '0 0 58%' }}>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              {currentTrip.days && currentTrip.days.length > 0 ? (
                <TripTimeline days={currentTrip.days} travelerCount={currentTrip.traveler_count} />
              ) : (
                <div className="flex items-center justify-center py-16 text-gray-400 text-sm">还没有安排行程项</div>
              )}
            </div>
          </div>

          {/* Right: Info panels 42% */}
          <div className="overflow-y-auto space-y-3" style={{ flex: '0 0 42%' }}>

            {/* AI Summary */}
            {currentTrip.summary && (
              <div className="bg-primary-50 rounded-xl border border-primary-100 p-4">
                <h3 className="text-sm font-semibold text-primary-700 mb-2">📋 行程简介</h3>
                <p className="text-[13px] text-gray-700 leading-relaxed">{currentTrip.summary}</p>
              </div>
            )}

            {/* Special Notes */}
            {currentTrip.special_notes && (
              <div className="bg-orange-50 rounded-xl border border-orange-200 p-4">
                <h3 className="text-sm font-semibold text-orange-700 mb-2">⚠️ 特殊说明</h3>
                <p className="text-[13px] text-orange-600">{currentTrip.special_notes}</p>
              </div>
            )}

            {/* Tips */}
            {currentTrip.tips && currentTrip.tips.length > 0 && (
              <div className="bg-white rounded-xl border border-amber-200 p-4">
                <h3 className="text-sm font-semibold text-amber-700 mb-2">💡 出行提示</h3>
                <ul className="space-y-1.5">
                  {currentTrip.tips.map((tip: string, i: number) => (
                    <li key={i} className="text-xs text-amber-600 flex gap-1.5">
                      <span className="flex-shrink-0">•</span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Weather */}
            {(weatherParts.length > 0 || currentTrip.weather_info) && (
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">🌤️ 天气</h3>
                {weatherParts.length > 0 ? (
                  <div className="space-y-2">
                    {weatherParts.map((wp, i) => {
                      const isOrigin = wp.city === originCity
                      const isDest = wp.city === currentTrip.destination
                      return (
                        <div key={i} className={i > 0 ? 'pt-2 border-t border-gray-100' : ''}>
                          <div className="text-xs font-semibold text-gray-700 mb-0.5">
                            {wp.city}
                            {isOrigin && <span className="text-gray-400 font-normal ml-1">出发地</span>}
                            {isDest && <span className="text-gray-400 font-normal ml-1">目的地</span>}
                          </div>
                          <div className="text-xs text-gray-500 leading-relaxed whitespace-pre-line">{wp.data}</div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="text-[13px] text-gray-600 whitespace-pre-line leading-relaxed">{currentTrip.weather_info}</div>
                )}
              </div>
            )}

            {/* Trip Info */}
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">行程信息</h3>
              <div className="space-y-3">
                {originCity && (
                  <div className="flex items-center gap-2.5 text-gray-600">
                    <MapPin size={16} className="text-gray-400 flex-shrink-0" />
                    <span className="text-[13px]">{originCity}（出发地）</span>
                  </div>
                )}
                {currentTrip.destination && (
                  <div className="flex items-center gap-2.5 text-gray-600">
                    <MapPin size={16} className="text-primary-400 flex-shrink-0" />
                    <span className="text-[13px]">{currentTrip.destination}（目的地）</span>
                  </div>
                )}
                {currentTrip.start_date && (
                  <div className="flex items-center gap-2.5 text-gray-600">
                    <Calendar size={16} className="text-gray-400 flex-shrink-0" />
                    <span className="text-[13px]">{currentTrip.start_date} - {currentTrip.end_date}</span>
                  </div>
                )}
                <div className="flex items-center gap-2.5 text-gray-600">
                  <Users size={16} className="text-gray-400 flex-shrink-0" />
                  <span className="text-[13px]">{currentTrip.traveler_count}人</span>
                </div>
              </div>
            </div>

            {budget && <BudgetPanel budget={budget} originalBudget={currentTrip.budget_total} />}
          </div>
        </div>
      )}

      {/* ── Map Tab ── */}
      {tab === 'map' && (
        <div className="flex-1 flex gap-6 min-h-0">
          {/* Left: Day selector + plan 35% */}
          <div className="overflow-y-auto space-y-3" style={{ flex: '0 0 35%' }}>
            {/* Day selector */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {Array.from({ length: totalDays }, (_, i) => i + 1).map(d => (
                <button
                  key={d}
                  onClick={() => { setMapDay(d); setFocusPoiId(null) }}
                  className={`px-4 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                    d === mapDay ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                  }`}
                >
                  第{d}天
                </button>
              ))}
            </div>

            {/* Day plan */}
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              {selectedDay ? (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-gray-700">第{selectedDay.day_number}天</h3>
                    {selectedDay.date && <span className="text-xs text-gray-400">{selectedDay.date}</span>}
                  </div>
                  <div className="space-y-2">
                    {selectedDay.items?.map((item: any, idx: number) => (
                      <div
                        key={item.id}
                        onClick={() => setFocusPoiId(item.id)}
                        className="flex gap-2.5 text-[13px] cursor-pointer hover:bg-gray-50 rounded-lg px-2 py-1.5 -mx-2 transition-colors"
                      >
                        <span className="text-gray-400 text-[10px] w-8 text-right pt-0.5 font-mono">D{selectedDay.day_number}.{idx + 1}</span>
                        <span className="text-base">{typeEmoji[item.type] || '📍'}</span>
                        <span className="text-[10px] text-gray-400 flex-shrink-0 pt-0.5">{item.type}</span>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-800 truncate">{item.title}</div>
                          <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                            {item.start_time && <span>{item.start_time}{item.end_time ? `-${item.end_time}` : ''}</span>}
                            {item.price ? <span className="text-primary-600">¥{item.price}</span> : null}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-gray-400 text-sm text-center py-8">暂无数据</div>
              )}
            </div>
          </div>

          {/* Right: Map 65% */}
          <div style={{ flex: '0 0 65%' }}>
            {id && <TripMap tripId={id} totalDays={totalDays} selectedDay={mapDay} focusPoiId={focusPoiId} className="h-full" />}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowDelete(false)}>
          <div className="bg-white rounded-2xl shadow-2xl mx-4 overflow-hidden" style={{ width: 'clamp(300px, 90%, 420px)' }} onClick={e => e.stopPropagation()}>
            <div className="px-6 pt-8 pb-6 text-center">
              <div className="mx-auto w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mb-4">
                <AlertTriangle size={28} className="text-red-500" />
              </div>
              <h2 className="text-lg font-bold text-gray-800 mb-2">确认删除</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                确定要删除行程<br />
                <span className="font-semibold text-gray-800">「{currentTrip.title}」</span> 吗？
              </p>
              <p className="text-xs text-gray-400 mt-3">此操作不可撤销，所有数据将被永久删除</p>
            </div>
            <div className="flex gap-3 px-6 pb-6">
              <button onClick={() => setShowDelete(false)}
                className="flex-1 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors">
                取消
              </button>
              <button onClick={handleDelete}
                className="flex-1 py-2.5 text-sm font-medium text-white bg-red-500 rounded-xl hover:bg-red-600 transition-colors">
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
