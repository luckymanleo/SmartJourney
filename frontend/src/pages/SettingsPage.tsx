import { useEffect, useState } from 'react'
import { LogOut, Save } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { getPreferences, savePreferences as savePrefs } from '../api'

export default function SettingsPage() {
  const { user, logout } = useAuthStore()
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
    <div className="p-4 pb-24">
      <h1 className="text-xl font-bold text-gray-800 mb-4">我的设置</h1>

      {/* User Info */}
      {user && (
        <div className="bg-white rounded-xl border border-gray-100 p-4 mb-4 flex items-center gap-3">
          <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center text-primary-600 font-bold text-lg">
            {user.nickname?.[0] || '旅'}
          </div>
          <div className="flex-1">
            <div className="font-medium text-gray-800">{user.nickname || '旅行者'}</div>
            <div className="text-sm text-gray-500">{user.phone}</div>
          </div>
          <button onClick={logout} className="text-gray-400 hover:text-red-500">
            <LogOut size={18} />
          </button>
        </div>
      )}

      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">AI 规划偏好</h2>

      {/* Weather Toggle */}
      <Section title="🌤️ 参考天气因素">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-700">{prefs.use_weather ? '已开启' : '已关闭'}</p>
            <p className="text-[10px] text-gray-400 mt-0.5">
              {prefs.use_weather ? '根据目的地天气自动调整行程（晴天户外、雨天室内等）' : '不考虑天气，生成通用行程方案'}
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
      </Section>

      {/* Route Strategy */}
      <Section title="🎯 路线策略">
        <div className="flex gap-2">
          {[
            { label: '默认', value: -1, desc: '智能平衡' },
            { label: '💰 经济实惠', value: 0, desc: '低价优先' },
            { label: '🏨 舒适优先', value: 1, desc: '品质体验' },
            { label: '⚡ 最快到达', value: 2, desc: '效率至上' },
          ].map((s) => (
            <button
              key={s.value}
              onClick={() => setPrefs((p) => ({ ...p, route_strategy: s.value }))}
              className={`flex-1 rounded-lg px-2 py-2 text-xs font-medium transition-colors ${
                prefs.route_strategy === s.value
                  ? 'bg-primary-600 text-white shadow'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-primary-300'
              }`}
            >
              <div>{s.label}</div>
              <div className="text-[10px] opacity-70 mt-0.5">{s.desc}</div>
            </button>
          ))}
        </div>
      </Section>

      {/* Save Button */}
      <button onClick={handleSave} className="w-full mt-6 bg-primary-600 text-white rounded-xl py-3 font-medium flex items-center justify-center gap-2">
        <Save size={18} />
        {saved ? '已保存' : '保存偏好'}
      </button>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{title}</h3>
      <div className="bg-white border border-gray-100 rounded-xl p-3">
        {children}
      </div>
    </div>
  )
}
