import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useSearchStore, SearchHistoryItem } from '../stores/searchStore'
import { Clock, X, Trash2 } from 'lucide-react'
import { renderSearchCard } from '../components/SearchCards'
import CityCascader from './CityCascaderPC'

const TYPE_LABELS: Record<string, string> = {
  flights: '机票', trains: '火车票', hotels: '酒店',
  pois: '景点', foods: '美食', transport: '同城交通',
}

function historyLabel(h: SearchHistoryItem): string {
  const type = TYPE_LABELS[h.type] || h.type
  const parts: string[] = [type]
  if (h.type === 'transport' && h.city) { parts.push(h.city); if (h.from && h.to) parts.push(`${h.from} → ${h.to}`) }
  else if (h.from && h.to) parts.push(`${h.from} → ${h.to}`)
  if (h.city && h.type !== 'transport') parts.push(h.city)
  if (h.keyword) parts.push(h.keyword)
  return parts.join(' · ')
}

export default function SearchPagePC() {
  const { type } = useParams<{ type: string }>()
  const [searchParams] = useSearchParams()
  const { results, loading, error, search, history, removeHistory, clearHistory } = useSearchStore()
  const [from, setFrom] = useState(searchParams.get('from') || '')
  const [to, setTo] = useState(searchParams.get('to') || '')
  const [city, setCity] = useState(searchParams.get('city') || '')
  const [date, setDate] = useState(searchParams.get('date') || '')
  const [keyword, setKeyword] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [fromOpen, setFromOpen] = useState(false)
  const [toOpen, setToOpen] = useState(false)
  const [cityOpen, setCityOpen] = useState(false)
  const today = new Date().toISOString().split('T')[0]

  const needsCity = type === 'hotels' || type === 'pois' || type === 'foods' || type === 'transport'
  const needsFromTo = type === 'flights' || type === 'trains'
  const needsDate = type === 'flights' || type === 'trains'
  const isTransport = type === 'transport'
  const typeHistory = type ? history.filter(h => h.type === type) : []

  const searchFromHistory = (h: SearchHistoryItem) => {
    setFrom(h.from || ''); setTo(h.to || ''); setCity(h.city || ''); setDate(h.date || ''); setKeyword(h.keyword || '')
    const params: Record<string, any> = {}
    if (h.from) params.from = h.from; if (h.to) params.to = h.to; if (h.city) params.city = h.city
    if (h.date || needsDate) params.date = h.date || today
    if (h.keyword) params.keyword = h.keyword
    setHasSearched(true)
    if (type) search(type, params)
  }

  useEffect(() => {
    setFrom(searchParams.get('from') || ''); setTo(searchParams.get('to') || '')
    setCity(searchParams.get('city') || ''); setDate(searchParams.get('date') || '')
    setKeyword(''); setHasSearched(false)
    useSearchStore.setState({ results: [], error: null })
  }, [type])

  const handleSearch = () => {
    const params: Record<string, any> = {}
    if (from) params.from = from; if (to) params.to = to; if (city) params.city = city
    if (needsDate) params.date = date || today; else if (date) params.date = date
    if (keyword) params.keyword = keyword
    setHasSearched(true)
    if (type) search(type, params)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === 'Enter') handleSearch() }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
        <div className="flex flex-wrap items-end gap-3">
          {needsFromTo && (
            <>
              <div className="flex-1 min-w-[160px]">
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">出发城市</label>
                <div className="relative">
                  <input value={from} onChange={e => setFrom(e.target.value)} onKeyDown={handleKeyDown} placeholder="出发城市" className="w-full border rounded-lg pl-4 pr-10 py-3 text-[15px]" />
                  <button onClick={() => setFromOpen(!fromOpen)} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500 text-sm leading-none">▼</button>
                  {fromOpen && <CityCascader value={from} onSelect={c => { setFrom(c); setFromOpen(false) }} onClose={() => setFromOpen(false)} />}
                </div>
              </div>
              <div className="flex-1 min-w-[160px]">
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">到达城市</label>
                <div className="relative">
                  <input value={to} onChange={e => setTo(e.target.value)} onKeyDown={handleKeyDown} placeholder="到达城市" className="w-full border rounded-lg pl-4 pr-10 py-3 text-[15px]" />
                  <button onClick={() => setToOpen(!toOpen)} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500 text-sm leading-none">▼</button>
                  {toOpen && <CityCascader value={to} onSelect={c => { setTo(c); setToOpen(false) }} onClose={() => setToOpen(false)} />}
                </div>
              </div>
            </>
          )}
          {needsDate && (
            <div className="flex-1 min-w-[180px]">
              <label className="text-xs font-medium text-gray-500 mb-1.5 block">出发日期</label>
              <input type="date" value={date} onChange={e => setDate(e.target.value)} min={today} className="w-full border rounded-lg px-4 py-3 text-[15px]" />
            </div>
          )}
          {needsCity && !isTransport && (
            <>
              <div className="flex-1 min-w-[120px]">
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">城市</label>
                <div className="relative">
                  <input value={city} onChange={e => setCity(e.target.value)} onKeyDown={handleKeyDown} placeholder="选择城市" className="w-full border rounded-lg pl-4 pr-10 py-3 text-[15px]" />
                  <button onClick={() => setCityOpen(!cityOpen)} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500 text-sm leading-none">▼</button>
                  {cityOpen && <CityCascader value={city} onSelect={c => { setCity(c); setCityOpen(false) }} onClose={() => setCityOpen(false)} />}
                </div>
              </div>
              <div className="flex-1 min-w-[120px]">
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">关键词</label>
                <input value={keyword} onChange={e => setKeyword(e.target.value)} onKeyDown={handleKeyDown} placeholder="关键词" className="w-full border rounded-lg px-4 py-3 text-[15px]" />
              </div>
            </>
          )}
          {isTransport && (
            <>
              <div className="flex-1 min-w-[140px]">
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">所在城市</label>
                <div className="relative">
                  <input value={city} onChange={e => setCity(e.target.value)} onKeyDown={handleKeyDown} placeholder="选择城市" className="w-full border rounded-lg pl-4 pr-10 py-3 text-[15px]" />
                  <button onClick={() => setCityOpen(!cityOpen)} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-500 text-sm leading-none">▼</button>
                  {cityOpen && <CityCascader value={city} onSelect={c => { setCity(c); setCityOpen(false) }} onClose={() => setCityOpen(false)} />}
                </div>
              </div>
              <div className="flex-1 min-w-[150px]">
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">出发地点</label>
                <input value={from} onChange={e => setFrom(e.target.value)} onKeyDown={handleKeyDown} placeholder="如宝安机场" className="w-full border rounded-lg px-4 py-3 text-[15px]" />
              </div>
              <div className="flex-1 min-w-[150px]">
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">目的地</label>
                <input value={to} onChange={e => setTo(e.target.value)} onKeyDown={handleKeyDown} placeholder="如深圳北站" className="w-full border rounded-lg px-4 py-3 text-[15px]" />
              </div>
            </>
          )}
          <button onClick={handleSearch} disabled={loading}
            className="bg-primary-600 text-white rounded-lg px-8 py-3 text-[15px] font-medium disabled:opacity-50 hover:bg-primary-700 transition-colors whitespace-nowrap">
            {loading ? '搜索中...' : '搜索'}
          </button>
        </div>
      </div>

      {loading && <div className="text-center py-12 text-gray-400 text-sm">加载中...</div>}

      {!loading && error && (
        <div className="bg-red-50 text-red-600 rounded-xl p-4 text-sm mb-4">
          <div className="font-medium mb-1">搜索失败</div><div className="text-xs">{error}</div>
          <button onClick={handleSearch} className="mt-2 text-xs text-red-600 underline">重试</button>
        </div>
      )}

      {!loading && !error && hasSearched && results.length === 0 && (
        <div className="text-center py-16"><div className="text-5xl mb-4">🔍</div><div className="text-gray-500 mb-2">未找到相关结果</div><div className="text-xs text-gray-400">尝试更换关键词或城市</div></div>
      )}

      {!loading && !error && !hasSearched && (
        <div>
          {typeHistory.length > 0 ? (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-1.5 text-sm text-gray-500"><Clock size={14} /><span>搜索历史</span></div>
                <button onClick={clearHistory} className="text-xs text-gray-400 hover:text-red-400 flex items-center gap-1"><Trash2 size={12} />清空</button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                {typeHistory.map((h, i) => {
                  const gi = history.indexOf(h)
                  return (
                    <div key={i} className="flex items-center group">
                      <button onClick={() => searchFromHistory(h)} className="flex-1 text-left text-sm text-gray-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg px-3 py-2 transition-colors flex items-center gap-2">
                        <Clock size={12} className="text-gray-300 flex-shrink-0" /><span className="truncate">{historyLabel(h)}</span>
                      </button>
                      <button onClick={() => removeHistory(gi)} className="p-1 text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"><X size={14} /></button>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : (
            <div className="text-center py-16"><div className="text-5xl mb-4">{isTransport ? '🚗' : '👆'}</div><div className="text-gray-400 text-sm">{isTransport ? '选择城市，输入具体出发地和目的地，点击搜索' : '选择城市和关键词，点击搜索'}</div></div>
          )}
        </div>
      )}

      {!loading && results.length > 0 && (
        <div>
          <div className="text-sm text-gray-500 mb-3">共 {results.length} 条结果</div>
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
            {results.map((item: any, idx: number) => renderSearchCard(item, idx))}
          </div>
        </div>
      )}
    </div>
  )
}
