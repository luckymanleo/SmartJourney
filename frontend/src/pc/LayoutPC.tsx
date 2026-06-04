import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { Home, MapPin, ClipboardList, Settings, ChevronDown, ChevronRight, Plus, LogOut } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useAuthStore } from '../stores/authStore'

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
  const { user, token, logout } = useAuthStore()
  const location = useLocation()

  const isSearchRoute = location.pathname.startsWith('/search')
  const isTripRoute   = location.pathname === '/plan' || location.pathname === '/trips' || location.pathname.startsWith('/trips/')

  const [searchOpen, setSearchOpen] = useState(() => loadState('search', isSearchRoute))
  const [tripOpen, setTripOpen]     = useState(() => loadState('trip', isTripRoute))

  useEffect(() => { if (isSearchRoute) setSearchOpen(true) }, [isSearchRoute])
  useEffect(() => { if (isTripRoute)   setTripOpen(true)   }, [isTripRoute])

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
      {/* Sidebar — always visible, no breakpoints */}
      <aside className="flex-shrink-0 flex flex-col bg-white border-r border-gray-200" style={{width: 'clamp(200px, 20%, 320px)'}}>
        {/* Logo */}
        <div className="px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🌍</span>
            <div>
              <h1 className="text-sm font-bold text-gray-800 leading-tight">智旅</h1>
              <p className="text-[10px] text-gray-400 leading-tight">SmartJourney</p>
            </div>
          </div>
        </div>

        {/* Nav */}
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
                  <NavLink key={to} to={to} className={({ isActive }) => subCls(isActive)}>
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
                  <NavLink key={to} to={to} className={({ isActive }) => subCls(isActive)}>
                    <span className="w-[17px] text-center text-sm">{icon}</span><span>{label}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>

          <NavLink to="/settings" className={({ isActive }) => navCls(isActive)}>
            <Settings size={17} /><span>设置</span>
          </NavLink>
        </nav>

        {/* User */}
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
            <div className="text-[11px] text-gray-400 text-center">请登录</div>
          )}
        </div>
      </aside>

      {/* Content — fills remaining space, scrolls independently */}
      <main className="flex-1 min-w-0 overflow-y-auto bg-gray-50 p-6">
        <Outlet />
      </main>
    </div>
  )
}
