import { useEffect, useState, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useSearchStore, SearchHistoryItem } from '../stores/searchStore'
import { Clock, X, Trash2 } from 'lucide-react'
import { renderSearchCard } from '../components/SearchCards'
import CityCascader from '../components/CityCascader'

const TYPE_LABELS: Record<string, string> = {
  flights: '机票', trains: '火车票', hotels: '酒店',
  pois: '景点', foods: '美食', transport: '同城交通',
}

function historyLabel(h: SearchHistoryItem): string {
  const type = TYPE_LABELS[h.type] || h.type
  const parts: string[] = [type]
  if (h.type === 'transport' && h.city) {
    parts.push(h.city)
    if (h.from && h.to) parts.push(`${h.from} → ${h.to}`)
  } else if (h.from && h.to) {
    parts.push(`${h.from} → ${h.to}`)
  }
  if (h.city && h.type !== 'transport') parts.push(h.city)
  if (h.keyword) parts.push(h.keyword)
  return parts.join(' · ')
}

export default function SearchPage() {
  const { type } = useParams<{ type: string }>()
  const [searchParams] = useSearchParams()
  const { results, loading, error, search, history, removeHistory, clearHistory } = useSearchStore()
  const [from, setFrom] = useState(searchParams.get('from') || '')
  const [to, setTo] = useState(searchParams.get('to') || '')
  const [city, setCity] = useState(searchParams.get('city') || '')
  const [date, setDate] = useState(searchParams.get('date') || '')
  const [keyword, setKeyword] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [showFromPicker, setShowFromPicker] = useState(false)
  const [showToPicker, setShowToPicker] = useState(false)
  const today = new Date().toISOString().split('T')[0]

  const searchFromHistory = (h: SearchHistoryItem) => {
    setFrom(h.from || '')
    setTo(h.to || '')
    setCity(h.city || '')
    setDate(h.date || '')
    setKeyword(h.keyword || '')
    const params: Record<string, any> = {}
    if (h.from) params.from = h.from
    if (h.to) params.to = h.to
    if (h.city) params.city = h.city
    if (h.date || needsDate) params.date = h.date || today
    if (h.keyword) params.keyword = h.keyword
    setHasSearched(true)
    if (type) search(type, params)
  }

  useEffect(() => {
    setFrom(searchParams.get('from') || '')
    setTo(searchParams.get('to') || '')
    setCity(searchParams.get('city') || '')
    setDate(searchParams.get('date') || '')
    setKeyword('')
    setHasSearched(false)
    useSearchStore.setState({ results: [], error: null })
  }, [type])

  const handleSearch = () => {
    const params: Record<string, any> = {}
    if (from) params.from = from
    if (to) params.to = to
    if (city) params.city = city
    if (needsDate) params.date = date || today
    else if (date) params.date = date
    if (keyword) params.keyword = keyword
    setHasSearched(true)
    if (type) search(type, params)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  const needsCity = type === 'hotels' || type === 'pois' || type === 'foods' || type === 'transport'
  const needsFromTo = type === 'flights' || type === 'trains'
  const needsDate = type === 'flights' || type === 'trains'
  const isTransport = type === 'transport'
  const typeHistory = type ? history.filter(h => h.type === type) : []

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold text-gray-800 mb-4">{TYPE_LABELS[type || ''] || '搜索'}</h1>
      <div className="space-y-3 mb-4">
        {needsFromTo && (
          <>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input value={from} onChange={e => setFrom(e.target.value)} onKeyDown={handleKeyDown}
                  placeholder="出发城市" className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 pr-8" />
                <button onClick={() => setShowFromPicker(true)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500 p-1 text-lg">▼</button>
              </div>
              <div className="flex-1 relative">
                <input value={to} onChange={e => setTo(e.target.value)} onKeyDown={handleKeyDown}
                  placeholder="到达城市" className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 pr-8" />
                <button onClick={() => setShowToPicker(true)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500 p-1 text-lg">▼</button>
              </div>
            </div>
          </>
        )}
        {needsDate && (
          <div>
            <label className="text-xs text-gray-500 mb-1 block">出发日期</label>
            <input type="date" value={date} onChange={e => setDate(e.target.value)} min={today}
              className="w-full border-2 border-gray-200 focus:border-primary-400 rounded-lg px-3 py-2.5 text-sm bg-white" />
            {!date && <div className="text-[10px] text-gray-400 mt-1">请选择日期</div>}
          </div>
        )}
        {needsCity && !isTransport && (
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <input value={city} onChange={e => setCity(e.target.value)} onKeyDown={handleKeyDown}
                placeholder="城市" className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 pr-8" />
              <button onClick={() => setShowFromPicker(true)}
                className="absolute right-1 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500 p-1 text-lg">▼</button>
            </div>
            <input value={keyword} onChange={e => setKeyword(e.target.value)} onKeyDown={handleKeyDown} placeholder="关键词"
              className="flex-1 border rounded-lg px-3 py-2 text-sm bg-gray-50" />
          </div>
        )}
        {type === 'transport' && (
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">所在城市</label>
              <div className="relative">
                <input value={city} onChange={e => setCity(e.target.value)} onKeyDown={handleKeyDown}
                  placeholder="选择城市" className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 pr-8" />
                <button onClick={() => setShowFromPicker(true)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500 p-1 text-lg">▼</button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <input value={from} onChange={e => setFrom(e.target.value)} onKeyDown={handleKeyDown}
                  placeholder="出发地点（如宝安机场）" className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50" />
              </div>
              <span className="text-gray-400 text-lg flex-shrink-0">→</span>
              <div className="flex-1">
                <input value={to} onChange={e => setTo(e.target.value)} onKeyDown={handleKeyDown}
                  placeholder="目的地（如深圳北站）" className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50" />
              </div>
            </div>
            <div className="text-[11px] text-gray-400 flex items-center gap-1">
              <span>🚗</span>
              <span>同城导航 · 输入具体地点如机场、火车站、商圈、景点</span>
            </div>
          </div>
        )}
        <button onClick={handleSearch} disabled={loading}
          className="w-full bg-primary-600 text-white rounded-lg py-2.5 font-medium disabled:opacity-50 flex items-center justify-center gap-2">
          {loading ? '搜索中...' : '搜索'}
        </button>
      </div>

      {loading && (
        <div className="text-center py-8 text-gray-400 text-sm">加载中...</div>
      )}

      {!loading && error && (
        <div className="bg-red-50 text-red-600 rounded-xl p-4 text-sm mb-4 flex items-start gap-2">
          <span>⚠️</span>
          <div>
            <div className="font-medium mb-1">搜索失败</div>
            <div className="text-xs text-red-500">{error}</div>
            <button onClick={handleSearch} className="mt-2 text-xs text-red-600 underline">重试</button>
          </div>
        </div>
      )}

      {!loading && !error && hasSearched && results.length === 0 && (
        <div className="text-center py-16">
          <div className="text-5xl mb-4">🔍</div>
          <div className="text-gray-500 mb-2">未找到相关结果</div>
          <div className="text-xs text-gray-400">尝试更换关键词或城市</div>
        </div>
      )}

      {!loading && !error && !hasSearched && (
        <div>
          {typeHistory.length > 0 ? (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 text-sm text-gray-500">
                  <Clock size={14} />
                  <span>搜索历史</span>
                </div>
                <button onClick={clearHistory}
                  className="text-xs text-gray-400 hover:text-red-400 flex items-center gap-1">
                  <Trash2 size={12} /> 清空
                </button>
              </div>
              <div className="space-y-1">
                {typeHistory.map((h, i) => {
                  const globalIdx = history.indexOf(h)
                  return (
                    <div key={i} className="flex items-center group">
                      <button onClick={() => searchFromHistory(h)}
                        className="flex-1 text-left text-sm text-gray-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg px-3 py-2 transition-colors flex items-center gap-2">
                        <Clock size={12} className="text-gray-300 group-hover:text-primary-300 flex-shrink-0" />
                        <span className="truncate">{historyLabel(h)}</span>
                      </button>
                      <button onClick={() => removeHistory(globalIdx)}
                        className="p-1 text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                        <X size={14} />
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : (
            <div className="text-center py-16">
              <div className="text-5xl mb-4">{isTransport ? '🚗' : '👆'}</div>
              <div className="text-gray-400 text-sm">
                {isTransport ? '选择城市，输入具体出发地和目的地，点击搜索' : '选择城市和关键词，点击搜索'}
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-3">
          {(type === 'flights' || type === 'trains') && !results[0]?.extra_data?.is_info && (
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <span>{type === 'flights' ? '✈' : '🚄'}</span>
              <span className="font-medium">{type === 'flights' ? '航班信息' : '车次信息'}</span>
            </div>
          )}
          {results.map((item: any, idx: number) => renderSearchCard(item, idx))}
        </div>
      )}

      {showFromPicker && (
        <CityCascader value={needsCity ? city : from}
          onSelect={c => { needsCity ? setCity(c) : setFrom(c); setShowFromPicker(false) }}
          onClose={() => setShowFromPicker(false)} />
      )}
      {showToPicker && !needsCity && (
        <CityCascader value={to}
          onSelect={c => { setTo(c); setShowToPicker(false) }}
          onClose={() => setShowToPicker(false)} />
      )}
    </div>
  )
}
