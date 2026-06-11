import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, AlertTriangle, X } from 'lucide-react'
import { useTripStore } from '../stores/tripStore'
import TripCard from '../components/TripCard'

export default function MyTripsPage() {
  const navigate = useNavigate()
  const { trips, loading, fetchTrips, deleteTrip } = useTripStore()
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null)

  useEffect(() => {
    fetchTrips()
  }, [])

  const handleConfirmDelete = () => {
    if (deleteTarget) {
      deleteTrip(deleteTarget.id)
      setDeleteTarget(null)
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-800">我的行程</h1>
        <button
          onClick={() => navigate('/plan')}
          className="bg-primary-600 text-white rounded-full w-10 h-10 flex items-center justify-center"
        >
          <Plus size={22} />
        </button>
      </div>

      {loading && <div className="text-center text-gray-500 py-8">加载中...</div>}

      <div className="space-y-3">
        {trips.map((trip) => (
          <TripCard key={trip.id} trip={trip} onRequestDelete={(id, title) => setDeleteTarget({ id, title })} />
        ))}
      </div>

      {!loading && trips.length === 0 && (
        <div className="text-center py-16">
          <div className="text-5xl mb-4">🗺️</div>
          <div className="text-gray-500 mb-4">还没有行程</div>
          <button
            onClick={() => navigate('/plan')}
            className="bg-primary-600 text-white rounded-xl px-6 py-3 font-medium"
          >
            创建第一个行程
          </button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setDeleteTarget(null)}>
          <div className="bg-white rounded-2xl shadow-xl mx-4 overflow-hidden"
            style={{ width: 'clamp(280px, 85%, 400px)' }}
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center">
                  <AlertTriangle size={18} className="text-red-500" />
                </div>
                <h2 className="font-semibold text-gray-800 text-base">确认删除</h2>
              </div>
              <button onClick={() => setDeleteTarget(null)}
                className="text-gray-400 active:text-gray-600 p-1 rounded-lg active:bg-gray-100 transition-colors">
                <X size={18} />
              </button>
            </div>
            <div className="px-5 py-4">
              <p className="text-sm text-gray-600 leading-relaxed">
                确定要删除行程 <span className="font-semibold text-gray-800">「{deleteTarget.title}」</span> 吗？
              </p>
              <p className="text-xs text-gray-400 mt-1.5">此操作不可撤销，行程中的所有数据将被永久删除。</p>
            </div>
            <div className="flex items-center justify-end gap-2.5 px-5 py-3.5 border-t border-gray-100 bg-gray-50">
              <button onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 text-sm font-medium text-gray-600 active:text-gray-800 bg-white border border-gray-200 rounded-lg active:bg-gray-50 transition-colors">
                取消
              </button>
              <button onClick={handleConfirmDelete}
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
