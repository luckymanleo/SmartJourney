import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plane, Train, Hotel, Ticket, Utensils, Car, Sparkles, Loader2, Search } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { sendCode, login, getPopularDestinations } from '../api'

const QUICK_ACTIONS = [
  { label: '机票', icon: Plane, to: '/search/flights' },
  { label: '火车票', icon: Train, to: '/search/trains' },
  { label: '酒店', icon: Hotel, to: '/search/hotels' },
  { label: '景点', icon: Ticket, to: '/search/pois' },
  { label: '美食', icon: Utensils, to: '/search/foods' },
  { label: '同城交通', icon: Car, to: '/search/transport' },
]

export default function HomePage() {
  const navigate = useNavigate()
  const { token, login: doLogin, user, logout } = useAuthStore()
  const [showLogin, setShowLogin] = useState(false)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState<'phone' | 'code'>('phone')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [countdown, setCountdown] = useState(0) // 60秒倒计时

  // 倒计时
  useEffect(() => {
    if (countdown <= 0) return
    const timer = setInterval(() => {
      setCountdown(c => (c <= 1 ? 0 : c - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [countdown > 0])

  const startCountdown = useCallback(() => setCountdown(60), [])
  const clearCountdown = useCallback(() => setCountdown(0), [])

  // 搜索词状态 — 与 AI 规划按钮共享
  const [searchQuery, setSearchQuery] = useState('')

  // 热门目的地 — 从后端加载
  const [popularDestinations, setPopularDestinations] = useState<Array<{name:string;image:string;description:string;tags:string[]}>>([])
  const loaded = useRef(false)
  useEffect(() => {
    if (loaded.current) return; loaded.current = true
    getPopularDestinations(6).then(r => {
      setPopularDestinations(r.data?.data?.destinations || [])
    }).catch(() => {})
  }, [])

  const handleSendCode = async () => {
    if (!/^1\d{10}$/.test(phone)) { setError('请输入正确的11位手机号'); return }
    setLoading(true); setError('')
    try {
      const res = await sendCode(phone)
      setStep('code')
      // mock 模式返回验证码 → 不限频，不启动倒计时
      if (!res.data?.data?.code) startCountdown()
    } catch (e: any) {
      setError(e.response?.data?.detail || '发送失败，请稍后再试')
    } finally { setLoading(false) }
  }

  const handleLogin = async () => {
    if (!code || code.length < 4) { setError('请输入验证码'); return }
    setLoading(true); setError('')
    try {
      await doLogin(phone, code)
      setShowLogin(false); setStep('phone')
      setPhone(''); setCode('')
    } catch (e: any) {
      setError(e.response?.data?.detail || '登录失败，请检查验证码')
    } finally { setLoading(false) }
  }

  const goPlan = (q: string) => {
    if (!token) { setShowLogin(true); return }
    navigate(q ? `/plan?q=${encodeURIComponent(q)}` : '/plan')
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    goPlan(searchQuery.trim())
  }

  const handleAIPlan = () => goPlan(searchQuery.trim())

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            {token ? `你好，${user?.nickname || '旅行者'}` : '智旅 SmartJourney'}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {token ? '今天想去哪儿？' : '智能旅行规划助手'}
          </p>
        </div>
        {token ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">{user?.phone}</span>
            <button onClick={logout} className="text-xs text-gray-400 hover:text-red-500">退出</button>
          </div>
        ) : (
          <button
            onClick={() => setShowLogin(true)}
            className="bg-primary-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            登录 / 注册
          </button>
        )}
      </div>

      {/* Search — 与 AI 规划共享 searchQuery */}
      <form onSubmit={handleSearch} className="relative">
        <div className="flex items-center bg-gray-100 rounded-2xl px-4 py-3">
          <Search size={20} className="text-gray-400 mr-3 flex-shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="想去哪里？试试说「北京到三亚5天亲子游 预算6000」"
            className="flex-1 bg-transparent outline-none text-gray-700 placeholder-gray-400 text-sm"
          />
        </div>
      </form>

      {/* AI Plan Button — 携带搜索词跳转 */}
      <button
        onClick={handleAIPlan}
        className="w-full mt-4 bg-gradient-to-r from-primary-500 to-primary-700 text-white rounded-2xl p-4 flex items-center justify-center gap-2 font-medium shadow-lg shadow-primary-200 hover:shadow-xl transition-shadow"
      >
        <Sparkles size={20} />
        AI 智能规划行程
      </button>

      {/* Quick Actions */}
      <div className="mt-6">
        <h2 className="text-sm font-semibold text-gray-600 mb-3">快速查询</h2>
        <div className="grid grid-cols-3 gap-3">
          {QUICK_ACTIONS.map(({ label, icon: Icon, to }) => (
            <button
              key={to}
              onClick={() => token ? navigate(to) : setShowLogin(true)}
              className="bg-white border border-gray-100 rounded-xl p-3 flex flex-col items-center gap-2 hover:border-primary-200 hover:shadow-sm transition-all"
            >
              <div className="w-10 h-10 bg-primary-50 rounded-full flex items-center justify-center">
                <Icon size={20} className="text-primary-600" />
              </div>
              <span className="text-xs text-gray-700">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Trending Destinations */}
      <div className="mt-6 mb-4">
        <h2 className="text-sm font-semibold text-gray-600 mb-3">热门目的地</h2>
        <div className="flex flex-wrap gap-2">
          {popularDestinations.length > 0 ? (
            popularDestinations.map((dest) => (
              <button
                key={dest.name}
                onClick={() => navigate(`/plan?q=${dest.name}`)}
                className="flex-shrink-0 bg-white border border-gray-100 rounded-full px-4 py-2 text-sm text-gray-700 hover:border-primary-300 hover:text-primary-600 transition-colors"
                title={dest.description}
              >
                {dest.image} {dest.name}
              </button>
            ))
          ) : (
            // fallback 硬编码列表（API 不可用时）
            ['三亚', '成都', '西安', '杭州', '大理', '厦门'].map((city) => (
              <button
                key={city}
                onClick={() => navigate(`/plan?q=${city}`)}
                className="flex-shrink-0 bg-white border border-gray-100 rounded-full px-4 py-2 text-sm text-gray-700 hover:border-primary-300 hover:text-primary-600 transition-colors"
              >
                {city}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black/50 z-[60] flex items-end justify-center" onClick={() => { setShowLogin(false); setError(''); setStep('phone'); clearCountdown() }}>
          <div className="bg-white rounded-t-2xl p-6 w-full max-w-md animate-slide-up pb-8" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">手机号登录 / 注册</h2>
              <button onClick={() => { setShowLogin(false); setError(''); setStep('phone'); clearCountdown() }} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <p className="text-xs text-gray-500 mb-4">未注册手机号将自动创建账号</p>

            {error && <div className="bg-red-50 text-red-600 rounded-lg px-3 py-2 text-sm mb-3">{error}</div>}

            <div className={step === 'phone' ? '' : 'hidden'}>
              <label className="text-xs text-gray-500 mb-1 block">手机号</label>
              <input type="tel" value={phone} onChange={(e) => { setPhone(e.target.value); setError('') }}
                onKeyDown={(e) => e.key === 'Enter' && handleSendCode()} placeholder="请输入11位手机号"
                maxLength={11} autoFocus
                className="w-full border border-gray-200 rounded-lg px-4 py-3 mb-4 text-sm outline-none focus:border-primary-400" />
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
                onKeyDown={(e) => e.key === 'Enter' && handleLogin()} placeholder="请输入验证码"
                maxLength={6} autoFocus
                className="w-full border border-gray-200 rounded-lg px-4 py-3 mb-1 text-sm outline-none focus:border-primary-400 tracking-[0.3em] text-center text-lg font-bold" />
              <button onClick={handleLogin} disabled={loading || code.length < 4}
                className="w-full bg-primary-600 text-white rounded-lg py-3 font-medium flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-primary-700 transition-colors mb-2">
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}
                登录
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
                className="w-full text-gray-500 text-sm py-2 hover:text-gray-700">
                ← 更换手机号
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
        .animate-slide-up { animation: slideUp 0.3s ease-out; }
      `}</style>
    </div>
  )
}
