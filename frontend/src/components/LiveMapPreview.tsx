import { useEffect, useRef, useState } from 'react'
import { usePlanStore } from '../stores/planStore'

export default function LiveMapPreview({ compact = false }: { compact?: boolean }) {
  const poiCoords = usePlanStore(s => s.poiCoords)
  const isPlanning = usePlanStore(s => s.isPlanning)
  const tripData = usePlanStore(s => s.tripData)
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const markersRef = useRef<any[]>([])
  const [amapReady, setAmapReady] = useState(false)

  // Load Amap SDK
  useEffect(() => {
    const Am = (window as any).AMap
    if (Am) { setAmapReady(true); return }

    const isPC = typeof window !== 'undefined' && window.location.pathname.startsWith('/pc.html')
    const tokenKey = isPC ? 'sj_pc_token' : 'sj_token'
    const token = (() => { try { return sessionStorage.getItem(tokenKey) || '' } catch { return '' } })()
    fetch('/api/v1/map/config', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(cfg => {
        if (cfg.code === 0 && cfg.data?.js_key) {
          const s = document.createElement('script')
          s.src = `https://webapi.amap.com/maps?v=2.0&key=${cfg.data.js_key}`
          s.async = true
          s.onload = () => setAmapReady(true)
          document.head.appendChild(s)
        }
      })
      .catch(() => {})
  }, [])

  // Render markers when poiCoords change
  useEffect(() => {
    const Am = (window as any).AMap
    if (!Am || !amapReady || !containerRef.current || poiCoords.length === 0) return

    // Create map if not exists
    if (!mapRef.current) {
      const cx = poiCoords.reduce((s, c) => s + c.lng, 0) / poiCoords.length
      const cy = poiCoords.reduce((s, c) => s + c.lat, 0) / poiCoords.length
      mapRef.current = new Am.Map(containerRef.current, {
        zoom: 12, center: [cx, cy], resizeEnable: true,
      })
    }

    const map = mapRef.current

    // Clear old markers
    markersRef.current.forEach(m => m.setMap(null))
    markersRef.current = []

    // Add all markers
    poiCoords.forEach(c => {
      const label = `D${c.day}.${c.idx + 1}`
      const m = new Am.Marker({
        position: [c.lng, c.lat],
        label: {
          content: `<span style="font-size:9px;background:#3b82f6;color:#fff;padding:1px 4px;border-radius:10px">${label}</span>`,
          direction: 'top', offset: [0, -18],
        },
      })
      m.setMap(map)
      markersRef.current.push(m)
    })

    // Auto-fit if trip is done
    if (tripData) {
      map.setFitView(markersRef.current, false, [30, 30, 30, 30])
    }
  }, [poiCoords, tripData, amapReady])

  // Cleanup
  useEffect(() => {
    return () => {
      markersRef.current.forEach(m => m.setMap(null))
      if (mapRef.current) mapRef.current.destroy()
    }
  }, [])

  if (!isPlanning || poiCoords.length === 0) return null

  const h = compact ? 'h-52' : 'h-64'

  return (
    <div className="mt-3 mb-3">
      <div className="text-xs text-primary-600 font-medium mb-1.5">
        🗺️ 实时地图预览 ({poiCoords.length} 个节点已定位)
      </div>
      <div className={`${h} rounded-xl overflow-hidden border border-primary-200 relative`}>
        <div ref={containerRef} className="w-full h-full" />
      </div>
    </div>
  )
}
