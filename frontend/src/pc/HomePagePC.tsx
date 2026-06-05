import { useNavigate } from 'react-router-dom'
import { Sparkles, TrendingUp, MapPin, Search, Plane, Train, Hotel, Ticket, Utensils, Car } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '../stores/authStore'
import { useTripStore } from '../stores/tripStore'
import { getPopularDestinations } from '../api'

export default function HomePagePC() {
  const navigate = useNavigate()
  const { token, user, openLogin } = useAuthStore()
  const { trips, fetchTrips } = useTripStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [popularDestinations, setPopularDestinations] = useState<Array<{ name: string; image: string; description: string; tags: string[] }>>([])
  const loaded = useRef(false)
  const prevToken = useRef(token)
  const loginTriggered = useRef(false)

  // 未登录 → 自动弹出登录框
  useEffect(() => {
    if (!token && !loginTriggered.current) {
      loginTriggered.current = true
      openLogin()
    }
  }, [token])

  useEffect(() => {
    if (loaded.current) return; loaded.current = true
    getPopularDestinations(12).then(r => setPopularDestinations(r.data?.data?.destinations || [])).catch(() => {})
    if (token) fetchTrips()
  }, [])

  // 登录后自动加载行程
  useEffect(() => {
    if (token && !prevToken.current) fetchTrips()
    prevToken.current = token
  }, [token])

  const handleAIPlan = () => {
    if (!token) { openLogin('/plan'); return }
    const q = searchQuery.trim()
    navigate(q ? `/plan?q=${encodeURIComponent(q)}` : '/plan')
  }

  const fallbackCities = ['三亚', '成都', '西安', '杭州', '大理', '厦门', '桂林', '张家界', '青岛', '拉萨']

  // 未登录不渲染页面内容（登录弹窗由 LayoutPC 托管）
  if (!token) return null

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Welcome */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800">
          {token ? `${user?.nickname || '旅行者'}，下午好 ☀️` : '探索你的下一次旅程'}
        </h1>
        {!token && (
          <p className="text-sm text-gray-400 mt-1">
            <button onClick={() => openLogin()} className="text-primary-600 hover:underline font-medium">登录</button>
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

      {/* AI Plan */}
      <div className="mb-8 bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles size={20} className="text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-800">AI 智能规划</h2>
        </div>
        <div className="flex gap-3 mb-4">
          <div className="flex-1 flex items-center bg-gray-50 border border-gray-200 rounded-lg px-4">
            <Search size={18} className="text-gray-400 mr-2 flex-shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAIPlan()}
              placeholder="想去哪里？试试说「三亚5天亲子游」"
              className="flex-1 bg-transparent py-3 outline-none text-gray-700 placeholder-gray-400 text-sm"
            />
          </div>
          <button onClick={handleAIPlan}
            className="bg-primary-600 text-white rounded-lg px-6 py-3 font-medium flex items-center gap-2 hover:bg-primary-700 transition-colors whitespace-nowrap text-sm">
            <Sparkles size={18} />
            AI 智能规划
          </button>
        </div>
        <div className="text-xs text-gray-400 mb-2">或直接搜索：</div>
        <div className="grid grid-cols-3 gap-2">
          {[
            { icon: Plane, label: '机票', to: '/search/flights' },
            { icon: Train, label: '火车票', to: '/search/trains' },
            { icon: Hotel, label: '酒店', to: '/search/hotels' },
            { icon: Ticket, label: '景点', to: '/search/pois' },
            { icon: Utensils, label: '美食', to: '/search/foods' },
            { icon: Car, label: '交通', to: '/search/transport' },
          ].map(({ icon: Icon, label, to }) => (
            <button key={to}
              onClick={() => token ? navigate(to) : openLogin(to)}
              className="flex items-center gap-2 bg-gray-50 hover:bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors">
              <Icon size={16} className="text-primary-500 flex-shrink-0" />
              <span className="truncate">{label}</span>
            </button>
          ))}
        </div>
      </div>

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
    </div>
  )
}
