import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 90000,
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const store = useAuthStore.getState()
      // 防止死循环：1秒内不重复触发 logout
      if (!store._logoutTriggered) {
        store._logoutTriggered = true
        store.logout()
      }
    }
    return Promise.reject(err)
  }
)

export default api
