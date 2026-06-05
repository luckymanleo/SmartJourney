import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { Home, MapPin, ClipboardList, Settings, ChevronDown, ChevronRight, Plus, LogOut, Loader2 } from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '../stores/authStore'
import { sendCode } from '../api'

const searchChildren = [
  { to: '/search/flights',   icon: '✈️', label: '机票' },
  { to: '/search/trains',    icon: '🚄', label: '火车票' },
  { to: '/search/hotels',    icon: '🏨', label: '酒店' },
  { to: '/search/pois',      icon: '🎫', label: '景点' },
  { to: '/search/foods',     icon: '🍜', label: '美食' },
  { to: '/search/transport', icon: '🚗', label: '同城交通' },
]

const tripChildren = [
  { to: '/plan',  icon: Plus,           label: 'AI智能规划' },
  { to: '/trips', icon: ClipboardList,  label: '我的行程' },
]

function loadState(key: string, fallback: boolean): boolean {
  try { const v = localStorage.getItem(`sj_nav_${key}`); return v !== null ? v === '1' : fallback } catch { return fallback }
}
function saveState(key: string, v: boolean) {
  try { localStorage.setItem(`sj_nav_${key}`, v ? '1' : '0') } catch {}
}

export default function LayoutPC() {
  const { user, token, logout, showLogin, openLogin, closeLogin, pendingPath } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()

  const isSearchRoute = location.pathname.startsWith('/search')
  const isTripRoute   = location.pathname === '/plan' || location.pathname === '/trips' || location.pathname.startsWith('/trips/')

  const [searchOpen, setSearchOpen] = useState(() => loadState('search', isSearchRoute))
  const [tripOpen, setTripOpen]     = useState(() => loadState('trip', true))

  useEffect(() => { if (isSearchRoute) setSearchOpen(true) }, [isSearchRoute])
  useEffect(() => { if (isTripRoute)   setTripOpen(true)   }, [isTripRoute])

  // ---- 登录弹窗 ----
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState<'phone' | 'code'>('phone')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [countdown, setCountdown] = useState(0)

  useEffect(() => {
    if (countdown <= 0) return
    const timer = setInterval(() => setCountdown(c => (c <= 1 ? 0 : c - 1)), 1000)
    return () => clearInterval(timer)
  }, [countdown > 0])
  const startCountdown = useCallback(() => setCountdown(60), [])
  const clearCountdown = useCallback(() => setCountdown(0), [])

  const closeLoginDialog = () => { closeLogin(); setError(''); setStep('phone'); clearCountdown() }

  const handleSendCode = async () => {
    if (!/^1\d{10}$/.test(phone)) { setError('请输入正确的11位手机号'); return }
    setLoading(true); setError('')
    try {
      await sendCode(phone)
      setStep('code')
      startCountdown()
    } catch (e: any) { setError(e.response?.data?.detail || '发送失败') } finally { setLoading(false) }
  }

  const handleLogin = async () => {
    if (!code || code.length < 4) { setError('请输入验证码'); return }
    setLoading(true); setError('')
    try {
      const { login: doLogin } = useAuthStore.getState()
      await doLogin(phone, code)
      closeLogin(); setStep('phone'); setPhone(''); setCode(''); clearCountdown()
      // 登录成功后跳转到待进入的页面
      const path = useAuthStore.getState().pendingPath
      if (path) navigate(path)
    } catch (e: any) { setError(e.response?.data?.detail || '登录失败') } finally { setLoading(false) }
  }

  // 侧边栏链接点击：未登录则弹出登录框，记录目标路径
  const requireAuth = (to: string) => (e: React.MouseEvent) => {
    if (token) return
    e.preventDefault()
    openLogin(to)
  }

  const navCls = (active: boolean) =>
    `flex items-center gap-3.5 mx-4 px-3 py-2.5 rounded-lg text-[15px] transition-colors ${
      active ? 'bg-primary-50 text-primary-700 font-semibold' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-800'
    }`
  const subCls = (active: boolean) =>
    `flex items-center gap-3.5 mx-4 px-3 py-2 rounded-lg text-[13px] transition-colors ${
      active ? 'bg-primary-50 text-primary-700 font-semibold' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
    }`
  const grpCls = (active: boolean) =>
    `w-full flex items-center gap-3.5 mx-4 px-3 py-2.5 rounded-lg text-[15px] transition-colors ${
      active ? 'bg-primary-50 text-primary-700 font-semibold' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-800'
    }`

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Sidebar */}
      <aside className="flex-shrink-0 flex flex-col bg-white border-r border-gray-200" style={{width: 'clamp(200px, 20%, 320px)'}}>
        <div className="px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🌍</span>
            <div>
              <h1 className="text-sm font-bold text-gray-800 leading-tight">智旅</h1>
              <p className="text-[10px] text-gray-400 leading-tight">SmartJourney</p>
            </div>
          </div>
        </div>

        <nav className="py-3 overflow-auto">
          <NavLink to="/" end className={({ isActive }) => navCls(isActive)}>
            <Home size={17} /><span>首页</span>
          </NavLink>

          <div className="mt-1">
            <button onClick={() => { const v = !tripOpen; setTripOpen(v); saveState('trip', v) }} className={grpCls(isTripRoute)}>
              <MapPin size={17} />
              <span className="flex-1 text-left">行程</span>
              {tripOpen ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
            </button>
            {tripOpen && (
              <div className="ml-2 mt-0.5 border-l-2 border-gray-100 space-y-0.5">
                {tripChildren.map(({ to, icon: Icon, label }) => (
                  <NavLink key={to} to={to} onClick={requireAuth(to)} className={({ isActive }) => subCls(isActive)}>
                    <Icon size={15} className="w-[17px]" /><span>{label}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>

          <div className="mt-1">
            <button onClick={() => { const v = !searchOpen; setSearchOpen(v); saveState('search', v) }} className={grpCls(isSearchRoute)}>
              <span className="w-[17px] text-center text-base">🔍</span>
              <span className="flex-1 text-left">搜索</span>
              {searchOpen ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
            </button>
            {searchOpen && (
              <div className="ml-2 mt-0.5 border-l-2 border-gray-100 space-y-0.5">
                {searchChildren.map(({ to, icon, label }) => (
                  <NavLink key={to} to={to} onClick={requireAuth(to)} className={({ isActive }) => subCls(isActive)}>
                    <span className="w-[17px] text-center text-sm">{icon}</span><span>{label}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>

          <NavLink to="/settings" onClick={requireAuth('/settings')} className={({ isActive }) => navCls(isActive)}>
            <Settings size={17} /><span>设置</span>
          </NavLink>
        </nav>

        <div className="px-4 py-3 border-t border-gray-100 mt-auto mb-[5vh]">
          {token && user ? (
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-primary-100 flex items-center justify-center text-primary-600 font-bold text-sm flex-shrink-0">
                {user.nickname?.[0] || '旅'}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-base font-medium text-gray-700 truncate">{user.nickname || '旅行者'}</div>
                <div className="text-sm text-gray-400">{user.phone}</div>
              </div>
              <button onClick={logout} className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="退出登录">
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <button onClick={() => openLogin()} className="text-sm text-primary-600 hover:underline">登录 / 注册</button>
          )}
        </div>
      </aside>

      <main className="flex-1 min-w-0 overflow-y-auto bg-gray-50 p-6">
        <Outlet />
      </main>

      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={closeLoginDialog}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm mx-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">手机号登录 / 注册</h2>
              <button onClick={closeLoginDialog} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <p className="text-xs text-gray-500 mb-4">未注册手机号将自动创建账号</p>
            {error && <div className="bg-red-50 text-red-600 rounded-lg px-3 py-2 text-sm mb-3">{error}</div>}

            <div className={step === 'phone' ? '' : 'hidden'}>
              <label className="text-xs text-gray-500 mb-1 block">手机号</label>
              <input type="tel" value={phone} onChange={(e) => { setPhone(e.target.value); setError('') }}
                onKeyDown={(e) => e.key === 'Enter' && handleSendCode()} placeholder="请输入11位手机号"
                maxLength={11} autoFocus className="w-full border border-gray-200 rounded-lg px-4 py-3 mb-4 text-sm outline-none focus:border-primary-400" />
              <button onClick={handleSendCode} disabled={loading || phone.length < 11 || countdown > 0}
                className="w-full bg-primary-600 text-white rounded-lg py-3 font-medium flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-primary-700 transition-colors">
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}
                {countdown > 0 ? `${countdown}s 后重新获取` : '获取验证码'}
              </button>
            </div>

            <div className={step === 'code' ? '' : 'hidden'}>
              <div className="text-sm text-gray-600 mb-2">验证码已发送至 <span className="font-medium text-gray-800">{phone}</span></div>
              <label className="text-xs text-gray-500 mb-1 block">验证码</label>
              <input type="text" value={code} onChange={(e) => { setCode(e.target.value); setError('') }}
                onKeyDown={(e) => e.key === 'Enter' && handleLogin()} placeholder="请输入6位验证码"
                maxLength={6} autoFocus
                className="w-full border border-gray-200 rounded-lg px-4 py-3 mb-1 text-sm outline-none focus:border-primary-400 tracking-[0.3em] text-center text-lg font-bold" />
              <button onClick={handleLogin} disabled={loading || code.length < 4}
                className="w-full bg-primary-600 text-white rounded-lg py-3 font-medium flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-primary-700 transition-colors mb-2">
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}登录
              </button>
              {countdown > 0 ? (
                <p className="text-xs text-gray-400 text-center mb-1">{countdown}s 后可重新获取验证码</p>
              ) : (
                <button onClick={() => { setStep('phone'); setCode(''); clearCountdown() }}
                  className="w-full text-primary-600 text-sm py-2 hover:text-primary-700 font-medium">
                  重新获取验证码
                </button>
              )}
              <button onClick={() => { setStep('phone'); setError(''); setCode(''); clearCountdown() }}
                className="w-full text-gray-500 text-sm py-2 hover:text-gray-700">← 更换手机号</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
