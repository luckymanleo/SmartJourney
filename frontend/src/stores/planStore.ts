import { create } from 'zustand'

interface PlanStep {
  type: 'step' | 'tool_call' | 'tool_result'
  text: string
  data?: any
}

interface WeatherData {
  origin: string
  dest: string
  origin_weather: string
  dest_weather: string
}

interface PlanStore {
  isPlanning: boolean
  steps: PlanStep[]
  toolPhase: 'idle' | 'calling' | 'done'
  toolCount: { total: number; done: number }
  tripData: any
  tripRoutes: any[]          // 多路线支持
  routeCount: number
  error: string | null
  weatherData: WeatherData | null
  startPlan: (body: any) => void
  cancelPlan: () => void
  selectRoute: (index: number) => void
}

export const usePlanStore = create<PlanStore>((set) => ({
  isPlanning: false,
  steps: [],
  toolPhase: 'idle',
  toolCount: { total: 0, done: 0 },
  tripData: null,
  tripRoutes: [],
  routeCount: 1,
  error: null,
  weatherData: null,

  startPlan: async (body) => {
    set({ isPlanning: true, steps: [], tripData: null, tripRoutes: [], error: null, weatherData: null, toolPhase: 'idle', toolCount: { total: 0, done: 0 } })
    const { streamPlan } = await import('../api')

    streamPlan(
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
              steps: [...s.steps, { type: 'tool_result', text: `✅ ${data.summary}`, data }],
            }
          })
        } else if (event === 'weather') {
          set({ weatherData: data })
        } else if (event === 'trip_data') {
          set((s) => ({
            tripRoutes: [...s.tripRoutes, data],
            tripData: s.tripRoutes.length === 0 ? data : s.tripData,  // 第一条设为默认
          }))
        } else if (event === 'done') {
          set((s) => ({
            isPlanning: false,
            routeCount: data.route_count || s.tripRoutes.length || 1,
          }))
        } else if (event === 'chunk') {
          // LLM 文本输出（非结构化）
          if (data.text) {
            set((s) => ({ steps: [...s.steps, { type: 'step', text: data.text.slice(0, 300) }] }))
          }
        } else if (event === 'error') {
          set((s) => ({ error: data.message || '规划异常', isPlanning: false }))
        }
      },
      (err) => {
        const msg = typeof err === 'string' ? err : (err as any)?.message || '规划失败'
        set({ isPlanning: false, error: msg })
      }
    )
  },

  cancelPlan: () => {
    set({ isPlanning: false })
  },

  selectRoute: (index) => {
    set((s) => ({ tripData: s.tripRoutes[index] || s.tripData }))
  },
}))
