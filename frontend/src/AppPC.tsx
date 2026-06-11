import { Routes, Route } from 'react-router-dom'
import { useEffect, useRef } from 'react'
import LayoutPC from './pc/LayoutPC'
import HomePagePC from './pc/HomePagePC'
import SearchPagePC from './pc/SearchPagePC'
import PlanPagePC from './pc/PlanPagePC'
import MyTripsPagePC from './pc/MyTripsPagePC'
import TripDetailPagePC from './pc/TripDetailPagePC'
import SettingsPagePC from './pc/SettingsPagePC'
import { useAuthStore } from './stores/authStore'

function ProtectedRoutePC({ children }: { children: React.ReactNode }) {
  const { token, openLogin } = useAuthStore()
  useEffect(() => { if (!token) openLogin() }, [token])
  if (!token) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-4xl mb-3">🔒</div>
          <div className="text-gray-500 text-sm mb-4">请先登录后访问此页面</div>
          <button onClick={() => openLogin()}
            className="bg-primary-600 text-white rounded-lg px-6 py-2.5 text-sm font-medium hover:bg-primary-700">
            登录 / 注册
          </button>
        </div>
      </div>
    )
  }
  return <>{children}</>
}

export default function AppPC() {
  const restore = useAuthStore((s) => s.restore)
  const called = useRef(false)
  useEffect(() => { if (!called.current) { called.current = true; restore() } }, [])

  return (
    <Routes>
      <Route element={<LayoutPC />}>
        <Route path="/" element={<HomePagePC />} />
        <Route path="/search/:type" element={<ProtectedRoutePC><SearchPagePC /></ProtectedRoutePC>} />
        <Route path="/plan" element={<ProtectedRoutePC><PlanPagePC /></ProtectedRoutePC>} />
        <Route path="/trips" element={<ProtectedRoutePC><MyTripsPagePC /></ProtectedRoutePC>} />
        <Route path="/trips/:id" element={<ProtectedRoutePC><TripDetailPagePC /></ProtectedRoutePC>} />
        <Route path="/settings" element={<ProtectedRoutePC><SettingsPagePC /></ProtectedRoutePC>} />
      </Route>
    </Routes>
  )
}
