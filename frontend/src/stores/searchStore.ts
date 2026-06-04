import { create } from 'zustand'

export interface SearchHistoryItem {
  type: string
  from?: string
  to?: string
  city?: string
  keyword?: string
  date?: string
  time: number
}

const HISTORY_KEY = 'sj_search_history'
const MAX_HISTORY = 20

function loadHistory(): SearchHistoryItem[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory(items: SearchHistoryItem[]) {
  const data = items.slice(0, MAX_HISTORY)
  // 异步写入，不阻塞主流程渲染
  if (typeof requestIdleCallback !== 'undefined') {
    requestIdleCallback(() => localStorage.setItem(HISTORY_KEY, JSON.stringify(data)))
  } else {
    setTimeout(() => localStorage.setItem(HISTORY_KEY, JSON.stringify(data)), 0)
  }
}

interface SearchStore {
  query: string
  results: any[]
  loading: boolean
  error: string | null
  history: SearchHistoryItem[]
  search: (type: string, params: Record<string, any>) => Promise<void>
  setQuery: (q: string) => void
  addHistory: (item: SearchHistoryItem) => void
  removeHistory: (index: number) => void
  clearHistory: () => void
}

export const useSearchStore = create<SearchStore>((set, get) => ({
  query: '',
  results: [],
  loading: false,
  error: null,
  history: loadHistory(),

  search: async (type, params) => {
    set({ loading: true, results: [], error: null })
    const api = await import('../api')
    let res
    try {
      switch (type) {
        case 'flights': res = await api.searchFlights(params); break
        case 'trains': res = await api.searchTrains(params); break
        case 'hotels': res = await api.searchHotels(params); break
        case 'pois': res = await api.searchPOIs(params); break
        case 'foods': res = await api.searchFoods(params); break
        case 'transport': res = await api.searchTransport(params); break
        default: return
      }
      set({ results: res.data.data.items || [], loading: false })

      // 保存到搜索历史
      const item: SearchHistoryItem = {
        type,
        from: params.from,
        to: params.to,
        city: params.city,
        keyword: params.keyword,
        date: params.date,
        time: Date.now(),
      }
      const current = get().history
      const updated = [item, ...current.filter(h =>
        !(h.type === item.type && h.from === item.from && h.to === item.to &&
          h.city === item.city && h.keyword === item.keyword && h.date === item.date)
      )]
      set({ history: updated })
      saveHistory(updated)
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || '搜索失败'
      const friendlyMsg = e.code === 'ECONNABORTED' || msg.includes('timeout')
        ? '搜索超时，请检查网络后重试'
        : msg.includes('503') ? '搜索服务暂不可用，正在重连...'
        : msg
      set({ error: friendlyMsg, loading: false })
    }
  },

  setQuery: (q) => set({ query: q }),

  addHistory: (item) => {
    const current = get().history
    const updated = [item, ...current.filter(h =>
      !(h.type === item.type && h.from === item.from && h.to === item.to &&
        h.city === item.city && h.keyword === item.keyword && h.date === item.date)
    )]
    set({ history: updated })
    saveHistory(updated)
  },

  removeHistory: (index) => {
    const updated = get().history.filter((_, i) => i !== index)
    set({ history: updated })
    saveHistory(updated)
  },

  clearHistory: () => {
    set({ history: [] })
    saveHistory([])
  },
}))
