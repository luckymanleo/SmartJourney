import { useNavigate } from 'react-router-dom'
import { Sparkles, Loader2, TrendingUp, MapPin } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '../stores/authStore'
import { useTripStore } from '../stores/tripStore'
import { sendCode, login as loginApi, getPopularDestinations } from '../api'

export default function HomePagePC() {
  const navigate = useNavigate()
  const { token, login: doLogin, user } = useAuthStore()
  const { trips, fetchTrips } = useTripStore()
  const [showLogin, setShowLogin] = useState(false)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState<'phone' | 'code'>('phone')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [devCode, setDevCode] = useState('')
  const [popularDestinations, setPopularDestinations] = useState<Array<{ name: string; image: string; description: string; tags: string[] }>>([])
  const loaded = useRef(false)

  useEffect(() => {
    if (loaded.current) return; loaded.current = true
    getPopularDestinations(12).then(r => setPopularDestinations(r.data?.data?.destinations || [])).catch(() => {})
    if (token) fetchTrips()
  }, [])

  const handleSendCode = async () => {
    if (!/^1\d{10}$/.test(phone)) { setError('请输入正确的11位手机号'); return }
    setLoading(true); setError('')
    try {
      const res = await sendCode(phone)
      if (res.data?.data?.code) { setDevCode(res.data.data.code); setCode(res.data.data.code) }
      setStep('code')
    } catch (e: any) { setError(e.response?.data?.detail || '发送失败') } finally { setLoading(false) }
  }

  const handleLogin = async () => {
    if (!code || code.length < 4) { setError('请输入验证码'); return }
    setLoading(true); setError('')
    try { await doLogin(phone, code); setShowLogin(false); setStep('phone'); setPhone(''); setCode(''); setDevCode('') }
    catch (e: any) { setError(e.response?.data?.detail || '登录失败') } finally { setLoading(false) }
  }

  const fallbackCities = ['三亚', '成都', '西安', '杭州', '大理', '厦门', '桂林', '张家界', '青岛', '拉萨']

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Welcome */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800">
          {token ? `${user?.nickname || '旅行者'}，下午好 ☀️` : '探索你的下一次旅程'}
        </h1>
        {!token && (
          <p className="text-sm text-gray-400 mt-1">
            <button onClick={() => setShowLogin(true)} className="text-primary-600 hover:underline font-medium">登录</button>
            后使用 AI 规划、搜索等功能
          </p>
        )}
      </div>

      {/* Quick Stats (logged in) */}
      {token && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="text-2xl font-bold text-primary-600">{trips.length}</div>
            <div className="text-sm text-gray-500 mt-1">行程总数</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="text-2xl font-bold text-green-600">{trips.filter(t => t.status === 'active' || t.status === 'planning').length}</div>
            <div className="text-sm text-gray-500 mt-1">进行中</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="text-2xl font-bold text-purple-600">
              ¥{trips.reduce((sum, t) => sum + (t.budget_total || 0), 0).toLocaleString()}
            </div>
            <div className="text-sm text-gray-500 mt-1">总预算</div>
          </div>
        </div>
      )}

      {/* Popular Destinations */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={20} className="text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-800">热门目的地</h2>
        </div>

        {popularDestinations.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
            {popularDestinations.map((dest) => (
              <button key={dest.name} onClick={() => navigate(`/plan?q=${dest.name}3天游`)}
                className="bg-white border border-gray-200 rounded-xl p-4 text-left hover:border-primary-300 hover:shadow-md transition-all group overflow-hidden">
                <div className="flex items-start justify-between mb-2">
                  <span className="text-2xl">{dest.image}</span>
                  {dest.tags?.[0] && (
                    <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full truncate max-w-[80px]">{dest.tags[0]}</span>
                  )}
                </div>
                <div className="font-medium text-gray-800 text-sm group-hover:text-primary-600 transition-colors truncate">{dest.name}</div>
                {dest.description && (
                  <div className="text-[11px] text-gray-400 mt-1 line-clamp-2 leading-relaxed break-words">{dest.description}</div>
                )}
              </button>
            ))}
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {fallbackCities.map((city) => (
              <button key={city} onClick={() => navigate(`/plan?q=${city}3天游`)}
                className="bg-white border border-gray-200 rounded-full px-5 py-2.5 text-sm text-gray-700 hover:border-primary-300 hover:text-primary-600 hover:shadow-sm transition-all">
                {city}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Recent Trips (logged in) */}
      {token && trips.length > 0 && (
        <div className="mt-8">
          <div className="flex items-center gap-2 mb-4">
            <MapPin size={20} className="text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-800">最近行程</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {trips.slice(0, 3).map((trip) => (
              <button key={trip.id} onClick={() => navigate(`/trips/${trip.id}`)}
                className="bg-white border border-gray-200 rounded-xl p-4 text-left hover:border-primary-200 hover:shadow-sm transition-all">
                <div className="text-sm font-medium text-gray-700 truncate">{trip.title}</div>
                <div className="text-xs text-gray-400 mt-1.5">
                  {trip.destination && <span>{trip.destination} · </span>}
                  {trip.traveler_count}人
                  {trip.budget_total && <span> · ¥{trip.budget_total.toLocaleString()}</span>}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={() => { setShowLogin(false); setError(''); setStep('phone') }}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm mx-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">手机号登录 / 注册</h2>
              <button onClick={() => { setShowLogin(false); setError(''); setStep('phone') }} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <p className="text-xs text-gray-500 mb-4">未注册手机号将自动创建账号</p>
            {error && <div className="bg-red-50 text-red-600 rounded-lg px-3 py-2 text-sm mb-3">{error}</div>}

            <div className={step === 'phone' ? '' : 'hidden'}>
              <label className="text-xs text-gray-500 mb-1 block">手机号</label>
              <input type="tel" value={phone} onChange={(e) => { setPhone(e.target.value); setError('') }}
                onKeyDown={(e) => e.key === 'Enter' && handleSendCode()} placeholder="请输入11位手机号"
                maxLength={11} autoFocus className="w-full border border-gray-200 rounded-lg px-4 py-3 mb-4 text-sm outline-none focus:border-primary-400" />
              <button onClick={handleSendCode} disabled={loading || phone.length < 11}
                className="w-full bg-primary-600 text-white rounded-lg py-3 font-medium flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-primary-700 transition-colors">
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}获取验证码
              </button>
            </div>

            <div className={step === 'code' ? '' : 'hidden'}>
              <div className="text-sm text-gray-600 mb-2">验证码已发送至 <span className="font-medium text-gray-800">{phone}</span></div>
              <label className="text-xs text-gray-500 mb-1 block">验证码</label>
              <input type="text" value={code} onChange={(e) => { setCode(e.target.value); setError('') }}
                onKeyDown={(e) => e.key === 'Enter' && handleLogin()} placeholder="请输入6位验证码"
                maxLength={6} autoFocus className="w-full border border-gray-200 rounded-lg px-4 py-3 mb-1 text-sm outline-none focus:border-primary-400 tracking-[0.3em] text-center text-lg font-bold" />
              {devCode && (
                <div className="bg-green-50 text-green-700 rounded-lg px-3 py-1.5 text-xs mb-3 text-center">
                  🔧 开发模式验证码: <span className="font-bold text-base tracking-wider">{devCode}</span>
                </div>
              )}
              <button onClick={handleLogin} disabled={loading || code.length < 4}
                className="w-full bg-primary-600 text-white rounded-lg py-3 font-medium flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-primary-700 transition-colors mb-2">
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}登录
              </button>
              <button onClick={() => { setStep('phone'); setError(''); setDevCode('') }}
                className="w-full text-gray-500 text-sm py-2 hover:text-gray-700">← 更换手机号</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
