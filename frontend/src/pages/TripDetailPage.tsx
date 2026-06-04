import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Trash2 } from 'lucide-react'
import { useTripStore } from '../stores/tripStore'
import TripTimeline from '../components/TripTimeline'
import BudgetPanel from '../components/BudgetPanel'

export default function TripDetailPage() {
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
        <button onClick={handleDelete} className="p-2 text-gray-400 hover:text-red-500">
          <Trash2 size={18} />
        </button>
      </div>

      {/* Trip Info */}
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

      {/* Weather */}
      {currentTrip.weather_info && (
        <div className="bg-blue-50 rounded-xl px-4 py-3 mb-4">
          <div className="text-xs font-medium text-blue-700 mb-1">🌤️ 天气情况</div>
          <div className="text-xs text-blue-600 whitespace-pre-line">{currentTrip.weather_info}</div>
        </div>
      )}

      {/* Timeline */}
      {currentTrip.days && currentTrip.days.length > 0 ? (
        <TripTimeline days={currentTrip.days} />
      ) : (
        <div className="text-center text-gray-400 py-12">
          还没有安排行程项，去搜索并添加吧
        </div>
      )}

      {/* Budget */}
      {budget && (
        <div className="mt-6">
          <BudgetPanel budget={budget} />
        </div>
      )}
    </div>
  )
}
