import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Sparkles, Loader2, MapPin, Users, Calendar, DollarSign, Navigation, ArrowRight, List } from 'lucide-react'
import { usePlanStore } from '../stores/planStore'
import { parseTripQuery } from '../utils/parseQuery'
import TripTimeline from '../components/TripTimeline'
import BudgetPanel from '../components/BudgetPanel'

const STRATEGIES = [
  { label: '智能平衡', value: -1, emoji: '🎯' },
  { label: '经济实惠', value: 0,  emoji: '💰' },
  { label: '舒适优先', value: 1,  emoji: '🏨' },
  { label: '最快到达', value: 2,  emoji: '⚡' },
]

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
        }
      }).catch(() => {})
    })
  }, [])

  const { isPlanning, steps, tripData, tripRoutes, error, weatherData, startPlan, cancelPlan, selectRoute, toolPhase, toolCount } = usePlanStore()
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
    })
  }

  const inputCls = (field: string) =>
    `w-full border rounded-lg px-4 py-3 text-[15px] outline-none transition-colors bg-white ${
      fieldErrors[field] ? 'border-red-400 focus:border-red-500' : 'border-gray-200 focus:border-primary-400 focus:ring-1 focus:ring-primary-200'
    }`

  // ── Left: Form Panel ──
  const formPanel = (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium text-gray-600 mb-2 block">出行需求</label>
        <textarea value={query}
          onChange={e => { setQuery(e.target.value); const p = parseTripQuery(e.target.value); setOrigin(p.origin || ''); setDestination(p.destination || ''); setTravelers(p.travelers || ''); setBudget(p.budget ? String(p.budget) : ''); setStartDate(p.startDate || ''); setEndDate(p.endDate || ''); if (!e.target.value.trim()) setUserEditedTravelers(false) }}
          placeholder="例如：北京出发三亚5天亲子游，预算1万" rows={3} className={inputCls('query') + ' resize-none'} />
        {fieldErrors.query && <p className="text-red-500 text-xs mt-1">{fieldErrors.query}</p>}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div><label className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1"><Navigation size={13} />出发地</label><input value={origin} onChange={e => setOrigin(e.target.value)} placeholder="从上海出发" className={inputCls('origin')} /></div>
        <div><label className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1"><MapPin size={13} />目的地</label><input value={destination} onChange={e => setDestination(e.target.value)} placeholder="自动识别" className={inputCls('destination')} /></div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div><label className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1"><Users size={13} />出行人数</label><input type="number" value={travelers} min={1} onChange={e => { const v = e.target.value; setTravelers(v === '' ? '' : Number(v)); setUserEditedTravelers(true) }} className={inputCls('travelers')} />{!userEditedTravelers && !travelers && !fieldErrors.travelers && <p className="text-blue-500 text-xs mt-1">💡 未识别到人数，请确认</p>}</div>
        <div><label className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1"><DollarSign size={13} />预算（元）</label><input value={budget} onChange={e => setBudget(e.target.value)} type="number" placeholder="自动识别" className={inputCls('budget')} /></div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div><label className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1"><Calendar size={13} />出发日期</label><input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className={inputCls('startDate')} /></div>
        <div><label className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1"><Calendar size={13} />返回日期</label><input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className={inputCls('endDate')} /></div>
      </div>
      <div>
        <label className="text-sm font-medium text-gray-600 mb-2 block">路线策略</label>
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          {STRATEGIES.map(s => (
            <button key={s.value} onClick={() => { prefApplied.current = true; setRouteStrategy(s.value) }}
              className={`flex-1 rounded-md py-2.5 text-xs font-medium transition-all text-center ${
                routeStrategy === s.value ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}>
              <div>{s.emoji}</div>
              <div className="mt-0.5">{s.label}</div>
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
        <div><span className="text-sm text-gray-700">🌤️ 参考天气因素</span><p className="text-xs text-gray-400 mt-0.5">{useWeather ? '根据目的地天气自动调整行程' : '不考虑天气因素'}</p></div>
        <button onClick={() => { prefApplied.current = true; setUseWeather(!useWeather) }}
          className={`relative w-11 h-6 rounded-full transition-colors flex-shrink-0 ${useWeather ? 'bg-primary-500' : 'bg-gray-300'}`}>
          <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${useWeather ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </button>
      </div>
      {Object.keys(fieldErrors).length > 0 && <div className="bg-red-50 text-red-600 rounded-xl px-4 py-2.5 text-xs font-medium">请完善信息后再生成</div>}
      <button onClick={isPlanning ? cancelPlan : handleGenerate}
        style={{width:'40%', margin:'0 auto'}}
        className={`rounded-2xl py-4 px-8 font-semibold text-base flex items-center justify-center gap-2 transition-colors shadow-sm ${
          isPlanning ? 'bg-red-500 text-white hover:bg-red-600' : 'bg-primary-600 text-white hover:bg-primary-700'
        }`}>
        {isPlanning ? <><Loader2 size={20} className="animate-spin" />取消规划</> : <><Sparkles size={20} />开始智能规划</>}
      </button>
    </div>
  )

  const hasResults = tripRoutes.length > 0 || tripData
  const route = currentTrip

  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center gap-2 mb-6">
        <Sparkles size={22} className="text-primary-600" />
        <h1 className="text-xl font-bold text-gray-800">AI 智能规划</h1>
      </div>

      <div className="flex-1 flex gap-6 min-h-0">

        {/* ── LEFT: Form ── */}
        <div className="overflow-y-auto" style={{flex: '0 0 35%'}}>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-700 mb-6">出行信息</h2>
            {formPanel}
          </div>
        </div>

        {/* ── CENTER: Progress / Results ── */}
        <div className="flex-1 min-w-0 overflow-y-auto">

          {isPlanning && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-base font-semibold text-gray-800 mb-5">规划进度</h3>
              <div className="flex items-center gap-1.5 mb-4">
                {[0,1,2,3].map(i => (
                  <div key={i} className={`flex-1 h-2 rounded-full transition-colors ${
                    i===0 ? (steps.length>0?'bg-primary-400':'bg-gray-200') :
                    i===1 ? (toolPhase!=='idle'?'bg-primary-400 animate-pulse':'bg-gray-200') :
                    i===2 ? (toolPhase==='done'?'bg-primary-400':'bg-gray-200') :
                    tripData?'bg-green-400':'bg-gray-200'
                  }`} />
                ))}
              </div>
              <div className="flex justify-between text-xs text-gray-400 mb-4"><span>分析</span><span>搜索</span><span>生成</span><span>完成</span></div>
              <div className="text-sm text-primary-600 font-medium mb-3">
                {!steps.length && '准备中...'}
                {steps.length > 0 && toolPhase === 'idle' && steps[steps.length - 1].text}
                {toolPhase==='calling'&&<><span className="text-green-500">✅ 出行需求分析完成</span><br/>并行搜索 {toolCount.total} 个数据源 ({toolCount.done}/{toolCount.total})</>}
                {toolPhase==='done'&&!tripData&&'正在生成行程方案...'}
                {tripData&&'✅ 行程方案已生成'}
              </div>
              <div className="space-y-1 max-h-72 overflow-y-auto">
                {steps.filter(s=>toolPhase==='done' ? s.type==='tool_result' : s.type!=='step').slice(-12).map((s,i)=>(
                  <div key={i} className="text-xs flex items-center gap-2 py-0.5">
                    <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                      s.type==='step'?'bg-blue-400':s.type==='tool_call'?'bg-yellow-400':'bg-green-400'
                    }`} />
                    <span className={s.type==='tool_call'?'text-yellow-600':'text-gray-400'}>{s.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {hasResults && route?.days && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-gray-800">{route.title || '行程方案'}</h2>
              {tripRoutes.length > 1 && (
                <div className="flex gap-2">
                  {tripRoutes.map((r:any,i:number)=>(
                    <button key={i} onClick={()=>{setSelectedRouteIdx(i);selectRoute(i)}}
                      className={`px-4 py-2 rounded-full text-sm font-medium ${i===selectedRouteIdx?'bg-primary-600 text-white shadow':'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}>
                      {r.route_tag||`路线 ${i+1}`}
                    </button>
                  ))}
                </div>
              )}
              {route.summary && <div className="bg-primary-50 rounded-xl p-4 text-sm text-gray-700">{route.summary}</div>}
              <TripTimeline days={route.days} />
            </div>
          )}

          {!isPlanning && !hasResults && (
            <div className="flex items-center justify-center h-full"><div className="text-center"><div className="text-5xl mb-3">🗺️</div><p className="text-gray-400 text-sm">在左侧填写出行信息后开始规划</p></div></div>
          )}

          {error && <div className="mt-4 bg-red-50 text-red-600 rounded-xl p-4 text-sm">{error}</div>}
        </div>

        {/* ── RIGHT: Detail Panel ── */}
        {hasResults && route && (
          <div className="overflow-y-auto space-y-3 pr-3" style={{flex: '0 0 25%'}}>
            {/* Weather */}
            {weatherData && (
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="text-xs font-semibold text-gray-600 mb-3">🌤️ 天气</div>
                <div className="space-y-3">
                  {weatherData.origin_weather && (
                    <div>
                      <div className="text-[12px] font-semibold text-gray-700 mb-1.5">🌤️ {weatherData.origin}（出发地）</div>
                      <div className="text-[12px] text-gray-500 leading-relaxed whitespace-pre-line">{weatherData.origin_weather}</div>
                    </div>
                  )}
                  {weatherData.dest_weather && (
                    <div className="pt-3 border-t border-gray-100">
                      <div className="text-[12px] font-semibold text-gray-700 mb-1.5">🌤️ {weatherData.dest}（目的地）</div>
                      <div className="text-[12px] text-gray-500 leading-relaxed whitespace-pre-line">{weatherData.dest_weather}</div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tips */}
            {route.tips && Array.isArray(route.tips) && (
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="text-xs font-semibold text-gray-600 mb-2">💡 出行提示</div>
                <ul className="text-[11px] text-gray-500 space-y-1.5 leading-relaxed">
                  {route.tips.map((tip: string, i: number) => <li key={i} className="flex gap-1.5"><span className="text-gray-300 flex-shrink-0">•</span><span>{tip}</span></li>)}
                </ul>
              </div>
            )}

            {/* Budget */}
            {route.budget && typeof route.budget === 'object' && (
              <BudgetPanel budget={{
                total_estimated: Object.values(route.budget).reduce((a: number, b: any) => a + (Number(b) || 0), 0),
                total_actual: 0,
                categories: Object.entries(route.budget).map(([cat, val]) => ({ category: cat, estimated: val as number, actual: 0, currency: 'CNY' })),
              }} />
            )}

            {/* Bottom actions — 右下角横向 */}
            <div className="flex gap-2">
              <button onClick={() => navigate('/trips')}
                className="flex-1 border border-primary-300 text-primary-600 rounded-lg py-2.5 text-[13px] font-medium hover:bg-primary-50 transition-colors text-center">
                我的行程
              </button>
              <button onClick={() => usePlanStore.setState({ tripData: null, tripRoutes: [], steps: [] })}
                className="flex-1 border border-gray-300 text-gray-600 rounded-lg py-2.5 text-[13px] font-medium hover:bg-gray-100 transition-colors text-center">
                重新规划
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
