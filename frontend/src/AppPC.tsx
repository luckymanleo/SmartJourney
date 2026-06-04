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

export default function AppPC() {
  const restore = useAuthStore((s) => s.restore)
  const called = useRef(false)
  useEffect(() => { if (!called.current) { called.current = true; restore() } }, [])

  return (
    <Routes>
      <Route element={<LayoutPC />}>
        <Route path="/" element={<HomePagePC />} />
        <Route path="/search/:type" element={<SearchPagePC />} />
        <Route path="/plan" element={<PlanPagePC />} />
        <Route path="/trips" element={<MyTripsPagePC />} />
        <Route path="/trips/:id" element={<TripDetailPagePC />} />
        <Route path="/settings" element={<SettingsPagePC />} />
      </Route>
    </Routes>
  )
}
