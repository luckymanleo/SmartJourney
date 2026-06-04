import { useState, useEffect, useCallback, useMemo } from 'react'

interface Location {
  id: number; name: string; pinyin: string; initials: string
  initial: string; suffix: string; parent_name?: string; province_name?: string
}

interface Props {
  value: string
  onSelect: (name: string) => void
  onClose: () => void
  needsDistrict?: boolean
}

export default function CityCascaderPC({ value, onSelect, onClose, needsDistrict = false }: Props) {
  const [provinces, setProvinces] = useState<Location[]>([])
  const [cities, setCities] = useState<Location[]>([])
  const [districts, setDistricts] = useState<Location[]>([])
  const [selectedProvince, setSelectedProvince] = useState<Location | null>(null)
  const [selectedCity, setSelectedCity] = useState<Location | null>(null)
  const [searchText, setSearchText] = useState('')
  const [searchResults, setSearchResults] = useState<Location[]>([])

  useEffect(() => {
    fetch('/api/v1/info/locations?pid=0').then(r => r.json()).then(d => setProvinces(d.data || [])).catch(() => {})
  }, [])

  const selectProvince = useCallback((p: Location) => {
    setSelectedProvince(p); setCities([]); setDistricts([]); setSelectedCity(null)
    if (!needsDistrict && (p.suffix === '市' || p.suffix === '特别行政区')) { onSelect(p.name); onClose(); return }
    fetch(`/api/v1/info/locations?pid=${p.id}`).then(r => r.json()).then(async d => {
      const list = (d.data || []) as Location[]
      const merged: Location[] = []
      for (const city of list) {
        merged.push(city)
        try { const res = await fetch(`/api/v1/info/locations?pid=${city.id}`); const j = await res.json(); for (const sub of (j.data || [])) merged.push({ ...sub, parent_name: city.name }) } catch {}
      }
      setCities(merged)
    }).catch(() => {})
  }, [needsDistrict, onSelect, onClose])

  const selectCity = useCallback((c: Location) => {
    if (c.parent_name) { onSelect(c.name); onClose(); return }
    setSelectedCity(c); setDistricts([])
    if (!needsDistrict) { onSelect(c.name); onClose() }
    else { fetch(`/api/v1/info/locations?pid=${c.id}`).then(r => r.json()).then(d => setDistricts(d.data || [])).catch(() => {}) }
  }, [needsDistrict, onSelect, onClose])

  const selectDistrict = useCallback((d: Location) => { onSelect(d.name); onClose() }, [onSelect, onClose])

  useEffect(() => {
    if (!searchText) { setSearchResults([]); return }
    const t = setTimeout(() => {
      fetch(`/api/v1/info/locations/search?keyword=${encodeURIComponent(searchText)}&limit=20`).then(r => r.json()).then(d => setSearchResults(d.data || [])).catch(() => {})
    }, 200)
    return () => clearTimeout(t)
  }, [searchText])

  const provinceGroups = useMemo(() => {
    const g: Record<string, Location[]> = {}
    for (const p of provinces) { const k = p.initial.toUpperCase(); if (!g[k]) g[k] = []; g[k].push(p) }
    return g
  }, [provinces])

  const goBack = () => {
    if (districts.length) setDistricts([])
    else if (selectedCity) setSelectedCity(null)
    else if (selectedProvince) { setSelectedProvince(null); setCities([]) }
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40" onClick={onClose} />
      {/* Dropdown panel */}
      <div className="absolute top-full left-0 mt-1 z-50 bg-white rounded-xl border border-gray-200 shadow-xl w-72 max-h-80 flex flex-col">
        {/* Breadcrumb + Search */}
        <div className="px-3 py-2 border-b border-gray-100 flex items-center gap-2">
          {selectedProvince && (
            <button onClick={goBack} className="text-gray-400 hover:text-gray-600 flex-shrink-0">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M15 18l-6-6 6-6"/></svg>
            </button>
          )}
          <span className="text-xs font-medium text-gray-500 truncate">
            {selectedCity ? selectedCity.name : selectedProvince ? selectedProvince.name : '选择城市'}
          </span>
          <div className="flex-1" />
          <input value={searchText} onChange={e => setSearchText(e.target.value)}
            placeholder="搜索" className="w-24 text-xs border border-gray-200 rounded-md px-2 py-1 outline-none focus:border-primary-400" />
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-3">
          {searchText ? (
            <div className="space-y-0.5">
              {searchResults.length === 0 ? (
                <div className="text-center text-gray-400 text-xs py-4">未找到</div>
              ) : (
                searchResults.map(r => (
                  <button key={r.id} onClick={() => { onSelect(r.name); onClose() }}
                    className={`w-full text-left px-2.5 py-2 rounded-lg text-xs hover:bg-gray-50 flex items-center justify-between ${
                      r.name === value ? 'bg-primary-50 text-primary-600' : 'text-gray-700'
                    }`}>
                    <span>{r.name}{r.parent_name && <span className="text-gray-400 ml-1">{r.parent_name}</span>}</span>
                    <span className="text-[10px] text-gray-300">{r.pinyin}</span>
                  </button>
                ))
              )}
            </div>
          ) : !selectedProvince ? (
            <div>
              {Object.entries(provinceGroups).map(([letter, group]) => (
                <div key={letter} className="mb-2">
                  <div className="text-[10px] text-gray-400 font-medium mb-1">{letter}</div>
                  <div className="flex flex-wrap gap-1">
                    {group.map(p => (
                      <button key={p.id} onClick={() => selectProvince(p)}
                        className={`px-2 py-1 rounded-full text-[11px] transition-colors ${
                          p.name === value ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-primary-50 hover:text-primary-600'
                        }`}>{p.name}</button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : !selectedCity ? (
            <div className="space-y-0.5">
              {cities.map(c => (
                <button key={c.id} onClick={() => selectCity(c)}
                  className={`w-full text-left px-2.5 py-2 rounded-lg text-xs hover:bg-gray-50 flex items-center justify-between ${
                    c.name === value ? 'bg-primary-50 text-primary-600' : 'text-gray-700'
                  }`}>
                  <span>{c.name}{c.parent_name && <span className="text-gray-400 ml-1">{c.parent_name}</span>}</span>
                  <span className="text-[10px] text-gray-300">{c.pinyin}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-1">
              {districts.map(d => (
                <button key={d.id} onClick={() => selectDistrict(d)}
                  className="px-2 py-1 rounded-full text-[11px] bg-gray-100 text-gray-600 hover:bg-primary-50 hover:text-primary-600 transition-colors">{d.name}</button>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
