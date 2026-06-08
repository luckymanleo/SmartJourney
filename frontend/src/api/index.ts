import api from './client'

// 平台检测
const P = typeof window !== 'undefined' && window.location.pathname.startsWith('/pc.html') ? 'pc' : 'mobile'

// Auth
export const sendCode = (phone: string) => api.post('/auth/send-code', { phone, platform: P })
export const login = (phone: string, code: string) => api.post('/auth/login', { phone, code, platform: P })
export const getMe = () => api.get('/auth/me')
export const updateProfile = (data: { nickname?: string; avatar_url?: string }) => api.put('/auth/profile', data)

// Search
export const searchFlights = (params: Record<string, any>) => api.get('/search/flights', { params })
export const searchTrains = (params: Record<string, any>) => api.get('/search/trains', { params })
export const searchHotels = (params: Record<string, any>) => api.get('/search/hotels', { params })
export const searchPOIs = (params: Record<string, any>) => api.get('/search/pois', { params })
export const searchFoods = (params: Record<string, any>) => api.get('/search/foods', { params })
export const searchTransport = (params: Record<string, any>) => api.get('/search/transport', { params })

// Trips
export const createTrip = (data: any) => api.post('/trips', data)
export const getTrips = (params?: any) => api.get('/trips', { params })
export const getTrip = (id: string) => api.get(`/trips/${id}`)
export const updateTrip = (id: string, data: any) => api.put(`/trips/${id}`, data)
export const deleteTrip = (id: string) => api.delete(`/trips/${id}`)
export const addTripItem = (tripId: string, data: any) => api.post(`/trips/${tripId}/items`, data)
export const removeTripItem = (tripId: string, itemId: string) => api.delete(`/trips/${tripId}/items/${itemId}`)
export const getBudget = (tripId: string) => api.get(`/trips/${tripId}/budget`)

// Info
export const getWeather = (city: string) => api.get('/info/weather', { params: { city } })
export const getDestinationInfo = (city: string) => api.get(`/info/destination/${city}`)
export const getPopularDestinations = (limit?: number) => api.get('/info/popular', { params: { limit: limit || 6 } } )
export const getPreferences = () => api.get('/user/preferences')
export const savePreferences = (data: any) => api.put('/user/preferences', data)

// Plan (SSE) — 返回 abort 函数用于取消
export function streamPlan(
  body: any,
  onEvent: (event: string, data: any) => void,
  onError: (err: string) => void,
): () => void {
  const token = localStorage.getItem('sj_token')
  if (!token) {
    onError('请先登录')
    return () => {}
  }

  const controller = new AbortController()

  fetch('/api/v1/plan/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  }).then(async (response) => {
    if (response.status === 401) {
      onError('登录已过期，请重新登录')
      localStorage.removeItem('sj_token')
      const base = window.location.pathname.startsWith('/pc.html') ? '/pc.html' : '/'
      window.location.href = base
      return
    }
    if (!response.ok) {
      const text = await response.text().catch(() => '')
      onError(`请求失败 (${response.status}): ${text.slice(0, 100)}`)
      return
    }
    const reader = response.body?.getReader()
    if (!reader) return
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      // 中断检测
      if (controller.signal.aborted) {
        reader.cancel()
        return
      }
      try {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onEvent(currentEvent, data)
            } catch (e) {
              console.warn('SSE parse error:', currentEvent, line.slice(6, 100))
            }
          }
        }
      } catch (e: any) {
        if (e.name === 'AbortError' || controller.signal.aborted) return
        throw e
      }
    }
  }).catch((e) => {
    if (e.name === 'AbortError') return // 正常取消，不报错
    onError(typeof e === 'string' ? e : e?.message || '规划失败')
  })

  return () => controller.abort()
}
