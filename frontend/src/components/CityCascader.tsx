/**
 * CityCascader — 省市区三级联动选择器（含拼音搜索）
 * 数据源: /api/v1/info/locations (eduosi/district)
 */
import { useState, useEffect, useCallback, useMemo } from 'react'

interface Location {
  id: number
  name: string
  pinyin: string
  initials: string
  initial: string
  suffix: string
  parent_name?: string
  province_name?: string
}

interface Props {
  value: string
  onSelect: (name: string) => void
  onClose: () => void
  needsDistrict?: boolean
}

export default function CityCascader({ value, onSelect, onClose, needsDistrict = false }: Props) {
  const [provinces, setProvinces] = useState<Location[]>([])
  const [cities, setCities] = useState<Location[]>([])
  const [districts, setDistricts] = useState<Location[]>([])
  const [selectedProvince, setSelectedProvince] = useState<Location | null>(null)
  const [selectedCity, setSelectedCity] = useState<Location | null>(null)
  const [searchText, setSearchText] = useState('')
  const [searchResults, setSearchResults] = useState<Location[]>([])

  useEffect(() => {
    fetch('/api/v1/info/locations?pid=0')
      .then(r => r.json())
      .then(d => setProvinces(d.data || []))
      .catch(() => {})
  }, [])

  const selectProvince = useCallback((p: Location) => {
    setSelectedProvince(p)
    setCities([])
    setDistricts([])
    setSelectedCity(null)
    // 直辖市(suffix="市")或特别行政区 → 无需子级选择，直接作为城市
    if (!needsDistrict && (p.suffix === '市' || p.suffix === '特别行政区')) {
      onSelect(p.name)
      onClose()
      return
    }
    // 加载市级列表，同时拉取各区级节点合并显示
    fetch(`/api/v1/info/locations?pid=${p.id}`)
      .then(r => r.json())
      .then(async d => {
        const cityList = (d.data || []) as Location[]
        // 为每个市拉取其区级子节点，合并到列表
        const merged: Location[] = []
        for (const city of cityList) {
          merged.push(city)
          try {
            const res = await fetch(`/api/v1/info/locations?pid=${city.id}`)
            const j = await res.json()
            const subItems = (j.data || []) as Location[]
            for (const sub of subItems) {
              merged.push({ ...sub, parent_name: city.name })
            }
          } catch { /* skip */ }
        }
        setCities(merged)
      })
      .catch(() => {})
  }, [needsDistrict, onSelect, onClose])

  const selectCity = useCallback((c: Location) => {
    // 带 parent_name 的是区级节点，直接选中
    if (c.parent_name) {
      onSelect(c.name)
      onClose()
      return
    }
    setSelectedCity(c)
    setDistricts([])
    if (!needsDistrict) {
      onSelect(c.name)
      onClose()
    } else {
      fetch(`/api/v1/info/locations?pid=${c.id}`)
        .then(r => r.json())
        .then(d => setDistricts(d.data || []))
        .catch(() => {})
    }
  }, [needsDistrict, onSelect, onClose])

  const selectDistrict = useCallback((d: Location) => {
    onSelect(d.name)
    onClose()
  }, [onSelect, onClose])

  useEffect(() => {
    if (!searchText || searchText.length < 1) {
      setSearchResults([])
      return
    }
    const timer = setTimeout(() => {
      fetch(`/api/v1/info/locations/search?keyword=${encodeURIComponent(searchText)}&limit=20`)
        .then(r => r.json())
        .then(d => setSearchResults(d.data || []))
        .catch(() => {})
    }, 200)
    return () => clearTimeout(timer)
  }, [searchText])

  const provinceGroups = useMemo(() => {
    const groups: Record<string, Location[]> = {}
    for (const p of provinces) {
      const key = p.initial.toUpperCase()
      if (!groups[key]) groups[key] = []
      groups[key].push(p)
    }
    return groups
  }, [provinces])

  const goBack = () => {
    if (districts.length > 0) setDistricts([])
    else if (selectedCity) setSelectedCity(null)
    else if (selectedProvince) { setSelectedProvince(null); setCities([]) }
  }

  const showBack = selectedProvince !== null

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center" onClick={onClose}>
      <div className="bg-white rounded-t-2xl w-full max-w-md max-h-[55vh] flex flex-col" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="px-3 pt-2 pb-1.5 border-b border-gray-100 flex-shrink-0">
          <div className="flex items-center gap-1.5 mb-1.5">
            {showBack && (
              <button onClick={goBack} className="text-gray-400 hover:text-gray-600 p-0.5 -ml-0.5">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </button>
            )}
            <span className="text-xs font-medium text-gray-500 flex-1">
              {selectedCity ? selectedCity.name : selectedProvince ? selectedProvince.name : '选择城市'}
            </span>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-0.5 -mr-0.5">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <input
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            placeholder="搜索（拼音/首字母/汉字）"
            className="w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs bg-gray-50 focus:bg-white focus:border-primary-400 outline-none"
            autoFocus
          />
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto px-3 py-2">
          {searchText ? (
            <div className="space-y-0.5">
              {searchResults.length === 0 ? (
                <div className="text-center text-gray-400 text-xs py-8">未找到匹配城市</div>
              ) : (
                searchResults.map(r => (
                  <button
                    key={r.id}
                    onClick={() => { onSelect(r.name); onClose() }}
                    className={`w-full text-left px-2.5 py-2 rounded-lg text-xs hover:bg-gray-50 flex items-center justify-between ${
                      r.name === value ? 'bg-primary-50 text-primary-600' : 'text-gray-700'
                    }`}
                  >
                    <span>
                      {r.name}
                      {r.parent_name ? (
                        <span className="text-gray-400 text-[10px] ml-1">{r.parent_name}</span>
                      ) : r.suffix ? (
                        <span className="text-gray-400 text-[10px] ml-1">{r.suffix}</span>
                      ) : null}
                    </span>
                    <span className="text-[10px] text-gray-300 ml-1.5 flex-shrink-0">{r.pinyin}</span>
                  </button>
                ))
              )}
            </div>
          ) : !selectedProvince ? (
            /* Province list */
            <div className="space-y-3">
              {Object.entries(provinceGroups).map(([letter, group]) => (
                <div key={letter}>
                  <div className="text-[10px] text-gray-400 font-medium mb-1 ml-0.5">{letter}</div>
                  <div className="flex flex-wrap gap-1">
                    {group.map(p => (
                      <button
                        key={p.id}
                        onClick={() => selectProvince(p)}
                        className={`px-2.5 py-1 rounded-full text-[11px] leading-tight transition-colors ${
                          p.name === value
                            ? 'bg-primary-600 text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-primary-50 hover:text-primary-600'
                        }`}
                      >
                        {p.name}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : !selectedCity ? (
            /* City list (含区级节点) */
            <div className="space-y-0.5">
              {cities.map(c => (
                <button
                  key={c.id}
                  onClick={() => selectCity(c)}
                  className={`w-full text-left px-2.5 py-2 rounded-lg text-xs hover:bg-gray-50 flex items-center justify-between ${
                    c.name === value ? 'bg-primary-50 text-primary-600' : 'text-gray-700'
                  }`}
                >
                  <span>
                    {c.name}
                    {c.parent_name ? (
                      <span className="text-gray-400 text-[10px] ml-1">{c.parent_name}</span>
                    ) : c.suffix ? (
                      <span className="text-gray-400 text-[10px] ml-1">{c.suffix}</span>
                    ) : null}
                  </span>
                  <span className="text-[10px] text-gray-300 ml-1.5 flex-shrink-0">{c.pinyin}</span>
                </button>
              ))}
            </div>
          ) : (
            /* District list */
            <div className="flex flex-wrap gap-1">
              {districts.map(d => (
                <button
                  key={d.id}
                  onClick={() => selectDistrict(d)}
                  className="px-2.5 py-1 rounded-full text-[11px] leading-tight bg-gray-100 text-gray-600 hover:bg-primary-50 hover:text-primary-600 transition-colors"
                >
                  {d.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
