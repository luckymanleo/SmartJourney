import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, MapPin, Calendar, Users, Trash2, X, AlertTriangle } from 'lucide-react'
import { useTripStore } from '../stores/tripStore'

const statusLabels: Record<string, string> = {
  planning: '规划中', active: '进行中', completed: '已完成', cancelled: '已取消', expired: '已过期',
}
const statusColors: Record<string, string> = {
  planning: 'bg-yellow-100 text-yellow-700', active: 'bg-green-100 text-green-700',
  completed: 'bg-gray-100 text-gray-500', cancelled: 'bg-red-100 text-red-500', expired: 'bg-gray-100 text-gray-400',
}

export default function MyTripsPagePC() {
  const navigate = useNavigate()
  const { trips, loading, fetchTrips, deleteTrip } = useTripStore()
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null)

  useEffect(() => { fetchTrips() }, [])

  const handleDeleteClick = (e: React.MouseEvent, id: string, title: string) => {
    e.stopPropagation()
    setDeleteTarget({ id, title })
  }

  const handleConfirmDelete = () => {
    if (deleteTarget) {
      deleteTrip(deleteTarget.id)
      setDeleteTarget(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">我的行程</h1>
          <p className="text-base text-gray-500 mt-1">管理你的所有旅行计划</p>
        </div>
        <button onClick={() => navigate('/plan')}
          className="bg-primary-600 text-white rounded-xl px-5 py-2.5 text-base font-medium flex items-center gap-2 hover:bg-primary-700 transition-colors">
          <Plus size={20} />新建行程
        </button>
      </div>

      {loading && <div className="text-center text-gray-500 py-12 text-base">加载中...</div>}

      {!loading && trips.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {trips.map((trip) => (
            <div key={trip.id} onClick={() => navigate(`/trips/${trip.id}`)}
              className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer">
              <div className="flex items-start justify-between mb-3">
                <div className="min-w-0 flex-1">
                  <h3 className="text-base font-semibold text-gray-800 truncate pr-4">{trip.title}</h3>
                  {trip.route_tag && (
                    <span className="inline-block mt-1 text-xs bg-primary-50 text-primary-600 px-2 py-0.5 rounded">{trip.route_tag}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[trip.status] || ''}`}>
                    {statusLabels[trip.status] || trip.status}
                  </span>
                  <button onClick={(e) => handleDeleteClick(e, trip.id, trip.title)}
                    className="text-gray-400 hover:text-red-500 p-1 rounded hover:bg-red-50 transition-colors">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-500">
                {trip.destination && <span className="flex items-center gap-1"><MapPin size={14} />{trip.destination}</span>}
                {trip.start_date && <span className="flex items-center gap-1"><Calendar size={14} />{trip.start_date}{trip.end_date ? ` - ${trip.end_date}` : ''}</span>}
                <span className="flex items-center gap-1"><Users size={14} />{trip.traveler_count}人</span>
              </div>
              {trip.weather_info && (
                <div className="mt-3 bg-blue-50 rounded-lg px-3 py-2 text-xs text-blue-700 leading-relaxed whitespace-pre-line line-clamp-3">
                  🌤️ {trip.weather_info}
                </div>
              )}
              {trip.budget_total && (
                <div className="mt-3 text-base text-primary-600 font-semibold">预算 ¥{trip.budget_total.toLocaleString()}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && trips.length === 0 && (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">🗺️</div>
          <div className="text-gray-500 mb-2 text-xl">还没有行程</div>
          <div className="text-gray-400 text-base mb-6">开始创建你的第一个旅行计划</div>
          <button onClick={() => navigate('/plan')}
            className="bg-primary-600 text-white rounded-xl px-6 py-3 text-base font-medium hover:bg-primary-700 transition-colors">
            创建第一个行程
          </button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setDeleteTarget(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-xl w-full max-w-md mx-4 overflow-hidden"
            onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
                  <AlertTriangle size={20} className="text-red-500" />
                </div>
                <h2 className="text-lg font-semibold text-gray-800">确认删除</h2>
              </div>
              <button onClick={() => setDeleteTarget(null)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100 transition-colors">
                <X size={20} />
              </button>
            </div>
            {/* Body */}
            <div className="px-6 py-5">
              <p className="text-gray-600 text-[15px] leading-relaxed">
                确定要删除行程 <span className="font-semibold text-gray-800">「{deleteTarget.title}」</span> 吗？
              </p>
              <p className="text-gray-400 text-sm mt-2">此操作不可撤销，行程中的所有数据将被永久删除。</p>
            </div>
            {/* Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100 bg-gray-50">
              <button onClick={() => setDeleteTarget(null)}
                className="px-5 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                取消
              </button>
              <button onClick={handleConfirmDelete}
                className="px-5 py-2.5 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors">
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
