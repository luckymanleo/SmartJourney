import { create } from 'zustand'

interface User {
  id: string
  phone: string
  nickname: string
  avatar_url: string | null
}

interface AuthStore {
  user: User | null
  token: string | null
  _logoutTriggered?: boolean
  login: (phone: string, code: string) => Promise<void>
  restore: () => Promise<void>
  logout: () => void
  loadFromStorage: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: localStorage.getItem('sj_token'),

  login: async (phone, code) => {
    const { login } = await import('../api')
    const res = await login(phone, code)
    const { access_token, user } = res.data.data
    localStorage.setItem('sj_token', access_token)
    set({ token: access_token, user })
  },

  restore: async () => {
    const token = localStorage.getItem('sj_token')
    if (!token) return
    try {
      const { getMe } = await import('../api')
      const res = await getMe()
      set({ token, user: res.data.data })
    } catch {
      // token 过期，清除
      localStorage.removeItem('sj_token')
      set({ token: null, user: null })
    }
  },

  logout: () => {
    localStorage.removeItem('sj_token')
    set({ token: null, user: null })
    window.location.href = '/'
  },

  loadFromStorage: () => {
    const token = localStorage.getItem('sj_token')
    if (token) set({ token })
  },
}))
