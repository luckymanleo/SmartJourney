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
    // Transport items: extract departure point from title
    if (poi.type === 'train' || poi.type === 'flight' || poi.type === 'transport') {
      let depName = ''
      const arrowIdx = poi.title.indexOf('→')
      if (arrowIdx >= 0) {
        // train/flight style: "D2325 武夷山北→深圳北 08:24-15:38"
        const before = poi.title.slice(0, arrowIdx).trim()
        depName = before.replace(/^[A-Z]+\d*\s+/, '').trim()
      } else {
        // transport style: "深圳北站到酒店（地铁/公交）"
        const daoIdx = poi.title.indexOf('到')
        if (daoIdx > 0) {
          depName = poi.title.slice(0, daoIdx).trim()
        }
      }

      if (depName) {
        const params = new URLSearchParams()
        params.set('type', 'car')
        params.set('from[name]', depName)
        // train/flight: to = arrival station (current poi coords)
        // transport: to = nextPoi (destination) or current poi
        const isTransit = poi.type === 'train' || poi.type === 'flight'
        if (isTransit) {
          params.set('to[lnglat]', `${poi.lng},${poi.lat}`)
          params.set('to[name]', depName) // will be overwritten below for → case
        } else if (nextPoi) {
          params.set('to[lnglat]', `${nextPoi.lng},${nextPoi.lat}`)
          params.set('to[name]', nextPoi.title)
        } else {
          params.set('to[lnglat]', `${poi.lng},${poi.lat}`)
          params.set('to[name]', depName)
        }

        // For → items, use arrival station name (clean up suffixes)
        if (arrowIdx >= 0) {
          const after = poi.title.slice(arrowIdx + 1).trim()
          const arrName = after
            .replace(/\s+\d{2}:\d{2}.*$/, '')          // strip time " 08:24-15:38"
            .replace(/\s+[A-Z]+\d+\s*$/i, '')           // strip train/flight number " D2325"
            .replace(/\s*(地铁|公交|步行|打车|网约车|专车|出租车)\d*号线?(转\d*号线?)?(\s*\([^)]*\))?\s*$/, '')  // strip transport method
            .trim()
          params.set('to[name]', arrName)
        }

        params.set('src', 'uriapi')
        params.set('callnative', '1')
        params.set('innersrc', 'uriapi')
        window.open(`https://ditu.amap.com/dir?${params.toString()}`, '_blank')
        return
      }
    }

    // Non-transport: current → next
    const from = `${poi.lng},${poi.lat},${encodeURIComponent(poi.title)}`
    const to = nextPoi
      ? `${nextPoi.lng},${nextPoi.lat},${encodeURIComponent(nextPoi.title)}`
      : `${poi.lng},${poi.lat},${encodeURIComponent(poi.title)}`
    const url = `https://uri.amap.com/navigation?from=${from}&to=${to}&mode=walking&callnative=1`
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
