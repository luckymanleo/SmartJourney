import { Routes, Route, useNavigate } from 'react-router-dom'
import { useEffect, useRef } from 'react'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import PlanPage from './pages/PlanPage'
import TripDetailPage from './pages/TripDetailPage'
import MyTripsPage from './pages/MyTripsPage'
import SettingsPage from './pages/SettingsPage'
import { useAuthStore } from './stores/authStore'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  const navigate = useNavigate()
  if (!token) {
    return (
      <div className="p-4">
        <div className="flex flex-col items-center justify-center py-20">
          <div className="text-5xl mb-4">🔒</div>
          <div className="text-gray-500 text-sm mb-6">请先登录后访问此页面</div>
          <button
            onClick={() => navigate('/')}
            className="bg-primary-600 text-white rounded-xl px-6 py-3 font-medium text-sm"
          >
            返回首页登录
          </button>
        </div>
      </div>
    )
  }
  return <>{children}</>
}

export default function App() {
  const restore = useAuthStore((s) => s.restore)
  const called = useRef(false)
  useEffect(() => { if (!called.current) { called.current = true; restore() } }, [])
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/search/:type" element={<ProtectedRoute><SearchPage /></ProtectedRoute>} />
        <Route path="/plan" element={<ProtectedRoute><PlanPage /></ProtectedRoute>} />
        <Route path="/trips" element={<ProtectedRoute><MyTripsPage /></ProtectedRoute>} />
        <Route path="/trips/:id" element={<ProtectedRoute><TripDetailPage /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      </Route>
    </Routes>
  )
}
