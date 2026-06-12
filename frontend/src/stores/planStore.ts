import { create } from 'zustand'

interface PlanStep {
  type: 'step' | 'tool_call' | 'tool_result'
  text: string
  data?: any
  elapsed?: number
}

interface WeatherData {
  origin: string
  dest: string
  origin_weather: string
  dest_weather: string
}

interface PoiCoord {
  title: string; day: number; idx: number; lng: number; lat: number
}

interface PlanStore {
  isPlanning: boolean
  steps: PlanStep[]
  toolPhase: 'idle' | 'calling' | 'done'
  toolCount: { total: number; done: number }
  tripData: any
  tripRoutes: any[]
  routeCount: number
  error: string | null
  weatherData: WeatherData | null
  llmStream: string
  poiCoords: PoiCoord[]
  planElapsed: number
  totalElapsed: number
  startPlan: (body: any) => void
  cancelPlan: () => void
  selectRoute: (index: number) => void
}

export const usePlanStore = create<PlanStore>((set, get) => {
  let _abort: (() => void) | null = null
  let _stopTimerFn: (() => void) | null = null  // 互斥：确保只有一个定时器

  return {
    isPlanning: false,
    steps: [],
    toolPhase: 'idle',
    toolCount: { total: 0, done: 0 },
    tripData: null,
    tripRoutes: [],
    routeCount: 1,
    error: null,
    weatherData: null,
    llmStream: '',
    poiCoords: [],
    planElapsed: 0,
    totalElapsed: 0,

    startPlan: async (body) => {
      // 先取消上一次的请求和定时器
      if (_abort) {
        _abort()
        _abort = null
      }
      if (_stopTimerFn) {
        _stopTimerFn()
        _stopTimerFn = null
      }
      set({ isPlanning: true, steps: [], tripData: null, tripRoutes: [], error: null, weatherData: null, llmStream: '', poiCoords: [], toolPhase: 'idle', toolCount: { total: 0, done: 0 }, planElapsed: 0, totalElapsed: 0 })

      // 计时器 — 从 0 开始
      const _planStart = Date.now()
      const _timer = setInterval(() => {
        set({ planElapsed: Math.round((Date.now() - _planStart) / 1000) })
      }, 1000)

      const _stopTimer = () => {
        clearInterval(_timer)
        const final = Math.round((Date.now() - _planStart) / 1000)
        set({ planElapsed: final, totalElapsed: final })
        _stopTimerFn = null
      }
      _stopTimerFn = _stopTimer
      const { streamPlan } = await import('../api')

      _abort = streamPlan(
        body,
        (event, data) => {
          if (event === 'step') {
            set((s) => ({ steps: [...s.steps, { type: 'step', text: data.text }] }))
          } else if (event === 'tool_call') {
            set((s) => ({
              toolPhase: 'calling',
              toolCount: { total: s.toolCount.total + 1, done: s.toolCount.done },
              steps: [...s.steps, { type: 'tool_call' as const, text: '🔍 正在搜索...', data }],
            }))
          } else if (event === 'tool_result') {
            set((s) => {
              const done = s.toolCount.done + 1
              const total = s.toolCount.total
              return {
                toolCount: { total, done },
                toolPhase: done >= total ? 'done' : 'calling',
                steps: [...s.steps, { type: 'tool_result', text: `✅ ${data.summary}`, data, elapsed: data.elapsed }],
              }
            })
          } else if (event === 'weather') {
            set({ weatherData: data })
          } else if (event === 'trip_data') {
            set((s) => ({
              tripRoutes: [...s.tripRoutes, data],
              tripData: s.tripRoutes.length === 0 ? data : s.tripData,
            }))
          } else if (event === 'done') {
            _stopTimer()
            set((s) => ({
              isPlanning: false,
              routeCount: data.route_count || s.tripRoutes.length || 1,
            }))
            _abort = null
          } else if (event === 'chunk') {
            if (data.text) {
              set((s) => ({ llmStream: s.llmStream + data.text }))
            }
          } else if (event === 'poi_coord') {
            set((s) => ({ poiCoords: [...s.poiCoords, data] }))
          } else if (event === 'error') {
            _stopTimer()
            set((s) => ({ error: data.message || '规划异常', isPlanning: false }))
            _abort = null
          }
        },
        (err) => {
          _stopTimer()
          const msg = typeof err === 'string' ? err : (err as any)?.message || '规划失败'
          set({ isPlanning: false, error: msg })
          _abort = null
        }
      )
    },

    cancelPlan: () => {
      if (_abort) {
        _abort()
        _abort = null
      }
      if (_stopTimerFn) {
        _stopTimerFn()
        _stopTimerFn = null
      } else {
        set({ isPlanning: false, planElapsed: 0, totalElapsed: 0 })
      }
    },

    selectRoute: (index) => {
      set((s) => ({ tripData: s.tripRoutes[index] || s.tripData }))
    },
  }
})
