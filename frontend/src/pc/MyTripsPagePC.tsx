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

  // ── fluid font sizes (viewport-based, no fixed px) ──────────

  const titleStyle = { fontSize: 'clamp(1.25rem, 1.8vw, 1.75rem)' }
  const cardTitleStyle = { fontSize: 'clamp(0.875rem, 1.1vw, 1.05rem)' }
  const bodyStyle = { fontSize: 'clamp(0.75rem, 0.95vw, 0.875rem)' }
  const smallStyle = { fontSize: 'clamp(0.6875rem, 0.8vw, 0.75rem)' }

  return (
    <div style={{ maxWidth: 'clamp(800px, 90%, 1400px)', margin: '0 auto' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="font-bold text-gray-800" style={titleStyle}>我的行程</h1>
        <button onClick={() => navigate('/plan')}
          className="bg-primary-600 text-white rounded-xl px-5 py-2.5 font-medium flex items-center gap-2 hover:bg-primary-700 transition-colors"
          style={bodyStyle}>
          <Plus size={18} />新建行程
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center text-gray-400 py-12" style={bodyStyle}>加载中...</div>
      )}

      {/* Card grid — fluid columns */}
      {!loading && trips.length > 0 && (
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(clamp(260px, 28%, 360px), 1fr))' }}>
          {trips.map((trip) => (
            <div key={trip.id} onClick={() => navigate(`/trips/${trip.id}`)}
              className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer flex flex-col">
              {/* Top row: title + status + delete */}
              <div className="flex items-start justify-between mb-3">
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold text-gray-800 truncate" style={cardTitleStyle}>{trip.title}</h3>
                  {trip.route_tag && (
                    <span className="inline-block mt-1 bg-primary-50 text-primary-600 px-2 py-0.5 rounded font-medium" style={smallStyle}>
                      {trip.route_tag}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                  <span className={`px-2 py-0.5 rounded-full font-medium ${statusColors[trip.status] || ''}`} style={smallStyle}>
                    {statusLabels[trip.status] || trip.status}
                  </span>
                  <button onClick={(e) => handleDeleteClick(e, trip.id, trip.title)}
                    className="text-gray-300 hover:text-red-500 p-1 rounded hover:bg-red-50 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Info row */}
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-gray-500 mb-2" style={smallStyle}>
                {trip.destination && (
                  <span className="flex items-center gap-1"><MapPin size={12} />{trip.destination}</span>
                )}
                {trip.start_date && (
                  <span className="flex items-center gap-1"><Calendar size={12} />{trip.start_date}{trip.end_date ? ` - ${trip.end_date}` : ''}</span>
                )}
                <span className="flex items-center gap-1"><Users size={12} />{trip.traveler_count}人</span>
              </div>

              {/* Summary — AI generated intro */}
              {trip.summary && (
                <p className="text-gray-500 leading-relaxed line-clamp-2 mb-2" style={smallStyle}>
                  {trip.summary}
                </p>
              )}

              {/* Budget — bottom right */}
              {trip.budget_total && (
                <div className="text-right" style={cardTitleStyle}>
                  <span className="text-primary-600 font-semibold">¥{trip.budget_total.toLocaleString()}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && trips.length === 0 && (
        <div className="text-center py-16">
          <div className="text-5xl mb-3">🗺️</div>
          <div className="text-gray-500 mb-1 font-medium" style={bodyStyle}>还没有行程</div>
          <div className="text-gray-400 mb-5" style={smallStyle}>开始创建你的第一个旅行计划</div>
          <button onClick={() => navigate('/plan')}
            className="bg-primary-600 text-white rounded-xl px-5 py-2.5 font-medium hover:bg-primary-700 transition-colors" style={bodyStyle}>
            创建第一个行程
          </button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setDeleteTarget(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-xl overflow-hidden"
            style={{ width: 'clamp(320px, 36%, 460px)', margin: '0 1rem' }}
            onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center">
                  <AlertTriangle size={18} className="text-red-500" />
                </div>
                <h2 className="font-semibold text-gray-800" style={bodyStyle}>确认删除</h2>
              </div>
              <button onClick={() => setDeleteTarget(null)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100 transition-colors">
                <X size={18} />
              </button>
            </div>
            {/* Body */}
            <div className="px-5 py-4">
              <p className="text-gray-600 leading-relaxed" style={bodyStyle}>
                确定要删除行程 <span className="font-semibold text-gray-800">「{deleteTarget.title}」</span> 吗？
              </p>
              <p className="text-gray-400 mt-1.5" style={smallStyle}>此操作不可撤销，行程中的所有数据将被永久删除。</p>
            </div>
            {/* Footer */}
            <div className="flex items-center justify-end gap-2.5 px-5 py-3.5 border-t border-gray-100 bg-gray-50">
              <button onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 font-medium text-gray-600 hover:text-gray-800 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors" style={smallStyle}>
                取消
              </button>
              <button onClick={handleConfirmDelete}
                className="px-4 py-2 font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors" style={smallStyle}>
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
