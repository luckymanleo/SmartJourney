import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, MapPin, Calendar, Users, Trash2, X, AlertTriangle, List } from 'lucide-react'
import { useTripStore } from '../stores/tripStore'

const statusLabels: Record<string, string> = {
  planning: '规划中', active: '进行中', completed: '已完成', cancelled: '已取消', expired: '已过期',
}
const statusColors: Record<string, string> = {
  planning: 'bg-yellow-100 text-yellow-700', active: 'bg-green-100 text-green-700',
  completed: 'bg-gray-100 text-gray-500', cancelled: 'bg-red-100 text-red-500', expired: 'bg-gray-100 text-gray-400',
}

type ViewMode = 'list' | 'map'

export default function MyTripsPagePC() {
  const navigate = useNavigate()
  const { trips, loading, fetchTrips, deleteTrip } = useTripStore()
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('list')

  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)

  useEffect(() => { fetchTrips() }, [])

  useEffect(() => {
    if (viewMode !== 'map' || !trips.length || !mapContainerRef.current) return
    const AMap = (window as any).AMap
    if (!AMap) {
      const token = localStorage.getItem('sj_pc_token') || ''
      fetch('/api/v1/map/config', { headers: { Authorization: `Bearer ${token}` } })
        .then(r => r.json())
        .then(cfg => {
          if (cfg.code === 0 && cfg.data?.js_key) {
            const script = document.createElement('script')
            script.src = `https://webapi.amap.com/maps?v=2.0&key=${cfg.data.js_key}`
            script.async = true; script.onload = () => initMap()
            document.head.appendChild(script)
          }
        }).catch(() => {})
      return
    }
    initMap()
    function initMap() {
      const A = (window as any).AMap; if (!A || !mapContainerRef.current) return
      if (mapRef.current) { mapRef.current.destroy(); mapRef.current = null }
      const markers: any[] = []; const points: [number, number][] = []
      trips.forEach(trip => {
        if (trip.dest_lng && trip.dest_lat) {
          points.push([trip.dest_lng, trip.dest_lat])
          const m = new A.Marker({
            position: [trip.dest_lng, trip.dest_lat],
            label: { content: `<div style="font-size:11px;background:#3b82f6;color:#fff;padding:2px 8px;border-radius:12px">${trip.destination || trip.title}</div>`, direction: 'top', offset: [0, -25] },
          })
          m.on('click', () => navigate(`/trips/${trip.id}`))
          markers.push(m)
        }
      })
      if (points.length === 0) return
      const map = new A.Map(mapContainerRef.current, {
        zoom: points.length === 1 ? 12 : 5,
        center: [points.reduce((s, p) => s + p[0], 0) / points.length, points.reduce((s, p) => s + p[1], 0) / points.length],
        resizeEnable: true,
      })
      markers.forEach(m => m.setMap(map))
      map.setFitView(markers, false, [40, 40, 40, 40])
      mapRef.current = map
    }
    return () => { if (mapRef.current) { mapRef.current.destroy(); mapRef.current = null } }
  }, [viewMode, trips])

  const handleDeleteClick = (e: React.MouseEvent, id: string, title: string) => {
    e.stopPropagation(); setDeleteTarget({ id, title })
  }
  const handleConfirmDelete = () => {
    if (deleteTarget) { deleteTrip(deleteTarget.id); setDeleteTarget(null) }
  }

  const titleStyle = { fontSize: 'clamp(1.25rem, 1.8vw, 1.75rem)' }
  const cardTitleStyle = { fontSize: 'clamp(0.875rem, 1.1vw, 1.05rem)' }
  const bodyStyle = { fontSize: 'clamp(0.75rem, 0.95vw, 0.875rem)' }
  const smallStyle = { fontSize: 'clamp(0.6875rem, 0.8vw, 0.75rem)' }

  return (
    <div style={{ maxWidth: 'clamp(800px, 90%, 1400px)', margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <h1 className="font-bold text-gray-800" style={titleStyle}>我的行程</h1>
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            <button onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-md transition-colors ${viewMode === 'list' ? 'bg-white text-primary-600 shadow-sm' : 'text-gray-400'}`}>
              <List size={16} />
            </button>
            <button onClick={() => setViewMode('map')}
              className={`p-1.5 rounded-md transition-colors ${viewMode === 'map' ? 'bg-white text-primary-600 shadow-sm' : 'text-gray-400'}`}>
              <MapPin size={16} />
            </button>
          </div>
        </div>
        <button onClick={() => navigate('/plan')}
          className="bg-primary-600 text-white rounded-xl px-5 py-2.5 font-medium flex items-center gap-2 hover:bg-primary-700 transition-colors" style={bodyStyle}>
          <Plus size={18} />新建行程
        </button>
      </div>

      {loading && <div className="text-center text-gray-400 py-12" style={bodyStyle}>加载中...</div>}

      {viewMode === 'map' && !loading && (
        <div className="rounded-xl border border-gray-200 overflow-hidden mb-4" style={{ height: 'clamp(300px, 50vh, 600px)' }}>
          <div ref={mapContainerRef} className="w-full h-full" />
        </div>
      )}

      {viewMode === 'list' && !loading && trips.length > 0 && (
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(clamp(260px, 28%, 360px), 1fr))' }}>
          {trips.map((trip) => (
            <div key={trip.id} onClick={() => navigate(`/trips/${trip.id}`)}
              className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer flex flex-col">
              <div className="flex items-start justify-between mb-3">
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold text-gray-800 truncate" style={cardTitleStyle}>{trip.title}</h3>
                  {trip.route_tag && (
                    <span className="inline-block mt-1 bg-primary-50 text-primary-600 px-2 py-0.5 rounded font-medium" style={smallStyle}>{trip.route_tag}</span>
                  )}
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                  <span className={`px-2 py-0.5 rounded-full font-medium ${statusColors[trip.status] || ''}`} style={smallStyle}>{statusLabels[trip.status] || trip.status}</span>
                  <button onClick={(e) => handleDeleteClick(e, trip.id, trip.title)} className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"><Trash2 size={14} /></button>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-gray-500 mb-2" style={smallStyle}>
                {trip.destination && <span className="flex items-center gap-1"><MapPin size={12} />{trip.destination}</span>}
                {trip.start_date && <span className="flex items-center gap-1"><Calendar size={12} />{trip.start_date}{trip.end_date ? ` - ${trip.end_date}` : ''}</span>}
                <span className="flex items-center gap-1"><Users size={12} />{trip.traveler_count}人</span>
              </div>
              {trip.summary && <p className="text-gray-500 leading-relaxed line-clamp-2 mb-2" style={smallStyle}>{trip.summary}</p>}
              {trip.budget_total && (
                <div className="text-right" style={cardTitleStyle}>
                  <span className="text-primary-600 font-semibold">¥{trip.budget_total.toLocaleString()}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && trips.length === 0 && (
        <div className="text-center py-16">
          <div className="text-5xl mb-3">🗺️</div>
          <div className="text-gray-500 mb-1 font-medium" style={bodyStyle}>还没有行程</div>
          <div className="text-gray-400 mb-5" style={smallStyle}>开始创建你的第一个旅行计划</div>
          <button onClick={() => navigate('/plan')} className="bg-primary-600 text-white rounded-xl px-5 py-2.5 font-medium hover:bg-primary-700 transition-colors" style={bodyStyle}>创建第一个行程</button>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in" onClick={() => setDeleteTarget(null)}>
          <div className="bg-white rounded-2xl shadow-2xl mx-4 overflow-hidden" style={{ width: 'clamp(300px, 90%, 420px)' }} onClick={e => e.stopPropagation()}>
            {/* Body */}
            <div className="px-6 pt-8 pb-6 text-center">
              <div className="mx-auto w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mb-4">
                <AlertTriangle size={28} className="text-red-500" />
              </div>
              <h2 className="text-lg font-bold text-gray-800 mb-2">确认删除</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                确定要删除行程<br />
                <span className="font-semibold text-gray-800">「{deleteTarget.title}」</span> 吗？
              </p>
              <p className="text-xs text-gray-400 mt-3">此操作不可撤销，所有数据将被永久删除</p>
            </div>
            {/* Footer */}
            <div className="flex gap-3 px-6 pb-6">
              <button onClick={() => setDeleteTarget(null)}
                className="flex-1 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors">
                取消
              </button>
              <button onClick={handleConfirmDelete}
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
