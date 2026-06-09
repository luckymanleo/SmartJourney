import { useEffect, useState } from 'react'
import { Navigation, X, ChevronLeft, ChevronRight } from 'lucide-react'

interface PoiDetail {
  id: string
  name: string
  type: string
  address: string
  lng: number
  lat: number
  tel?: string
  rating?: string
  photos: string[]
  website?: string
}

interface Props {
  poi: {
    id: string
    title: string
    type: string
    lng: number
    lat: number
    start_time?: string | null
    end_time?: string | null
    location?: string | null
  } | null
  nextPoi?: { title: string; lng: number; lat: number } | null
  distance?: string  // "🚶 步行15分钟"
  onClose: () => void
  compact?: boolean
}

export default function PoiDetailCard({ poi, nextPoi, distance, onClose, compact = false }: Props) {
  const [detail, setDetail] = useState<PoiDetail | null>(null)
  const [photoIdx, setPhotoIdx] = useState(0)

  // Fetch POI detail from backend for photos
  useEffect(() => {
    if (!poi) { setDetail(null); return }
    // First try to get more info via POI search
    const token = localStorage.getItem('sj_token') || ''
    fetch(`/api/v1/map/poi/text?keywords=${encodeURIComponent(poi.title)}&offset=1`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(data => {
        const pois = data?.data?.pois
        if (pois?.length > 0) {
          const best = pois[0]
          // Fetch detail for photos
          return fetch(`/api/v1/map/poi/${best.id}`, {
            headers: { Authorization: `Bearer ${token}` },
          }).then(r => r.json())
        }
        return null
      })
      .then(data => {
        if (data?.data) {
          setDetail(data.data)
        }
      })
      .catch(() => {})
  }, [poi?.id, poi?.title])

  if (!poi) return null

  const typeEmoji: Record<string, string> = {
    flight: '✈️', train: '🚄', hotel: '🏨', poi: '🎫',
    food: '🍽️', transport: '🚗', bus: '🚌', other: '📍',
  }

  const handleNavigate = () => {
    const url = `https://uri.amap.com/navigation?to=${poi.lng},${poi.lat},${encodeURIComponent(poi.title)}&mode=walking&callnative=1`
    window.open(url, '_blank')
  }

  const photos = detail?.photos || []

  return (
    <div className={`bg-white border-t border-gray-200 ${compact ? 'px-3 py-2.5' : 'px-4 py-3'}`}>
      {/* Close + Title row */}
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="text-sm">{typeEmoji[poi.type] || '📍'}</span>
            <h3 className="font-semibold text-gray-800 text-sm truncate">{poi.title}</h3>
            {detail?.rating && (
              <span className="text-xs text-yellow-600 flex-shrink-0">⭐{detail.rating}</span>
            )}
          </div>
          {detail?.address && (
            <p className="text-xs text-gray-400 mt-0.5 truncate">{detail.address}</p>
          )}
          {poi.start_time && (
            <p className="text-xs text-gray-400 mt-0.5">
              🕐 {poi.start_time}{poi.end_time ? ` - ${poi.end_time}` : ''}
            </p>
          )}
        </div>
        <button onClick={onClose} className="p-1 text-gray-300 hover:text-gray-500 flex-shrink-0">
          <X size={16} />
        </button>
      </div>

      {/* Photos */}
      {photos.length > 0 && (
        <div className="mb-2">
          <div className="relative rounded-lg overflow-hidden bg-gray-100" style={{ height: compact ? 120 : 160 }}>
            <img
              src={photos[photoIdx]}
              alt={poi.title}
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
            {photos.length > 1 && (
              <>
                <button
                  onClick={() => setPhotoIdx(p => (p - 1 + photos.length) % photos.length)}
                  className="absolute left-1 top-1/2 -translate-y-1/2 bg-black/30 text-white rounded-full p-1"
                >
                  <ChevronLeft size={14} />
                </button>
                <button
                  onClick={() => setPhotoIdx(p => (p + 1) % photos.length)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 bg-black/30 text-white rounded-full p-1"
                >
                  <ChevronRight size={14} />
                </button>
                <span className="absolute bottom-1 right-2 text-xs text-white bg-black/40 px-1.5 py-0.5 rounded">
                  {photoIdx + 1}/{photos.length}
                </span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Next stop + distance */}
      {nextPoi && (
        <div className="text-xs text-gray-500 mb-2 flex items-center gap-1">
          {distance && <span>{distance}</span>}
          <span>→</span>
          <span className="text-gray-700 font-medium">{nextPoi.title}</span>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleNavigate}
          className="w-[60%] mx-auto flex items-center justify-center gap-1.5 py-2 text-sm text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Navigation size={14} />开始导航
        </button>
      </div>
    </div>
  )
}
