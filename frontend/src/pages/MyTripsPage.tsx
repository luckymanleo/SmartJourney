import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { useTripStore } from '../stores/tripStore'
import TripCard from '../components/TripCard'

export default function MyTripsPage() {
  const navigate = useNavigate()
  const { trips, loading, fetchTrips, deleteTrip } = useTripStore()

  useEffect(() => {
    fetchTrips()
  }, [])

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-800">我的行程</h1>
        <button
          onClick={() => navigate('/plan')}
          className="bg-primary-600 text-white rounded-full w-10 h-10 flex items-center justify-center"
        >
          <Plus size={22} />
        </button>
      </div>

      {loading && <div className="text-center text-gray-500 py-8">加载中...</div>}

      <div className="space-y-3">
        {trips.map((trip) => (
          <TripCard key={trip.id} trip={trip} onDelete={deleteTrip} />
        ))}
      </div>

      {!loading && trips.length === 0 && (
        <div className="text-center py-16">
          <div className="text-5xl mb-4">🗺️</div>
          <div className="text-gray-500 mb-4">还没有行程</div>
          <button
            onClick={() => navigate('/plan')}
            className="bg-primary-600 text-white rounded-xl px-6 py-3 font-medium"
          >
            创建第一个行程
          </button>
        </div>
      )}
    </div>
  )
}
