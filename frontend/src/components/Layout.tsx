import { Outlet, NavLink } from 'react-router-dom'
import { Home, Search, MapPin, ClipboardList, User } from 'lucide-react'

const navItems = [
  { to: '/', icon: Home, label: '首页' },
  { to: '/plan', icon: MapPin, label: 'AI规划' },
  { to: '/trips', icon: ClipboardList, label: '行程' },
  { to: '/settings', icon: User, label: '我的' },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col max-w-md mx-auto bg-white shadow-lg">
      {/* Main content */}
      <main className="flex-1 overflow-auto pb-16">
        <Outlet />
      </main>

      {/* Bottom navigation */}
      <nav className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-white border-t border-gray-200 z-40">
        <div className="flex justify-around py-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex flex-col items-center px-3 py-1 text-xs transition-colors ${
                  isActive ? 'text-primary-600' : 'text-gray-500'
                }`
              }
            >
              <Icon size={22} />
              <span className="mt-1">{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
