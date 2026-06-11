import { create } from 'zustand'

interface Trip {
  id: string
  title: string
  status: string
  origin: string | null
  destination: string | null
  dest_lng: number | null
  dest_lat: number | null
  start_date: string | null
  end_date: string | null
  traveler_count: number
  budget_total: number | null
  route_tag: string | null
  weather_info: string | null
  tips: string[] | null
  summary: string | null
  special_notes: string | null
  created_at: string | null
  days: TripDay[]
}

interface TripDay {
  id: string
  day_number: number
  date: string | null
  items: TripItem[]
}

interface TripItem {
  id: string
  type: string
  title: string
  start_time: string | null
  end_time: string | null
  price: number | null
  booking_url: string | null
  extra_data: any
}

interface TripStore {
  trips: Trip[]
  currentTrip: Trip | null
  loading: boolean
  fetchTrips: () => Promise<void>
  fetchTrip: (id: string) => Promise<void>
  createTrip: (data: any) => Promise<Trip>
  deleteTrip: (id: string) => Promise<void>
  addItem: (tripId: string, data: any) => Promise<void>
  removeItem: (tripId: string, itemId: string) => Promise<void>
}

export const useTripStore = create<TripStore>((set, get) => ({
  trips: [],
  currentTrip: null,
  loading: false,

  fetchTrips: async () => {
    set({ loading: true })
    try {
      const { getTrips } = await import('../api')
      const res = await getTrips()
      set({ trips: res.data.data.items, loading: false })
    } catch (e: any) {
      set({ loading: false })
      if (e?.response?.status !== 401) {
        console.error('fetchTrips failed:', e?.message || e)
      }
    }
  },

  fetchTrip: async (id) => {
    set({ loading: true })
    try {
      const { getTrip } = await import('../api')
      const res = await getTrip(id)
      set({ currentTrip: res.data.data, loading: false })
    } catch (e: any) {
      set({ loading: false })
      if (e?.response?.status !== 401) {
        console.error('fetchTrip failed:', e?.message || e)
      }
    }
  },

  createTrip: async (data) => {
    const { createTrip } = await import('../api')
    const res = await createTrip(data)
    const trip = res.data.data
    set((s) => ({ trips: [trip, ...s.trips] }))
    return trip
  },

  deleteTrip: async (id) => {
    const { deleteTrip } = await import('../api')
    await deleteTrip(id)
    set((s) => ({ trips: s.trips.filter((t) => t.id !== id) }))
  },

  addItem: async (tripId, data) => {
    const { addTripItem, getTrip } = await import('../api')
    await addTripItem(tripId, data)
    const res = await getTrip(tripId)
    set({ currentTrip: res.data.data })
  },

  removeItem: async (tripId, itemId) => {
    const { removeTripItem, getTrip } = await import('../api')
    await removeTripItem(tripId, itemId)
    const res = await getTrip(tripId)
    set({ currentTrip: res.data.data })
  },
}))
