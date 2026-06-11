import { useEffect, useState } from 'react'
import { Save, Pencil, Check, X } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { getPreferences, savePreferences as savePrefs, updateProfile } from '../api'

const STRATEGIES = [
  { label: '智能平衡', value: -1, emoji: '🎯' },
  { label: '经济实惠', value: 0,  emoji: '💰' },
  { label: '舒适优先', value: 1,  emoji: '🏨' },
  { label: '最快到达', value: 2,  emoji: '⚡' },
]

export default function SettingsPagePC() {
  const { user, token, login: _login } = useAuthStore()
  const [prefs, setPrefs] = useState({ use_weather: true, route_strategy: -1, special_notes: '' })
  const [saved, setSaved] = useState(false)

  const [editing, setEditing] = useState(false)
  const [nickname, setNickname] = useState(user?.nickname || '')
  const [nickError, setNickError] = useState('')
  const [nickSaving, setNickSaving] = useState(false)

  useEffect(() => {
    getPreferences().then((res) => {
      if (res.data?.data) {
        const loaded = res.data.data
        setPrefs((prev) => ({
          ...prev,
          use_weather: typeof loaded.use_weather === 'boolean' ? loaded.use_weather : prev.use_weather,
          route_strategy: typeof loaded.route_strategy === 'number' ? loaded.route_strategy : prev.route_strategy,
          special_notes: typeof loaded.special_notes === 'string' ? loaded.special_notes : prev.special_notes,
        }))
      }
    }).catch(() => {})
  }, [])

  useEffect(() => { setNickname(user?.nickname || '') }, [user?.nickname])

  const handleSaveNick = async () => {
    const v = nickname.trim()
    if (!v) { setNickError('昵称不能为空'); return }
    if (v.length < 2 || v.length > 20) { setNickError('昵称需在 2-20 个字符之间'); return }
    setNickSaving(true); setNickError('')
    try {
      await updateProfile({ nickname: v })
      setEditing(false)
      const store = useAuthStore.getState()
      if (store.user) {
        useAuthStore.setState({ user: { ...store.user, nickname: v } })
      }
    } catch (e: any) {
      setNickError(e.response?.data?.detail || '保存失败')
    } finally { setNickSaving(false) }
  }

  const handleSave = async () => {
    await savePrefs(prefs)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const fs = {
    title: { fontSize: 'clamp(1rem, 1.3vw, 1.25rem)' },
    heading: { fontSize: 'clamp(0.8125rem, 0.95vw, 0.9375rem)' },
    body: { fontSize: 'clamp(0.75rem, 0.85vw, 0.875rem)' },
    small: { fontSize: 'clamp(0.6875rem, 0.75vw, 0.75rem)' },
  }

  return (
    <div className="mx-auto" style={{maxWidth: 'clamp(500px, 60%, 900px)', padding: 'clamp(12px, 1.5vw, 24px)'}}>
      <h1 className="font-bold text-gray-800 mb-5" style={fs.title}>我的设置</h1>

      {user && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-5 flex items-center gap-4">
          <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center text-primary-600 font-bold flex-shrink-0" style={fs.heading}>
            {user.nickname?.[0] || '旅'}
          </div>
          <div className="flex-1 min-w-0">
            {editing ? (
              <div className="flex items-center gap-2">
                <input type="text" value={nickname} onChange={(e) => { setNickname(e.target.value); setNickError('') }}
                  maxLength={20} autoFocus
                  className="border border-gray-200 rounded-lg px-3 py-2 font-semibold text-gray-800 outline-none focus:border-primary-400"
                  style={{width: 'clamp(120px, 50%, 200px)', fontSize: 'clamp(0.8125rem, 0.92vw, 0.9375rem)'}} />
                <button onClick={handleSaveNick} disabled={nickSaving}
                  className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg"><Check size={18} /></button>
                <button onClick={() => { setEditing(false); setNickname(user.nickname || ''); setNickError('') }}
                  className="p-1.5 text-gray-400 hover:bg-gray-50 rounded-lg"><X size={18} /></button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <div className="font-semibold text-gray-800" style={fs.heading}>{user.nickname || '旅行者'}</div>
                <button onClick={() => { setEditing(true); setNickname(user.nickname || ''); setNickError('') }}
                  className="p-1 text-gray-400 hover:text-primary-600"><Pencil size={15} /></button>
              </div>
            )}
            {nickError && <div className="text-red-500 mt-1" style={fs.small}>{nickError}</div>}
            <div className="text-gray-500" style={fs.small}>{user.phone}</div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-5">
        <h2 className="font-semibold text-gray-400 uppercase tracking-wide mb-4" style={fs.body}>AI 规划偏好</h2>

        <div className="bg-gray-50 rounded-lg p-4 mb-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-700" style={fs.body}>🌤️ 参考天气因素</h3>
              <p className="text-gray-500 mt-1" style={fs.small}>
                {prefs.use_weather ? '根据目的地天气自动调整行程' : '不考虑天气因素'}
              </p>
            </div>
            <button onClick={() => setPrefs((p) => ({ ...p, use_weather: !p.use_weather }))}
              className={`relative w-11 h-6 rounded-full transition-colors flex-shrink-0 ${prefs.use_weather ? 'bg-primary-500' : 'bg-gray-300'}`}>
              <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${prefs.use_weather ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4 mb-3">
          <h3 className="font-medium text-gray-700 mb-2" style={fs.body}>🎯 路线策略</h3>
          <div className="flex gap-1.5 bg-gray-100 rounded-lg p-1">
            {STRATEGIES.map(s => (
              <button key={s.value} onClick={() => setPrefs((p) => ({ ...p, route_strategy: s.value }))}
                className={`flex-1 rounded-md text-center font-medium transition-all ${prefs.route_strategy === s.value ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                style={{...fs.small, padding: 'clamp(6px, 1vh, 10px) clamp(4px, 0.5vw, 8px)'}}>
                <div>{s.emoji}</div>
                <div className="mt-0.5">{s.label}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4 mb-5">
          <h3 className="font-medium text-gray-700 mb-2" style={fs.body}>⚠️ 特殊说明（选填）</h3>
          <input type="text" value={prefs.special_notes}
            onChange={(e) => setPrefs((p) => ({ ...p, special_notes: e.target.value }))}
            placeholder="例如：花粉过敏、素食、行动不便"
            className="w-full border border-gray-200 rounded-lg outline-none focus:border-primary-400 bg-white"
            style={{...fs.body, padding: 'clamp(6px, 1vh, 10px) clamp(8px, 1.2vw, 12px)'}} />
          <p className="text-gray-400 mt-1" style={fs.small}>设置后将在 AI 规划时自动填入，避免生成不合适的行程。</p>
        </div>

        <button onClick={handleSave}
          className="bg-primary-600 text-white rounded-2xl py-3.5 font-semibold flex items-center justify-center gap-2 hover:bg-primary-700 transition-colors shadow-sm whitespace-nowrap"
          style={{width:'40%', margin:'0 auto', fontSize: 'clamp(0.8125rem, 0.95vw, 0.9375rem)'}}>
          <Save size={18} />
          {saved ? '已保存 ✓' : '保存偏好'}
        </button>
      </div>
    </div>
  )
}
