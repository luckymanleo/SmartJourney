import { useEffect, useRef, useState, useCallback } from 'react'
import PoiDetailCard from './PoiDetailCard'

// ── types ──────────────────────────────────────────────────────

interface Poi {
  id: string
  title: string
  type: string
  lng: number
  lat: number
  start_time?: string | null
  end_time?: string | null
  location?: string | null
}

interface DayData {
  day_number: number
  date: string
  pois: Poi[]
}

// ── consts ─────────────────────────────────────────────────────

const TYPE_EMOJI: Record<string, string> = {
  flight: '✈️', train: '🚄', hotel: '🏨', poi: '🎫',
  food: '🍽️', transport: '🚗', bus: '🚌', other: '📍',
}
const DAY_COLORS = ['#3b82f6', '#f97316', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#84cc16']

// ── Amap loader ────────────────────────────────────────────────

let _amapPromise: Promise<boolean> | null = null
let _amapKey = ''

function loadAmap(key: string): Promise<boolean> {
  if (_amapPromise && _amapKey === key) return _amapPromise
  if ((window as any).AMap) return Promise.resolve(true)
  _amapKey = key
  _amapPromise = new Promise(resolve => {
    const s = document.createElement('script')
    s.src = `https://webapi.amap.com/maps?v=2.0&key=${key}`
    s.async = true
    s.onload = () => resolve(true)
    s.onerror = () => resolve(false)
    document.head.appendChild(s)
  })
  return _amapPromise
}

// ── helpers ────────────────────────────────────────────────────

function walkDistance(p1: Poi, p2: Poi): string {
  const dx = (p2.lng - p1.lng) * 111000 * Math.cos(((p1.lat + p2.lat) / 2) * Math.PI / 180)
  const dy = (p2.lat - p1.lat) * 111000
  const m = Math.sqrt(dx * dx + dy * dy)
  if (m < 1000) return `🚶 步行${Math.round(m)}m`
  return `🚗 约${(m / 1000).toFixed(1)}km`
}

// ── component ──────────────────────────────────────────────────

interface Props {
  tripId: string
  totalDays: number
  compact?: boolean
  selectedDay?: number   // 外部控制选中天（PC 左侧天选择器）
  focusPoiId?: string | null  // 外部控制聚焦 POI（PC 左侧点击联动）
  className?: string
}

export default function TripMap({ tripId, totalDays, compact = false, selectedDay, focusPoiId, className = '' }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const allMarkersRef = useRef<any[]>([])
  const allPolylinesRef = useRef<any[]>([])

  const [allDays, setAllDays] = useState<DayData[]>([])
  const [filterDay, setFilterDay] = useState(0)  // 0 = all (only used when selectedDay is undefined)
  const effectiveDay = selectedDay ?? filterDay   // PC: from prop, mobile: from local state
  const [selectedPoi, setSelectedPoi] = useState<Poi | null>(null)
  const pendingFocusRef = useRef<string | null>(null)  // remember focus target until map ready

  // Sync external selectedDay → internal filterDay
  useEffect(() => { if (selectedDay) setFilterDay(selectedDay) }, [selectedDay])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [amapKey, setAmapKey] = useState('')

  // 1. Load config
  useEffect(() => {
    const token = localStorage.getItem('sj_token') || ''
    fetch('/api/v1/map/config', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(cfg => { if (cfg.code === 0 && cfg.data?.js_key) setAmapKey(cfg.data.js_key); else setError('地图服务未配置') })
      .catch(() => setError('配置加载失败'))
  }, [])

  // 2. Load Amap
  useEffect(() => { if (amapKey) loadAmap(amapKey).then(ok => { if (!ok) setError('地图加载失败') }) }, [amapKey])

  // 3. Load ALL days
  useEffect(() => {
    if (!tripId) return
    setLoading(true)
    const token = localStorage.getItem('sj_token') || ''
    // Load full trip map (all days)
    fetch(`/api/v1/map/trip/${tripId}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(json => {
        if (json.code === 0) {
          setAllDays(json.data.days || [])
        } else {
          setError(json.message || '加载失败')
        }
        setLoading(false)
      })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [tripId])

  // 4. Render map with all days, applying filter for highlight/dim
  useEffect(() => {
    if (!allDays.length || !containerRef.current) return
    const AMap = (window as any).AMap
    if (!AMap) return

    // Cleanup
    allMarkersRef.current.forEach(m => m.setMap(null))
    allMarkersRef.current = []
    allPolylinesRef.current.forEach(p => p.setMap(null))
    allPolylinesRef.current = []
    if (mapRef.current) { mapRef.current.destroy(); mapRef.current = null }

    const allPoints: [number, number][] = []

    // Collect all days' POIs
    allDays.forEach(day => {
      day.pois.forEach(p => { if (p.lng && p.lat) allPoints.push([p.lng, p.lat]) })
    })

    const center: [number, number] = allPoints.length > 0
      ? [allPoints.reduce((s, c) => s + c[0], 0) / allPoints.length, allPoints.reduce((s, c) => s + c[1], 0) / allPoints.length]
      : [116.40, 39.90]

    const map = new AMap.Map(containerRef.current, {
      zoom: 13, center, resizeEnable: true,
    })
    map.plugin(['AMap.ToolBar', 'AMap.Scale'], () => {
      map.addControl(new AMap.ToolBar({ position: 'RT' }))
      map.addControl(new AMap.Scale({ position: 'LB' }))
    })

    // Render all days
    allDays.forEach((day, dayIdx) => {
      const color = DAY_COLORS[dayIdx % DAY_COLORS.length]
      const isFiltered = effectiveDay > 0 && day.day_number !== effectiveDay
      // When externally controlled (PC left panel / mobile), hide non-selected days entirely
      // When using internal filter, dim them for overview context
      if (selectedDay && isFiltered) return  // skip non-selected day entirely
      const opacity = selectedDay ? 0.85 : (isFiltered ? 0.25 : 0.75)

      // Markers
      day.pois.forEach((poi, idx) => {
        if (!poi.lng || !poi.lat) return
        const m = new AMap.Marker({
          position: [poi.lng, poi.lat],
          label: {
            content: `<span style="font-size:10px;background:${color};color:#fff;padding:1px 5px;border-radius:10px;opacity:${opacity}">D${day.day_number}.${idx + 1}</span>`,
            direction: 'top',
            offset: [0, -20],
          },
          zIndex: isFiltered ? 50 : 100,
          opacity,
        })
        m.setMap(map)
        m.on('click', () => setSelectedPoi(poi))
        allMarkersRef.current.push(m)
      })

      // Polyline for this day
      const coords = day.pois.filter(p => p.lng && p.lat).map(p => [p.lng, p.lat] as [number, number])
      if (coords.length > 1) {
        const pl = new AMap.Polyline({
          path: coords,
          strokeColor: color,
          strokeWeight: 3,
          strokeOpacity: opacity,
          strokeStyle: 'dashed',
          lineJoin: 'round',
        })
        pl.setMap(map)
        allPolylinesRef.current.push(pl)
      }
    })

    // Fit all POIs
    if (allPoints.length > 0) {
      map.setFitView(allMarkersRef.current, false, [50, 50, 50, compact ? 80 : 40])
    }

    mapRef.current = map

    // Apply any pending focus that arrived before map was ready
    applyPendingFocus()

    return () => {
      allMarkersRef.current.forEach(m => m.setMap(null))
      allPolylinesRef.current.forEach(p => p.setMap(null))
      if (mapRef.current) mapRef.current.destroy()
    }
  }, [allDays, effectiveDay, compact, loading])

  // Apply pending focus: center map on a specific POI
  const applyPendingFocus = useCallback(() => {
    const poiId = pendingFocusRef.current
    if (!poiId || !mapRef.current || !allDays.length) return
    for (const day of allDays) {
      const poi = day.pois.find(p => p.id === poiId)
      if (poi && poi.lng && poi.lat) {
        mapRef.current.setZoomAndCenter(16, [poi.lng, poi.lat])
        setSelectedPoi(poi)
        pendingFocusRef.current = null
        break
      }
    }
  }, [allDays])

  // 5. External focus request: store ID, apply when map ready
  useEffect(() => {
    pendingFocusRef.current = focusPoiId || null
    applyPendingFocus()
  }, [focusPoiId, applyPendingFocus])

  // ── render ───────────────────────────────────────────────────

  const h = compact ? 'h-64' : 'h-full'
  const allPois = allDays.flatMap(d => d.pois).filter(p => p.lng && p.lat)

  // Find next POI for selected
  let nextPoi: Poi | null = null
  let dist: string | undefined
  if (selectedPoi) {
    const flat = allDays.flatMap(d => d.pois)
    const idx = flat.findIndex(p => p.id === selectedPoi.id)
    if (idx >= 0 && idx < flat.length - 1) {
      nextPoi = flat[idx + 1]
      dist = walkDistance(selectedPoi, nextPoi)
    }
  }

  if (error) {
    return <div className={`${h} bg-gray-100 rounded-xl flex items-center justify-center text-gray-400 text-sm`}>{error}</div>
  }

  return (
    <div className={`${className} flex flex-col`}>
      {/* Day filter bar — hidden when controlled externally by PC left panel */}
      {!selectedDay && (
        <div className="flex items-center gap-1.5 mb-2 shrink-0 flex-wrap">
          <span className="text-sm text-gray-500 mr-1">🗺️</span>
          <button
            onClick={() => setFilterDay(0)}
            className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${
              filterDay === 0 ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            全部
          </button>
          {allDays.map(d => (
            <button
              key={d.day_number}
              onClick={() => setFilterDay(d.day_number)}
              className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${
                d.day_number === filterDay
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              第{d.day_number}天
            </button>
          ))}
          <span className="text-xs text-gray-400 ml-auto">{allPois.length}个地点</span>
        </div>
      )}
      <div className={`${h} rounded-xl overflow-hidden border border-gray-200 flex-1 relative`}>
        {loading && (
          <div className="absolute inset-0 bg-gray-100 flex items-center justify-center z-10 rounded-xl">
            <span className="text-gray-400 text-sm">加载地图...</span>
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />
      </div>

      {/* Legend */}
      {!selectedDay && !compact && allDays.length > 1 && (
        <div className="flex gap-3 mt-1.5 text-xs text-gray-400 overflow-x-auto shrink-0">
          {allDays.map((day, i) => (
            <span key={day.day_number} className="flex items-center gap-1 whitespace-nowrap">
              <span className="w-2 h-2 rounded-full" style={{ background: DAY_COLORS[i % DAY_COLORS.length] }} />
              D{day.day_number}
            </span>
          ))}
        </div>
      )}

      {/* Poi detail card */}
      {selectedPoi && (
        <PoiDetailCard
          poi={selectedPoi}
          nextPoi={nextPoi}
          distance={dist}
          onClose={() => setSelectedPoi(null)}
          compact={compact}
        />
      )}
    </div>
  )
}
