import { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Trash2, AlertTriangle, X } from 'lucide-react'
import { useTripStore } from '../stores/tripStore'
import TripTimeline from '../components/TripTimeline'
import TripMap from '../components/TripMap'
import BudgetPanel from '../components/BudgetPanel'

type Tab = 'itinerary' | 'map'

export default function TripDetailPage() {
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

  const totalDays = currentTrip?.days?.length || 1
  const selectedDay = useMemo(() => {
    return currentTrip?.days?.find(d => d.day_number === mapDay)
  }, [currentTrip, mapDay])

  if (loading || !currentTrip) {
    return (
      <div className="p-4">
        <div className="flex items-center gap-3 mb-4">
          <button onClick={() => navigate(-1)}><ArrowLeft size={22} /></button>
        </div>
        <div className="text-center text-gray-500 py-12">加载中...</div>
      </div>
    )
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="p-1"><ArrowLeft size={22} /></button>
          <div>
            <h1 className="text-lg font-bold text-gray-800">{currentTrip.title}</h1>
            {currentTrip.destination && (
              <div className="text-xs text-gray-500">{currentTrip.destination}</div>
            )}
          </div>
        </div>
        <button
          onClick={() => setShowDelete(true)}
          className="p-2.5 rounded-xl border border-red-100 text-red-400 active:bg-red-50 active:text-red-500 transition-colors"
        >
          <Trash2 size={18} />
        </button>
      </div>

      {/* Trip Info — always visible */}
      <div className="flex flex-wrap gap-3 mb-4 text-xs text-gray-500">
        {currentTrip.start_date && (
          <span>{currentTrip.start_date} - {currentTrip.end_date}</span>
        )}
        <span>{currentTrip.traveler_count}人</span>
        {currentTrip.budget_total && (
          <span>预算 ¥{currentTrip.budget_total.toLocaleString()}</span>
        )}
        {currentTrip.route_tag && (
          <span className="bg-primary-50 text-primary-600 px-2 py-0.5 rounded-full text-[11px] font-medium">
            {currentTrip.route_tag}
          </span>
        )}
      </div>

      {/* Weather — always visible */}
      {currentTrip.weather_info && (
        <div className="bg-blue-50 rounded-xl px-4 py-3 mb-4">
          <div className="text-xs font-medium text-blue-700 mb-1">🌤️ 天气情况</div>
          <div className="text-xs text-blue-600 whitespace-pre-line">{currentTrip.weather_info}</div>
        </div>
      )}

      {/* Tips — always visible */}
      {currentTrip.tips && currentTrip.tips.length > 0 && (
        <div className="bg-amber-50 rounded-xl px-4 py-3 mb-4">
          <div className="text-xs font-medium text-amber-700 mb-1">💡 出行提示</div>
          <ul className="text-xs text-amber-600 space-y-1">
            {currentTrip.tips.map((tip: string, i: number) => (
              <li key={i} className="flex gap-1.5">
                <span className="flex-shrink-0">•</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Tab bar */}
      <div className="flex bg-gray-100 rounded-lg p-1 mb-4">
        <button
          onClick={() => setTab('itinerary')}
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
            tab === 'itinerary'
              ? 'bg-white text-primary-600 shadow-sm'
              : 'text-gray-500'
          }`}
        >
          行程
        </button>
        <button
          onClick={() => setTab('map')}
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
            tab === 'map'
              ? 'bg-white text-primary-600 shadow-sm'
              : 'text-gray-500'
          }`}
        >
          🗺️ 地图
        </button>
      </div>

      {/* Tab content */}
      {tab === 'itinerary' ? (
        <>
          {currentTrip.days && currentTrip.days.length > 0 ? (
            <TripTimeline days={currentTrip.days} travelerCount={currentTrip.traveler_count} />
          ) : (
            <div className="text-center text-gray-400 py-12">
              还没有安排行程项，去搜索并添加吧
            </div>
          )}
          {budget && (
            <div className="mt-6">
              <BudgetPanel budget={budget} />
            </div>
          )}
        </>
      ) : (
        /* Map tab: day selector + map + day itinerary */
        <div className="space-y-4">
          {/* Day selector */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {Array.from({ length: totalDays }, (_, i) => i + 1).map(d => (
              <button
                key={d}
                onClick={() => { setMapDay(d); setFocusPoiId(null) }}
                className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                  d === mapDay ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-500'
                }`}
              >
                第{d}天
              </button>
            ))}
          </div>

          {/* Map */}
          {id && (
            <TripMap
              tripId={id}
              totalDays={totalDays}
              selectedDay={mapDay}
              focusPoiId={focusPoiId}
              compact
              className="mb-0"
            />
          )}

          {/* Day itinerary */}
          {selectedDay && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700">
                  第{selectedDay.day_number}天
                </h3>
                {selectedDay.date && (
                  <span className="text-xs text-gray-400">{selectedDay.date}</span>
                )}
              </div>
              <div className="space-y-1.5">
                {selectedDay.items?.map((item: any, idx: number) => {
                  const emoji: Record<string, string> = {
                    flight: '✈️', train: '🚄', hotel: '🏨', poi: '🎫',
                    food: '🍽️', transport: '🚗', bus: '🚌', other: '📍',
                  }
                  return (
                    <div
                      key={item.id}
                      onClick={() => setFocusPoiId(item.id)}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg active:bg-gray-100 cursor-pointer"
                    >
                      <span className="text-gray-300 text-xs w-4 text-right">{idx + 1}</span>
                      <span className="text-base">{emoji[item.type] || '📍'}</span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-gray-800 truncate">{item.title}</div>
                        <div className="text-xs text-gray-400">
                          {item.start_time && item.end_time
                            ? `${item.start_time} - ${item.end_time}`
                            : item.start_time}
                          {item.price ? ` · ¥${item.price}` : ''}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setShowDelete(false)}>
          <div className="bg-white rounded-2xl shadow-xl mx-4 overflow-hidden"
            style={{ width: 'clamp(280px, 85%, 400px)' }}
            onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center">
                  <AlertTriangle size={18} className="text-red-500" />
                </div>
                <h2 className="font-semibold text-gray-800 text-base">确认删除</h2>
              </div>
              <button onClick={() => setShowDelete(false)}
                className="text-gray-400 active:text-gray-600 p-1 rounded-lg active:bg-gray-100 transition-colors">
                <X size={18} />
              </button>
            </div>
            {/* Body */}
            <div className="px-5 py-4">
              <p className="text-sm text-gray-600 leading-relaxed">
                确定要删除行程 <span className="font-semibold text-gray-800">「{currentTrip.title}」</span> 吗？
              </p>
              <p className="text-xs text-gray-400 mt-1.5">此操作不可撤销，行程中的所有数据将被永久删除。</p>
            </div>
            {/* Footer */}
            <div className="flex items-center justify-end gap-2.5 px-5 py-3.5 border-t border-gray-100 bg-gray-50">
              <button onClick={() => setShowDelete(false)}
                className="px-4 py-2 text-sm font-medium text-gray-600 active:text-gray-800 bg-white border border-gray-200 rounded-lg active:bg-gray-50 transition-colors">
                取消
              </button>
              <button onClick={handleDelete}
                className="px-4 py-2 text-sm font-medium text-white bg-red-500 active:bg-red-600 rounded-lg transition-colors">
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
