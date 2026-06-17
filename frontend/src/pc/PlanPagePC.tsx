import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Sparkles, Loader2, MapPin, Users, Calendar, DollarSign, Navigation, ArrowRight, List } from 'lucide-react'
import { usePlanStore } from '../stores/planStore'
import { parseTripQuery } from '../utils/parseQuery'
import TripTimeline from '../components/TripTimeline'
import LiveMapPreview from '../components/LiveMapPreview'
import LlmStreamBox from '../components/LlmStreamBox'
import BudgetPanel from '../components/BudgetPanel'

const STRATEGIES = [
  { label: '智能平衡', value: -1, emoji: '🎯' },
  { label: '经济实惠', value: 0,  emoji: '💰' },
  { label: '舒适优先', value: 1,  emoji: '🏨' },
  { label: '最快到达', value: 2,  emoji: '⚡' },
]

const DAY_COLORS = ['#3b82f6', '#f97316', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899']

export default function PlanPagePC() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') || ''

  const [query, setQuery] = useState('')
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [travelers, setTravelers] = useState<number | ''>('')
  const [budget, setBudget] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [useWeather, setUseWeather] = useState(true)
  const [routeStrategy, setRouteStrategy] = useState(-1)
  const [userEditedTravelers, setUserEditedTravelers] = useState(false)
  const [specialNotes, setSpecialNotes] = useState('')
  const prefApplied = useRef(false)

  useEffect(() => {
    if (initialQuery) {
      usePlanStore.setState({ tripData: null, tripRoutes: [], steps: [] })
      setQuery(initialQuery)
      const p = parseTripQuery(initialQuery)
      setOrigin(p.origin)
      if (p.destination) setDestination(p.destination)
      if (p.travelers) setTravelers(p.travelers)
      if (p.budget) setBudget(String(p.budget))
      if (p.startDate) setStartDate(p.startDate)
      if (p.endDate) setEndDate(p.endDate)
    }
  }, [initialQuery])

  useEffect(() => {
    import('../api').then(({ getPreferences }) => {
      getPreferences().then(r => {
        const d = r.data?.data
        if (d && !prefApplied.current) {
          if (typeof d.use_weather === 'boolean') setUseWeather(d.use_weather)
          if (typeof d.route_strategy === 'number') setRouteStrategy(d.route_strategy)
          if (typeof d.special_notes === 'string') setSpecialNotes(d.special_notes)
        }
      }).catch(() => {})
    })
  }, [])

  const { isPlanning, steps, tripData, tripRoutes, error, weatherData, startPlan, cancelPlan, selectRoute, toolPhase, toolCount } = usePlanStore()
  const planElapsed = usePlanStore(s => s.planElapsed)
  const totalElapsed = usePlanStore(s => s.totalElapsed)
  const [selectedRouteIdx, setSelectedRouteIdx] = useState(0)
  const currentTrip = tripRoutes[selectedRouteIdx] || tripData || tripRoutes[0]

  const handleGenerate = () => {
    const e: Record<string, string> = {}
    if (!query.trim()) e.query = '请描述出行需求'
    if (!origin.trim()) e.origin = '请填写出发地'
    if (!destination.trim()) e.destination = '请填写目的地'
    if (!startDate) e.startDate = '请选择出发日期'
    if (!endDate) e.endDate = '请选择返回日期'
    if (!budget || Number(budget) <= 0) e.budget = '请填写预算'
    if (!travelers || travelers < 1) e.travelers = '请填写出行人数'
    setFieldErrors(e); if (Object.keys(e).length) return
    startPlan({
      query: query.trim(), origin: origin || undefined, destination: destination || undefined,
      start_date: startDate || undefined, end_date: endDate || undefined,
      traveler_count: travelers || 1, budget_total: budget ? Number(budget) : undefined,
      save_as_trip: true, use_weather: useWeather, route_count: 1, route_strategy: routeStrategy,
      special_notes: specialNotes.trim() || undefined,
    })
  }

  const fs = {
    title: { fontSize: 'clamp(1rem, 1.3vw, 1.25rem)' },
    heading: { fontSize: 'clamp(0.875rem, 1.05vw, 1rem)' },
    label: { fontSize: 'clamp(0.75rem, 0.85vw, 0.8125rem)' },
    input: { fontSize: 'clamp(0.8125rem, 0.92vw, 0.9375rem)' },
    small: { fontSize: 'clamp(0.6875rem, 0.75vw, 0.75rem)' },
    btn: { fontSize: 'clamp(0.8125rem, 0.95vw, 0.9375rem)' },
  }

  const inputCls = (field: string) =>
    `w-full border rounded-lg outline-none transition-colors bg-white ${
      fieldErrors[field] ? 'border-red-400 focus:border-red-500' : 'border-gray-200 focus:border-primary-400 focus:ring-1 focus:ring-primary-200'
    }`

  const formPanel = (
    <div className="space-y-4">
      <div>
        <label className="font-medium text-gray-600 mb-2 block" style={fs.label}>出行需求</label>
        <textarea value={query} onChange={e => { setQuery(e.target.value); const p = parseTripQuery(e.target.value); setOrigin(p.origin || ''); setDestination(p.destination || ''); setTravelers(p.travelers || ''); setBudget(p.budget ? String(p.budget) : ''); setStartDate(p.startDate || ''); setEndDate(p.endDate || ''); if (!e.target.value.trim()) setUserEditedTravelers(false) }}
          placeholder="例如：北京出发三亚5天亲子游，预算1万" rows={3}
          className={inputCls('query') + ' resize-none'} style={{...fs.input, padding: 'clamp(8px, 1.2vh, 12px) clamp(10px, 1.5vw, 16px)'}} />
        {fieldErrors.query && <p className="text-red-500 mt-1" style={fs.small}>{fieldErrors.query}</p>}
      </div>
      <div className="grid gap-3" style={{gridTemplateColumns: 'repeat(auto-fit, minmax(clamp(120px, 45%, 200px), 1fr))'}}>
        <div><label className="font-medium text-gray-600 mb-2 flex items-center gap-1" style={fs.label}><Navigation size={13} />出发地</label><input value={origin} onChange={e => setOrigin(e.target.value)} placeholder="从上海出发" className={inputCls('origin')} style={{...fs.input, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1.2vw, 12px)'}} /></div>
        <div><label className="font-medium text-gray-600 mb-2 flex items-center gap-1" style={fs.label}><MapPin size={13} />目的地</label><input value={destination} onChange={e => setDestination(e.target.value)} placeholder="自动识别" className={inputCls('destination')} style={{...fs.input, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1.2vw, 12px)'}} /></div>
      </div>
      <div className="grid gap-3" style={{gridTemplateColumns: 'repeat(auto-fit, minmax(clamp(120px, 45%, 200px), 1fr))'}}>
        <div><label className="font-medium text-gray-600 mb-2 flex items-center gap-1" style={fs.label}><Users size={13} />出行人数</label><input type="number" value={travelers} min={1} onChange={e => { const v = e.target.value; setTravelers(v === '' ? '' : Number(v)); setUserEditedTravelers(true) }} className={inputCls('travelers')} style={{...fs.input, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1.2vw, 12px)'}} />{!userEditedTravelers && !travelers && !fieldErrors.travelers && <p className="text-blue-500 mt-1" style={fs.small}>💡 未识别到人数，请确认</p>}</div>
        <div><label className="font-medium text-gray-600 mb-2 flex items-center gap-1" style={fs.label}><DollarSign size={13} />预算（元）</label><input value={budget} onChange={e => setBudget(e.target.value)} type="number" placeholder="自动识别" className={inputCls('budget')} style={{...fs.input, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1.2vw, 12px)'}} /></div>
      </div>
      <div className="grid gap-3" style={{gridTemplateColumns: 'repeat(auto-fit, minmax(clamp(120px, 45%, 200px), 1fr))'}}>
        <div><label className="font-medium text-gray-600 mb-2 flex items-center gap-1" style={fs.label}><Calendar size={13} />出发日期</label><input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className={inputCls('startDate')} style={{...fs.input, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1.2vw, 12px)'}} /></div>
        <div><label className="font-medium text-gray-600 mb-2 flex items-center gap-1" style={fs.label}><Calendar size={13} />返回日期</label><input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className={inputCls('endDate')} style={{...fs.input, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1.2vw, 12px)'}} /></div>
      </div>
      <div>
        <label className="text-gray-600 mb-2 flex items-center gap-1" style={fs.label}>特殊说明 <span className="text-gray-300 font-normal">（选填）</span></label>
        <input value={specialNotes} onChange={e => setSpecialNotes(e.target.value)} placeholder="例如：花粉过敏、素食、行动不便"
          className="w-full border border-gray-200 rounded-lg outline-none focus:border-primary-400 bg-white" style={{...fs.input, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1.2vw, 12px)'}} />
      </div>
      <div>
        <label className="font-medium text-gray-600 mb-2 block" style={fs.label}>路线策略</label>
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          {STRATEGIES.map(s => (
            <button key={s.value} onClick={() => { prefApplied.current = true; setRouteStrategy(s.value) }}
              className={`flex-1 rounded-md text-center transition-all ${routeStrategy === s.value ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
              style={{...fs.small, padding: 'clamp(6px, 1vh, 10px) clamp(4px, 0.5vw, 8px)'}}>
              <div>{s.emoji}</div><div className="mt-0.5">{s.label}</div>
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
        <div><span className="text-gray-700" style={fs.label}>🌤️ 参考天气因素</span><p className="text-gray-400 mt-0.5" style={fs.small}>{useWeather ? '根据目的地天气自动调整行程' : '不考虑天气因素'}</p></div>
        <button onClick={() => { prefApplied.current = true; setUseWeather(!useWeather) }} className={`relative w-11 h-6 rounded-full transition-colors flex-shrink-0 ${useWeather ? 'bg-primary-500' : 'bg-gray-300'}`}>
          <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${useWeather ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </button>
      </div>
      {Object.keys(fieldErrors).length > 0 && <div className="bg-red-50 text-red-600 rounded-xl px-4 py-2.5 font-medium" style={fs.small}>请完善信息后再生成</div>}
      <button onClick={isPlanning ? cancelPlan : handleGenerate}
        style={{width:'55%', margin:'clamp(8px, 1.5vh, 16px) auto 0 auto', fontSize: 'clamp(0.8125rem, 0.95vw, 0.9375rem)'}}
        className={`rounded-2xl py-3.5 font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-sm whitespace-nowrap ${isPlanning ? 'bg-red-500 text-white hover:bg-red-600' : 'bg-primary-600 text-white hover:bg-primary-700'}`}>
        {isPlanning ? <><Loader2 size={18} className="animate-spin" />取消规划</> : <><Sparkles size={18} />开始智能规划</>}
      </button>
    </div>
  )

  const hasResults = tripRoutes.length > 0 || tripData
  const route = currentTrip

  return (
    <div className="h-full flex flex-col" style={{padding: 'clamp(12px, 1.5vw, 24px)'}}>
      <div className="flex items-center gap-2 mb-5">
        <Sparkles size={20} className="text-primary-600" />
        <h1 className="font-bold text-gray-800" style={fs.title}>AI 智能规划</h1>
      </div>

      <div className="flex-1 flex gap-0 min-h-0" style={{gap: 'clamp(12px, 1.5vw, 24px)'}}>

        <div className="overflow-y-auto" style={{flex: '0 0 35%'}}>
          {formPanel}
        </div>

        <div className="flex-1 min-w-0 overflow-y-auto">

          {isPlanning && (
            <div className="bg-white rounded-xl border border-gray-200" style={{padding: 'clamp(12px, 1.5vw, 24px)'}}>
              <h3 className="font-semibold text-gray-800 mb-4" style={fs.heading}>
                规划进度{planElapsed > 0 && <span className="text-gray-400 font-normal ml-1">· {planElapsed}s</span>}
              </h3>
              <div className="flex items-center gap-1.5 mb-3">
                <div className={`flex-1 h-2 rounded-full transition-colors ${toolPhase !== 'idle' ? 'bg-blue-500' : steps.length > 0 ? 'bg-blue-400 animate-pulse' : 'bg-gray-200'}`} />
                <div className={`flex-1 h-2 rounded-full transition-colors ${toolPhase === 'calling' ? 'bg-blue-400 animate-pulse' : toolPhase === 'done' ? 'bg-blue-500' : 'bg-gray-200'}`} />
                <div className={`flex-1 h-2 rounded-full transition-colors ${toolPhase === 'done' && !tripData ? 'bg-blue-400 animate-pulse' : tripData ? 'bg-blue-500' : 'bg-gray-200'}`} />
                <div className={`flex-1 h-2 rounded-full transition-colors ${tripData ? 'bg-green-500' : 'bg-gray-200'}`} />
              </div>
              <div className="flex justify-between text-gray-400 mb-3" style={fs.small}><span>分析</span><span>搜索</span><span>生成</span><span>完成</span></div>

              {/* 当前状态 — 搜索阶段在上 */}
              {toolPhase === 'calling' && (
                <div className="text-primary-600 font-medium mb-2" style={fs.label}>
                  <span className="text-green-500">✅ 出行需求分析完成</span><br/>并行搜索 {toolCount.total} 个数据源 ({toolCount.done}/{toolCount.total})
                </div>
              )}

              {/* 搜索详情 */}
              {!tripData && toolPhase !== 'idle' && (
                <div className="space-y-1 max-h-72 overflow-y-auto mb-3">
                  {(toolPhase==='done' ? steps.filter(s => s.type === 'tool_result') : steps.filter(s => s.type !== 'step')).slice(-12).map((s,i)=>(
                  <div key={i} className="flex items-center gap-2 py-0.5" style={fs.small}>
                    <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${s.type==='tool_call'?'bg-yellow-400':'bg-green-400'}`} />
                    <span className={s.type==='tool_call'?'text-yellow-600':'text-gray-400'}>{s.text}</span>
                  </div>
                ))}</div>
              )}

              {/* 当前状态 — 生成/完成阶段在下 */}
              <div className="text-primary-600 font-medium mb-2" style={fs.label}>
                {!steps.length && toolPhase === 'idle' && '准备中...'}
                {steps.length > 0 && toolPhase === 'idle' && steps[steps.length - 1].text}
                {toolPhase==='done'&&!tripData&&'✅正在生成行程方案...'}
                {toolPhase==='done'&&!tripData&&(
                  <LlmStreamBox />
                )}
                {tripData&&`✅行程方案规划完成 · 总耗时 ${totalElapsed}s`}
              </div>
            </div>
          )}

          <LiveMapPreview compact />

          {hasResults && route?.days && (
            <div className="space-y-4">
              <h2 className="font-bold text-gray-800" style={fs.heading}>{route.title || '行程方案'}</h2>
              {tripRoutes.length > 1 && (
                <div className="flex gap-2">
                  {tripRoutes.map((r:any,i:number)=>(
                    <button key={i} onClick={()=>{setSelectedRouteIdx(i);selectRoute(i)}}
                      className={`px-4 py-2 rounded-full font-medium ${i===selectedRouteIdx?'bg-primary-600 text-white shadow':'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}
                      style={fs.small}>{r.route_tag||`路线 ${i+1}`}</button>
                  ))}</div>
              )}
              {route.summary && <div className="bg-primary-50 rounded-xl p-4 text-gray-700" style={fs.small}>{route.summary}</div>}
              <TripTimeline days={route.days} travelerCount={travelers || 1} />
            </div>
          )}

          {!isPlanning && !hasResults && (
            <div className="flex items-center justify-center h-full"><div className="text-center"><div className="text-5xl mb-3">🗺️</div><p className="text-gray-400" style={fs.label}>在左侧填写出行信息后开始规划</p></div></div>
          )}

          {error && <div className="mt-4 bg-red-50 text-red-600 rounded-xl p-4" style={fs.small}>{error}</div>}
        </div>

        {hasResults && route && (
          <div className="overflow-y-auto space-y-3 pr-3" style={{flex: '0 0 25%'}}>
            <div className="flex gap-2">
              <button onClick={() => navigate('/trips')} className="flex-1 border border-primary-300 text-primary-600 rounded-lg font-medium hover:bg-primary-50 transition-colors text-center" style={{...fs.small, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1vw, 12px)'}}>我的行程</button>
              <button onClick={() => usePlanStore.setState({ tripData: null, tripRoutes: [], steps: [] })} className="flex-1 border border-gray-300 text-gray-600 rounded-lg font-medium hover:bg-gray-100 transition-colors text-center" style={{...fs.small, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1vw, 12px)'}}>重新规划</button>
            </div>
            {weatherData && (
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="font-semibold text-gray-600 mb-3" style={fs.small}>🌤️ 天气</div>
                <div className="space-y-3">
                  {weatherData.origin_weather && <div><div className="font-semibold text-gray-700 mb-1.5" style={fs.small}>🌤️ {weatherData.origin}（出发地）</div><div className="text-gray-500 leading-relaxed whitespace-pre-line" style={fs.small}>{weatherData.origin_weather}</div></div>}
                  {weatherData.dest_weather && <div className="pt-3 border-t border-gray-100"><div className="font-semibold text-gray-700 mb-1.5" style={fs.small}>🌤️ {weatherData.dest}（目的地）</div><div className="text-gray-500 leading-relaxed whitespace-pre-line" style={fs.small}>{weatherData.dest_weather}</div></div>}
                </div>
              </div>
            )}
            {route.tips && Array.isArray(route.tips) && (
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="font-semibold text-gray-600 mb-2" style={fs.small}>💡 出行提示</div>
                <ul className="text-gray-500 space-y-1.5 leading-relaxed" style={fs.small}>
                  {route.tips.map((tip: string, i: number) => <li key={i} className="flex gap-1.5"><span className="text-gray-300 flex-shrink-0">•</span><span>{tip}</span></li>)}
                </ul>
              </div>
            )}
            {route.budget && typeof route.budget === 'object' && (
              <BudgetPanel budget={{
                total_estimated: Object.values(route.budget).reduce((a: number, b: any) => a + (Number(b) || 0), 0),
                total_actual: 0,
                categories: Object.entries(route.budget).map(([cat, val]) => ({ category: cat, estimated: val as number, actual: 0, currency: 'CNY' })),
              }} originalBudget={Number(budget) || undefined} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
