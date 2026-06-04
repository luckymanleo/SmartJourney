import { useEffect, useState } from 'react'
import { Save } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { getPreferences, savePreferences as savePrefs } from '../api'

const STRATEGIES = [
  { label: '智能平衡', value: -1, emoji: '🎯' },
  { label: '经济实惠', value: 0,  emoji: '💰' },
  { label: '舒适优先', value: 1,  emoji: '🏨' },
  { label: '最快到达', value: 2,  emoji: '⚡' },
]

export default function SettingsPagePC() {
  const { user } = useAuthStore()
  const [prefs, setPrefs] = useState({
    use_weather: true,
    route_strategy: -1,
  })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getPreferences().then((res) => {
      if (res.data?.data) {
        const loaded = res.data.data
        setPrefs((prev) => ({
          ...prev,
          use_weather: typeof loaded.use_weather === 'boolean' ? loaded.use_weather : prev.use_weather,
          route_strategy: typeof loaded.route_strategy === 'number' ? loaded.route_strategy : prev.route_strategy,
        }))
      }
    }).catch(() => {})
  }, [])

  const handleSave = async () => {
    await savePrefs(prefs)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-xl font-bold text-gray-800 mb-6">我的设置</h1>

      {/* User Info */}
      {user && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6 flex items-center gap-4">
          <div className="w-14 h-14 bg-primary-100 rounded-full flex items-center justify-center text-primary-600 font-bold text-xl flex-shrink-0">
            {user.nickname?.[0] || '旅'}
          </div>
          <div>
            <div className="text-lg font-semibold text-gray-800">{user.nickname || '旅行者'}</div>
            <div className="text-sm text-gray-500">{user.phone}</div>
          </div>
        </div>
      )}

      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">AI 规划偏好</h2>

      {/* Weather Toggle */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-medium text-gray-700">🌤️ 参考天气因素</h3>
            <p className="text-sm text-gray-500 mt-1">
              {prefs.use_weather ? '根据目的地天气自动调整行程' : '不考虑天气因素'}
            </p>
          </div>
          <button
            onClick={() => setPrefs((p) => ({ ...p, use_weather: !p.use_weather }))}
            className={`relative w-11 h-6 rounded-full transition-colors flex-shrink-0 ${
              prefs.use_weather ? 'bg-primary-500' : 'bg-gray-300'
            }`}
          >
            <div
              className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                prefs.use_weather ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Route Strategy */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-base font-medium text-gray-700 mb-3">🎯 路线策略</h3>
        <div className="flex gap-1.5 bg-gray-100 rounded-lg p-1">
          {STRATEGIES.map(s => (
            <button
              key={s.value}
              onClick={() => setPrefs((p) => ({ ...p, route_strategy: s.value }))}
              className={`flex-1 rounded-md py-2.5 text-sm font-medium transition-all text-center ${
                prefs.route_strategy === s.value
                  ? 'bg-white text-gray-800 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <div>{s.emoji}</div>
              <div className="mt-0.5">{s.label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Save Button */}
      <button onClick={handleSave} style={{width:'40%', margin:'0 auto'}}
        className="bg-primary-600 text-white rounded-2xl py-3.5 font-semibold text-base flex items-center justify-center gap-2 hover:bg-primary-700 transition-colors shadow-sm">
        <Save size={20} />
        {saved ? '已保存 ✓' : '保存偏好'}
      </button>
    </div>
  )
}
