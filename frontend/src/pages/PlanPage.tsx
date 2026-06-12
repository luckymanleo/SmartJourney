import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Sparkles, Loader2, CheckCircle2, MapPin, Users, Calendar, DollarSign, Navigation, ArrowRight, List } from 'lucide-react'
import { usePlanStore } from '../stores/planStore'
import { parseTripQuery } from '../utils/parseQuery'
import TripTimeline from '../components/TripTimeline'
import LiveMapPreview from '../components/LiveMapPreview'
import LlmStreamBox from '../components/LlmStreamBox'
import BudgetPanel from '../components/BudgetPanel'

export default function PlanPage() {
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
  const [formError, setFormError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [useWeather, setUseWeather] = useState(true)  // 默认值，preferences 加载后覆盖
  const [routeStrategy, setRouteStrategy] = useState(-1)
  const [userEditedTravelers, setUserEditedTravelers] = useState(false)  // 用户手动改过人数
  const [specialNotes, setSpecialNotes] = useState('')

  // 自动解析搜索词 → 填充所有字段
  useEffect(() => {
    if (initialQuery) {
      // 新查询进入时，清除上一次的规划结果，回到表单页面
      usePlanStore.setState({ tripData: null, tripRoutes: [], steps: [] })
      setQuery(initialQuery)
      const parsed = parseTripQuery(initialQuery)
      setOrigin(parsed.origin)
      if (parsed.destination) setDestination(parsed.destination)
      if (parsed.travelers) setTravelers(parsed.travelers)
      if (parsed.budget) setBudget(String(parsed.budget))
      if (parsed.startDate) setStartDate(parsed.startDate)
      if (parsed.endDate) setEndDate(parsed.endDate)
    }
  }, [initialQuery])

  // 加载用户保存的偏好（含天气开关、路线策略默认值）
  const [preferences, setPreferences] = useState<any>(null)
  useEffect(() => {
    import('../api').then(({ getPreferences }) => {
      getPreferences().then(r => {
        const data = r.data?.data
        setPreferences(data)
        // 用保存的偏好覆盖天气开关和路线策略默认值
        if (data) {
          if (typeof data.use_weather === 'boolean') setUseWeather(data.use_weather)
          if (typeof data.route_strategy === 'number') setRouteStrategy(data.route_strategy)
          if (typeof data.special_notes === 'string') setSpecialNotes(data.special_notes)
        }
      }).catch(() => {})
    })
  }, [])

  const isPlanning = usePlanStore(s => s.isPlanning)
  const steps = usePlanStore(s => s.steps)
  const tripData = usePlanStore(s => s.tripData)
  const tripRoutes = usePlanStore(s => s.tripRoutes)
  const routeCount = usePlanStore(s => s.routeCount)
  const error = usePlanStore(s => s.error)
  const weatherData = usePlanStore(s => s.weatherData)
  const toolPhase = usePlanStore(s => s.toolPhase)
  const toolCount = usePlanStore(s => s.toolCount)
  const startPlan = usePlanStore(s => s.startPlan)
  const cancelPlan = usePlanStore(s => s.cancelPlan)
  const selectRoute = usePlanStore(s => s.selectRoute)
  const planElapsed = usePlanStore(s => s.planElapsed)
  const totalElapsed = usePlanStore(s => s.totalElapsed)

  // 多路线选择
  const [selectedRouteIdx, setSelectedRouteIdx] = useState(0)
  const currentTrip = tripRoutes[selectedRouteIdx] || tripData || tripRoutes[0]

  const handleGenerate = () => {
    const errors: Record<string, string> = {}
    if (!query.trim()) errors.query = '请描述出行需求'
    if (!origin.trim()) errors.origin = '请填写出发地'
    if (!destination.trim()) errors.destination = '请填写目的地'
    if (!startDate) errors.startDate = '请选择出发日期'
    if (!endDate) errors.endDate = '请选择返回日期'
    if (!budget || Number(budget) <= 0) errors.budget = '请填写预算'
    if (!travelers || travelers < 1) errors.travelers = '请填写出行人数'
    
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return
    
    startPlan({
      query: query.trim(),
      origin: origin || undefined,
      destination: destination || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      traveler_count: travelers || 1,
      budget_total: budget ? Number(budget) : undefined,
      preferences: preferences || undefined,
      save_as_trip: true,
      use_weather: useWeather,
      route_count: routeStrategy >= 0 ? 1 : 1,
      route_strategy: routeStrategy,
      special_notes: specialNotes.trim() || undefined,
    })
  }

  // Show results after planning
  if (tripRoutes.length > 0 || tripData) {
    const route = currentTrip
    if (!route || !route.days) {
      return (
        <div className="p-4">
          <div className="bg-yellow-50 text-yellow-800 rounded-xl p-4 text-sm">
            行程数据不完整，请重新规划
          </div>
          <button
            onClick={() => usePlanStore.setState({ tripData: null, tripRoutes: [], steps: [] })}
            className="w-full mt-4 border border-primary-300 text-primary-600 rounded-xl py-3 font-medium"
          >
            重新规划
          </button>
        </div>
      )
    }
    const hasTripId = route?.trip_id
    const isMultiRoute = tripRoutes.length > 1

    return (
      <div className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <CheckCircle2 size={20} className="text-green-500" />
          <h1 className="text-xl font-bold text-gray-800">{route?.title || '行程方案'}</h1>
          {totalElapsed > 0 && (
            <span className="text-xs text-gray-400 ml-1">总耗时 {totalElapsed}s</span>
          )}
          {hasTripId && (
            <span className="ml-auto text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
              已保存
            </span>
          )}
        </div>

        {/* 多路线选择器 */}
        {isMultiRoute && (
          <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
            {tripRoutes.map((r: any, i: number) => (
              <button
                key={i}
                onClick={() => { setSelectedRouteIdx(i); selectRoute(i) }}
                className={`flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  i === selectedRouteIdx
                    ? 'bg-primary-600 text-white shadow'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {r.route_tag || `路线 ${i + 1}`}
              </button>
            ))}
          </div>
        )}

        {/* 导航入口 */}
        {hasTripId && (
          <div className="flex justify-end mb-4">
            <button
              onClick={() => navigate('/trips')}
              className="flex items-center gap-1.5 px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600"
            >
              <List size={16} />
              我的行程
            </button>
          </div>
        )}

        {route?.summary && (
          <div className="bg-primary-50 rounded-xl p-4 mb-4">
            <p className="text-sm text-gray-700">{route.summary}</p>
          </div>
        )}

        {/* Weather */}
        {weatherData && (
          <div className="grid grid-cols-2 gap-3 mb-4">
            {weatherData.origin_weather && (
              <div className="bg-blue-50 rounded-xl p-3">
                <div className="text-xs font-semibold text-blue-700 mb-1">
                  🌤️ {weatherData.origin}（出发地）
                </div>
                <div className="text-[11px] text-blue-600 space-y-0.5">
                  {weatherData.origin_weather.split('\n').map((line: string, i: number) => (
                    <div key={i}>{line.replace(/^- /, '')}</div>
                  ))}
                </div>
              </div>
            )}
            {weatherData.dest_weather && (
              <div className="bg-blue-50 rounded-xl p-3">
                <div className="text-xs font-semibold text-blue-700 mb-1">
                  🌤️ {weatherData.dest}（目的地）
                </div>
                <div className="text-[11px] text-blue-600 space-y-0.5">
                  {weatherData.dest_weather.split('\n').map((line: string, i: number) => (
                    <div key={i}>{line.replace(/^- /, '')}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {route?.tips && Array.isArray(route.tips) && (
          <div className="bg-yellow-50 rounded-xl p-4 mb-4">
            <h3 className="text-sm font-semibold text-yellow-800 mb-1">出行提示</h3>
            <ul className="text-xs text-yellow-700 space-y-1">
              {route.tips.map((tip: string, i: number) => (
                <li key={i}>• {tip}</li>
              ))}
            </ul>
          </div>
        )}

        {route?.days && <TripTimeline days={route.days} travelerCount={travelers || 1} />}

        {route?.budget && typeof route.budget === 'object' && (
          <div className="mt-6">
            <BudgetPanel
              budget={{
                total_estimated: Object.values(route.budget).reduce((a: number, b: any) => a + (Number(b) || 0), 0),
                total_actual: 0,
                categories: Object.entries(route.budget).map(([cat, val]) => ({
                  category: cat,
                  estimated: val as number,
                  actual: 0,
                  currency: 'CNY',
                })),
              }}
            />
          </div>
        )}

        <div className="flex gap-2 mt-6">
          <button
            onClick={() => usePlanStore.setState({ tripData: null, tripRoutes: [], steps: [] })}
            className="flex-1 border border-primary-300 text-primary-600 rounded-xl py-3 font-medium"
          >
            重新规划
          </button>
          {hasTripId && (
            <button
              onClick={() => navigate(`/trips/${route.trip_id}`)}
              className="flex-1 bg-primary-600 text-white rounded-xl py-3 font-medium flex items-center justify-center gap-1.5"
            >
              <ArrowRight size={16} />
              查看详情
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles size={22} className="text-primary-600" />
        <h1 className="text-xl font-bold text-gray-800">AI 智能规划</h1>
      </div>

      {/* Input Form */}
      <div className="space-y-3">
        {/* 核心需求 */}
        <div>
          <label className="text-xs text-gray-500 mb-1 block">想去哪里、有什么要求？*</label>
          <textarea
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              // 编辑时重新解析（删除输入时清空所有字段）
              const parsed = parseTripQuery(e.target.value)
              setOrigin(parsed.origin || '')
              setDestination(parsed.destination || '')
              setTravelers(parsed.travelers || '')
              setBudget(parsed.budget ? String(parsed.budget) : '')
              setStartDate(parsed.startDate || '')
              setEndDate(parsed.endDate || '')
              if (!e.target.value.trim()) setUserEditedTravelers(false)
            }}
            placeholder="例如：北京出发三亚5天亲子游，预算1万，想去海边和热带雨林"
            rows={3}
            className={`w-full border rounded-xl px-4 py-3 text-sm outline-none focus:border-primary-400 resize-none ${fieldErrors.query ? 'border-red-300 bg-red-50' : 'border-gray-200'}`}
          />
          {fieldErrors.query && <div className="text-red-500 text-[11px] mt-1">{fieldErrors.query}</div>}
        </div>

        {/* 解析结果展示 */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-500 mb-1 flex items-center gap-1">
              <Navigation size={12} /> 出发地
            </label>
            <input
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              placeholder="例如：从上海出发"
              className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white outline-none focus:border-primary-400"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 flex items-center gap-1">
              <MapPin size={12} /> 目的地
            </label>
            <input
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="自动识别"
              className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white outline-none focus:border-primary-400"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-500 mb-1 flex items-center gap-1">
              <Users size={12} /> 出行人数
            </label>
            <input
              type="number"
              value={travelers}
              onChange={(e) => { const v = e.target.value; setTravelers(v === '' ? '' : Number(v)); setUserEditedTravelers(true) }}
              min={1}
              className={`w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white outline-none focus:border-primary-400 ${fieldErrors.travelers ? 'border-red-300 bg-red-50' : ''}`}
            />
            {!userEditedTravelers && !travelers && !fieldErrors.travelers && (
              <div className="text-blue-500 text-[10px] mt-0.5">💡 未识别到人数，请确认</div>
            )}
            {fieldErrors.travelers && <div className="text-red-500 text-[11px] mt-1">{fieldErrors.travelers}</div>}
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 flex items-center gap-1">
              <DollarSign size={12} /> 预算（元）
            </label>
            <input
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              type="number"
              placeholder="自动识别"
              className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white outline-none focus:border-primary-400"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-500 mb-1 flex items-center gap-1">
              <Calendar size={12} /> 出发日期
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white outline-none focus:border-primary-400"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 flex items-center gap-1">
              <Calendar size={12} /> 返回日期
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white outline-none focus:border-primary-400"
            />
          </div>
        </div>

        {/* Special Notes */}
        <div>
          <label className="text-xs text-gray-500 mb-1 flex items-center gap-1">
            特殊说明 <span className="text-gray-300 font-normal">（选填）</span>
          </label>
          <input
            value={specialNotes}
            onChange={(e) => setSpecialNotes(e.target.value)}
            placeholder="例如：花粉过敏、素食、行动不便"
            className="w-full border rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white outline-none focus:border-primary-400"
          />
        </div>

        {/* 路线策略选择 */}
        <div className="bg-gray-50 rounded-xl px-4 py-3">
          <span className="text-sm text-gray-700">🎯 路线策略</span>
          <div className="flex gap-2 mt-2">
            {[
              { label: '默认', value: -1, desc: '智能平衡' },
              { label: '💰 经济实惠', value: 0, desc: '低价优先' },
              { label: '🏨 舒适优先', value: 1, desc: '品质体验' },
              { label: '⚡ 最快到达', value: 2, desc: '效率至上' },
            ].map((s) => (
              <button
                key={s.value}
                onClick={() => setRouteStrategy(s.value)}
                className={`flex-1 rounded-lg px-2 py-2 text-xs font-medium transition-colors ${
                  routeStrategy === s.value
                    ? 'bg-primary-600 text-white shadow'
                    : 'bg-white text-gray-600 border border-gray-200 hover:border-primary-300'
                }`}
              >
                <div>{s.label}</div>
                <div className="text-[10px] opacity-70 mt-0.5">{s.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* 天气因素开关 */}
        <div className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
          <div>
            <span className="text-sm text-gray-700">🌤️ 参考天气因素</span>
            <p className="text-[10px] text-gray-400 mt-0.5">
              {useWeather ? '根据目的地天气自动调整行程（晴天户外、雨天室内等）' : '不考虑天气，生成通用行程方案'}
            </p>
          </div>
          <button
            onClick={() => setUseWeather(!useWeather)}
            className={`relative w-11 h-6 rounded-full transition-colors flex-shrink-0 ${
              useWeather ? 'bg-primary-500' : 'bg-gray-300'
            }`}
          >
            <div
              className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                useWeather ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        {Object.keys(fieldErrors).length > 0 && (
          <div className="bg-red-50 text-red-600 rounded-xl px-4 py-3 text-sm">
            请完善以下信息后再生成行程
          </div>
        )}

        <button
          onClick={isPlanning ? cancelPlan : handleGenerate}
          className={`w-full rounded-xl py-3 font-medium flex items-center justify-center gap-2 transition-colors ${
            isPlanning
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-gradient-to-r from-primary-500 to-primary-700 text-white'
          }`}
        >
          {isPlanning ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              取消规划
            </>
          ) : (
            <>
              <Sparkles size={18} />
              开始智能规划
            </>
          )}
        </button>
      </div>

      {/* Planning Progress */}
      {isPlanning && (
        <div className="mt-6 bg-white rounded-xl border border-gray-200 p-4">
          <div className="text-sm font-semibold text-gray-800 mb-3">
            规划进度{planElapsed > 0 && <span className="text-gray-400 font-normal ml-1">· {planElapsed}s</span>}
          </div>

          {/* 阶段指示器 — 顺序点亮 */}
          <div className="flex items-center gap-1.5 mb-2">
            <div className={`flex-1 h-2 rounded-full transition-colors ${toolPhase !== 'idle' ? 'bg-blue-500' : steps.length > 0 ? 'bg-blue-400 animate-pulse' : 'bg-gray-200'}`} />
            <div className={`flex-1 h-2 rounded-full transition-colors ${toolPhase === 'calling' ? 'bg-blue-400 animate-pulse' : toolPhase === 'done' ? 'bg-blue-500' : 'bg-gray-200'}`} />
            <div className={`flex-1 h-2 rounded-full transition-colors ${toolPhase === 'done' && !tripData ? 'bg-blue-400 animate-pulse' : tripData ? 'bg-blue-500' : 'bg-gray-200'}`} />
            <div className={`flex-1 h-2 rounded-full transition-colors ${tripData ? 'bg-green-500' : 'bg-gray-200'}`} />
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 mb-3">
            <span>分析</span><span>搜索</span><span>生成</span><span>完成</span>
          </div>

          {/* 当前状态 — 搜索阶段在上 */}
          {toolPhase === 'calling' && (
            <div className="text-sm text-primary-600 font-medium mb-2">
              <span className="text-green-500">✅ 出行需求分析完成</span><br/>并行搜索 {toolCount.total} 个数据源 ({toolCount.done}/{toolCount.total})
            </div>
          )}

          {/* 共享滚动区 — 搜索详情 */}
          {!tripData && toolPhase !== 'idle' && (
            <div className="max-h-64 overflow-y-auto mb-3">
              {toolPhase==='done' && !tripData && (
                <div className="text-[11px] text-gray-400 mb-2">
                  ✅ 搜索已完成（{steps.filter(s => s.type === 'tool_result').length} 个数据源）
                </div>
              )}
              <div className="space-y-0.5">
                {(toolPhase==='done'
                  ? steps.filter(s => s.type === 'tool_result')
                  : steps.filter(s => s.type !== 'step')
                ).map((s, i) => (
                <div key={i} className="text-[11px] flex items-center gap-1.5 py-0.5">
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${s.type==='tool_call'?'bg-yellow-400':'bg-green-400'}`} />
                  <span className={s.type==='tool_call'?'text-yellow-600':'text-gray-400'}>{s.text}</span>
                  {s.elapsed != null && <span className="text-gray-300 ml-auto flex-shrink-0">{s.elapsed}s</span>}
                </div>
                ))}
              </div>
            </div>
          )}

          {/* 当前状态 — 生成/完成阶段在下 */}
          <div className="text-sm text-primary-600 font-medium mb-2">
            {!steps.length && toolPhase === 'idle' && '准备中...'}
            {steps.length > 0 && toolPhase === 'idle' && steps[steps.length - 1].text}
            {toolPhase==='done'&&!tripData&&'✅正在生成行程方案...'}
            {tripData&&`✅行程方案规划完成 · 总耗时 ${totalElapsed}s`}
          </div>

          {/* LLM 打字机 — 在状态文字下方 */}
          {toolPhase==='done' && !tripData && (
            <LlmStreamBox />
          )}
        </div>
      )}

      <LiveMapPreview />

      {error && (
        <div className="mt-4 bg-red-50 text-red-600 rounded-xl p-4 text-sm">
          {error}
        </div>
      )}
    </div>
  )
}
