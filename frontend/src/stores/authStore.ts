import { create } from 'zustand'

interface User {
  id: string
  phone: string
  nickname: string
  avatar_url: string | null
}

// 平台检测 + 独立存储 key
const IS_PC = typeof window !== 'undefined' && window.location.pathname.startsWith('/pc.html')
const TOKEN_KEY = IS_PC ? 'sj_pc_token' : 'sj_token'

function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
function setToken(v: string) {
  try { localStorage.setItem(TOKEN_KEY, v) } catch {}
}
function removeToken() {
  try { localStorage.removeItem(TOKEN_KEY) } catch {}
}

interface AuthStore {
  user: User | null
  token: string | null
  _logoutTriggered?: boolean
  showLogin: boolean
  pendingPath: string | null
  login: (phone: string, code: string) => Promise<void>
  restore: () => Promise<void>
  logout: () => void
  loadFromStorage: () => void
  openLogin: (path?: string | null) => void
  closeLogin: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: getToken(),
  showLogin: false,
  pendingPath: null,

  login: async (phone, code) => {
    const { login } = await import('../api')
    const res = await login(phone, code)
    const { access_token, user } = res.data.data
    setToken(access_token)
    set({ token: access_token, user })
  },

  restore: async () => {
    const token = getToken()
    if (!token) return
    try {
      const { getMe } = await import('../api')
      const res = await getMe()
      set({ token, user: res.data.data })
    } catch {
      removeToken()
      set({ token: null, user: null })
    }
  },

  logout: () => {
    removeToken()
    set({ token: null, user: null, showLogin: false, pendingPath: null })
    const base = IS_PC ? '/pc.html' : '/'
    window.location.href = base
  },

  loadFromStorage: () => {
    const token = getToken()
    if (token) set({ token })
  },

  openLogin: (path) => set({ showLogin: true, pendingPath: path ?? null }),
  closeLogin: () => set({ showLogin: false, pendingPath: null }),
}))
