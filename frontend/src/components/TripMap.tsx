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
  photos?: string[] | null
  amap_poi_id?: string | null
  day_number?: number
  item_index?: number
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
  selectedDay?: number
  focusPoiId?: string | null
  className?: string
}

export default function TripMap({ tripId, totalDays, compact = false, selectedDay, focusPoiId, className = '' }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const allPolylinesRef = useRef<any[]>([])

  const [allDays, setAllDays] = useState<DayData[]>([])
  const [filterDay, setFilterDay] = useState(0)
  const effectiveDay = selectedDay ?? filterDay
  const [selectedPoi, setSelectedPoi] = useState<Poi | null>(null)
  const pendingFocusRef = useRef<string | null>(null)

  useEffect(() => { if (selectedDay) setFilterDay(selectedDay) }, [selectedDay])
  useEffect(() => { setSelectedPoi(null) }, [effectiveDay])
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

  // 4a. Init map — 仅首次创建，切换天时不重建
  useEffect(() => {
    if (!allDays.length || !containerRef.current || mapRef.current) return
    const AMap = (window as any).AMap
    if (!AMap) return

    const allPoints: [number, number][] = []
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
    mapRef.current = map

    return () => {
      if (mapRef.current) { mapRef.current.destroy(); mapRef.current = null }
    }
  }, [allDays, loading])

  // 4b. Render markers — 同坐标聚合为圆圈+计数，点击展开
  useEffect(() => {
    if (!allDays.length || !mapRef.current) return
    const AMap = (window as any).AMap
    if (!AMap) return

    // 清旧
    allPolylinesRef.current.forEach(p => p.setMap(null))
    allPolylinesRef.current = []

    const map = mapRef.current
    const markers: any[] = []

    allDays.forEach((day, dayIdx) => {
      const color = DAY_COLORS[dayIdx % DAY_COLORS.length]
      const isFiltered = effectiveDay > 0 && day.day_number !== effectiveDay
      if (selectedDay && isFiltered) return
      const opacity = selectedDay ? 0.85 : (isFiltered ? 0.25 : 0.75)

      // 按坐标分组
      const groups: Record<string, typeof day.pois> = {}
      day.pois.forEach(poi => {
        if (!poi.lng || !poi.lat) return
        const key = `${poi.lng.toFixed(6)},${poi.lat.toFixed(6)}`
        if (!groups[key]) groups[key] = []
        groups[key].push(poi)
      })

      Object.entries(groups).forEach(([key, pois]) => {
        const [lng, lat] = key.split(',').map(Number)

        if (pois.length === 1) {
          // 单点：普通 marker
          const poi = pois[0]
          const m = new AMap.Marker({
            position: [lng, lat],
            label: {
              content: `<span style="font-size:10px;background:${color};color:#fff;padding:1px 5px;border-radius:10px;opacity:${opacity}">D${day.day_number}.${(poi.item_index ?? 0) + 1}</span>`,
              direction: 'top',
              offset: [0, -20],
            },
            zIndex: isFiltered ? 50 : 100,
            opacity,
          })
          m._poiData = poi
          m.on('click', () => setSelectedPoi(poi))
          m.setMap(map)
          markers.push(m)
        } else {
          // 多点聚合：圆圈+计数，点击弹出列表
          const circleSize = 28 + Math.min(pois.length, 5) * 2
          const m = new AMap.Marker({
            position: [lng, lat],
            content: `<div style="
              width:${circleSize}px;height:${circleSize}px;border-radius:50%;
              background:${color};color:#fff;font-size:${12 + Math.min(pois.length, 3)}px;
              font-weight:bold;display:flex;align-items:center;justify-content:center;
              border:2px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,0.3);
              opacity:${opacity};cursor:pointer
            ">${pois.length}</div>`,
            offset: new AMap.Pixel(-circleSize / 2, -circleSize / 2),
            zIndex: isFiltered ? 50 : 150,
          })
          m._groupPois = pois
          m._dayNumber = day.day_number
          m._color = color
          m.on('click', () => {
            // 关闭旧 infoWindow
            if ((m as any)._infoWin) (m as any)._infoWin.close()
            const items = pois.map(p => {
              const label = `D${day.day_number}.${(p.item_index ?? 0) + 1}`
              return `<div style="padding:6px 8px;cursor:pointer;border-bottom:1px solid #f0f0f0;font-size:13px;white-space:nowrap"
                onmouseover="this.style.background='#f5f5f5'" onmouseout="this.style.background=''"
                data-poi-id="${p.id}">
                <span style="display:inline-block;min-width:32px;background:${color};color:#fff;font-size:10px;text-align:center;border-radius:8px;padding:1px 4px;margin-right:6px">${label}</span>${p.title}
              </div>`
            }).join('')
            const iw = new AMap.InfoWindow({
              content: `<div style="max-width:260px;max-height:220px;overflow-y:auto;padding:4px 0">${items}</div>`,
              offset: new AMap.Pixel(0, -circleSize / 2 - 8),
            })
            iw.open(map, [lng, lat])
            ;(m as any)._infoWin = iw
            // 委托点击 InfoWindow 内的项
            setTimeout(() => {
              document.querySelectorAll('[data-poi-id]').forEach(el => {
                el.addEventListener('click', (e) => {
                  e.stopPropagation()
                  const pid = (el as HTMLElement).dataset.poiId
                  const found = pois.find(p => p.id === pid)
                  if (found) {
                    iw.close()
                    setSelectedPoi(found)
                  }
                })
              })
            }, 100)
          })
          m.setMap(map)
          markers.push(m)
        }
      })

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

    if (markers.length > 0) {
      map.setFitView(markers, false, [50, 50, 50, compact ? 80 : 40])
    }

    applyPendingFocus()
  }, [allDays, effectiveDay, compact])

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

      {selectedPoi && (
        <PoiDetailCard
          key={selectedPoi.id}
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
