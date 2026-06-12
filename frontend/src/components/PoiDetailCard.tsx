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
    photos?: string[] | null
    amap_poi_id?: string | null
    day_number?: number
    item_index?: number
  } | null
  nextPoi?: { title: string; lng: number; lat: number } | null
  distance?: string
  onClose: () => void
  compact?: boolean
}

export default function PoiDetailCard({ poi, nextPoi, distance, onClose, compact = false }: Props) {
  const [detail, setDetail] = useState<PoiDetail | null>(null)
  const [photoIdx, setPhotoIdx] = useState(0)

  useEffect(() => {
    // Reset everything when POI changes (belt-and-suspenders with key prop)
    setDetail(null)
    setPhotoIdx(0)

    if (!poi) return

    // If DB already has photos, use them directly — no API call needed
    if (poi.photos && poi.photos.length > 0) {
      setDetail({
        id: poi.id,
        name: poi.title,
        type: poi.type,
        address: poi.location || '',
        lng: poi.lng,
        lat: poi.lat,
        photos: poi.photos,
      })
      return
    }

    const abort = new AbortController()
    const signal = abort.signal

    // Platform-aware token key (PC vs mobile)
    const isPC = typeof window !== 'undefined' && window.location.pathname.startsWith('/pc.html')
    const tokenKey = isPC ? 'sj_pc_token' : 'sj_token'
    const token = localStorage.getItem(tokenKey) || ''

    if (['train', 'flight', 'transport', 'bus', 'hotel'].includes(poi.type)) {
      const kw = poi.type === 'flight' ? '机场' : poi.type === 'train' ? '火车站' : poi.type === 'hotel' ? '酒店' : '站'
      fetch(`/api/v1/map/poi/around?lng=${poi.lng}&lat=${poi.lat}&keywords=${kw}&radius=3000&offset=1`, {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      })
        .then(r => r.json())
        .then(data => {
          if (signal.aborted) return
          const pois = data?.data?.pois
          if (pois?.length > 0) {
            return fetch(`/api/v1/map/poi/${pois[0].id}`, {
              headers: { Authorization: `Bearer ${token}` },
              signal,
            }).then(r => r.json())
          }
          return null
        })
        .then(data => {
          if (signal.aborted) return
          if (data?.data) setDetail(data.data)
        })
        .catch(() => {})
      return () => abort.abort()
    }

    // Non-transport: around-search by coordinates + keyword
    fetch(`/api/v1/map/poi/around?lng=${poi.lng}&lat=${poi.lat}&keywords=${encodeURIComponent(poi.title)}&radius=500&offset=1`, {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    })
      .then(r => r.json())
      .then(data => {
        if (signal.aborted) return
        const pois = data?.data?.pois
        if (pois?.length > 0) {
          const best = pois[0]
          return fetch(`/api/v1/map/poi/${best.id}`, {
            headers: { Authorization: `Bearer ${token}` },
            signal,
          }).then(r => r.json())
        }
        return null
      })
      .then(data => {
        if (signal.aborted) return
        if (data?.data) {
          setDetail(data.data)
        }
      })
      .catch(() => {})
    return () => abort.abort()
  }, [poi?.id])

  if (!poi) return null

  const typeEmoji: Record<string, string> = {
    flight: '✈️', train: '🚄', hotel: '🏨', poi: '🎫',
    food: '🍽️', transport: '🚗', bus: '🚌', other: '📍',
  }

  const handleNavigate = () => {
    const url = `https://uri.amap.com/navigation?to=${poi.lng},${poi.lat},${encodeURIComponent(poi.title)}&mode=walking&callnative=1`
    window.open(url, '_blank')
  }

  // Use detail if loaded (key prop + useEffect reset guarantee it matches current POI)
  const photos = detail?.photos || []

  return (
    <div className={`bg-white border-t border-gray-200 ${compact ? 'px-3 py-2.5' : 'px-4 py-3'}`}>
      {/* Close + Title row */}
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            {poi.day_number != null && poi.item_index != null && (
              <span className="text-[10px] text-gray-400 font-mono flex-shrink-0">D{poi.day_number}.{poi.item_index + 1}</span>
            )}
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

      {/* Next stop */}
      {nextPoi && (
        <div className="text-xs text-gray-500 mb-2 flex items-center gap-1">
          {distance && !distance.includes('km') && <span>{distance}</span>}
          <span>→</span>
          <span className="text-gray-700 font-medium">{nextPoi.title}</span>
        </div>
      )}

      {/* Navigation button */}
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
