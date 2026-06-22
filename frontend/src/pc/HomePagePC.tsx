import { useState, useEffect, useRef, useCallback } from 'react'
import { ChevronDown } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { getTripStats } from '../api'

type Period = 'year' | 'quarter' | 'month'
const PERIODS: { key: Period; label: string }[] = [
  { key: 'year', label: '年' }, { key: 'quarter', label: '季' }, { key: 'month', label: '月' },
]
const QUARTERS = [1, 2, 3, 4]
const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)
const CAT_COLORS: Record<string, string> = {
  '交通': '#6366f1', '住宿': '#f59e0b', '餐饮': '#10b981', '门票': '#3b82f6', '其他': '#9ca3af',
}

interface Stats {
  total_trips: number; active_trips: number; total_budget: number
  monthly_trend: { month: number; count: number; budget: number }[]
  category_breakdown: { category: string; amount: number }[]
}

// ==================== PeriodControl（弹窗模式） ====================

function PeriodControl({ year, period, periodVal, onYearChange, onPeriodChange, onPeriodValChange }: {
  year: number; period: Period; periodVal: number
  onYearChange: (y: number) => void; onPeriodChange: (p: Period) => void; onPeriodValChange: (v: number) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const now = new Date().getFullYear()

  useEffect(() => { setOpen(false) }, [period, year])
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h)
  }, [])

  const label = period === 'year' ? String(year) : period === 'quarter' ? `Q${periodVal}` : `${periodVal}月`
  const yearOptions = Array.from({ length: 5 }, (_, i) => now - 2 + i)

  return (
    <div ref={ref} className="relative inline-flex items-center bg-gray-100 rounded-lg p-0.5 gap-0.5"
      style={{ fontSize: 'clamp(0.625rem, 0.7vw, 0.6875rem)' }}>
      {PERIODS.map(({ key, label: lbl }) => (
        <button key={key} onClick={() => onPeriodChange(key)}
          className={`px-2 py-0.5 rounded-md transition-colors whitespace-nowrap ${period === key ? 'bg-white text-gray-800 shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700'}`}
        >{lbl}</button>
      ))}
      <button onClick={() => setOpen(!open)}
        className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded-md transition-colors ${open ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
        <span className="font-medium">{label}</span>
        <ChevronDown size={10} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 p-2"
          style={{ minWidth: 'clamp(140px, 16vw, 200px)' }}>
          {period === 'year' && (
            <div className="grid grid-cols-3 gap-1">
              {yearOptions.map(y => (
                <button key={y} onClick={() => { onYearChange(y); setOpen(false) }}
                  className={`py-1.5 rounded text-center text-xs transition-colors ${year === y ? 'bg-primary-50 text-primary-600 font-medium' : 'text-gray-500 hover:bg-gray-50'}`}
                >{y}</button>
              ))}
            </div>
          )}
          {period === 'quarter' && (
            <div className="flex gap-1">
              {QUARTERS.map(q => (
                <button key={q} onClick={() => { onPeriodValChange(q); setOpen(false) }}
                  className={`flex-1 py-1.5 rounded text-center text-xs transition-colors ${periodVal === q ? 'bg-primary-50 text-primary-600 font-medium' : 'text-gray-500 hover:bg-gray-50'}`}
                >Q{q}</button>
              ))}
            </div>
          )}
          {period === 'month' && (
            <div className="grid grid-cols-6 gap-1">
              {MONTHS.map(m => (
                <button key={m} onClick={() => { onPeriodValChange(m); setOpen(false) }}
                  className={`py-1.5 rounded text-center text-xs transition-colors ${periodVal === m ? 'bg-primary-50 text-primary-600 font-medium' : 'text-gray-500 hover:bg-gray-50'}`}
                >{m}月</button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ==================== usePeriod hook ====================

function usePeriod(defaultPeriod: Period = 'year') {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [period, setPeriod] = useState<Period>(defaultPeriod)
  const [periodVal, setPeriodVal] = useState(now.getMonth() + 1)
  const handlePeriodChange = useCallback((p: Period) => {
    setPeriod(p)
    if (p !== 'year') setPeriodVal(p === 'quarter' ? Math.ceil((now.getMonth() + 1) / 3) : now.getMonth() + 1)
  }, [])
  return { year, setYear, period, periodVal, setPeriodVal, handlePeriodChange }
}

// ==================== HomePagePC ====================

export default function HomePagePC() {
  const { token, user, openLogin } = useAuthStore()
  const loginTriggered = useRef(false)
  const year = new Date().getFullYear()

  useEffect(() => { if (!token && !loginTriggered.current) { loginTriggered.current = true; openLogin() } }, [token])

  const fs = {
    title: { fontSize: 'clamp(1.25rem, 1.5vw, 1.5rem)' },
    body: { fontSize: 'clamp(0.75rem, 0.85vw, 0.875rem)' },
    small: { fontSize: 'clamp(0.6875rem, 0.75vw, 0.75rem)' },
    number: { fontSize: 'clamp(1.75rem, 2.5vw, 2.5rem)' },
  }

  if (!token) return null

  return (
    <div style={{ maxWidth: 'clamp(960px, 92%, 1500px)', margin: '0 auto', padding: 'clamp(16px, 2vw, 32px)' }}>
      <div className="mb-6"><h1 className="font-bold text-gray-800" style={fs.title}>{user?.nickname || '旅行者'}，下午好 ☀️</h1></div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-5 mb-6">
        <StatCard label="行程总数" color="text-primary-600" token={token} year={year} fs={fs}
          getValue={(s) => s?.total_trips} />
        <StatCard label="进行中" color="text-green-600" token={token} year={year} fs={fs}
          getValue={(s) => s?.active_trips} />
        <StatCard label="总预算" color="text-purple-600" token={token} year={year} fs={fs}
          getValue={(s) => s ? `¥${s.total_budget.toLocaleString()}` : undefined} />
      </div>

      {/* 消费详情 */}
      <div className="grid grid-cols-3 gap-5">
          <TrendCard token={token} year={year} fs={fs} />
          <CategoryCard token={token} year={year} fs={fs} />
        </div>
    </div>
  )
}

// ==================== 统计卡片（独立周期 + 独立数据） ====================

function StatCard({ label, color, token, year, fs, getValue }: {
  label: string; color: string; token: string | null; year: number; fs: any
  getValue: (s: Stats | null) => number | string | undefined
}) {
  const p = usePeriod('year')
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    if (!token) return
    getTripStats({ year: p.year, period: p.period, period_value: p.period !== 'year' ? p.periodVal : undefined })
      .then(r => setStats(r.data?.data || null)).catch(() => setStats(null))
  }, [token, p.year, p.period, p.periodVal])

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-3">
        <span className="text-gray-500" style={fs.small}>{label}</span>
        <PeriodControl year={p.year} period={p.period} periodVal={p.periodVal}
          onYearChange={p.setYear} onPeriodChange={p.handlePeriodChange} onPeriodValChange={p.setPeriodVal} />
      </div>
      <div className={`font-bold ${color}`} style={fs.number}>{getValue(stats) ?? '—'}</div>
    </div>
  )
}

// ==================== 月度趋势卡片 ====================

function TrendCard({ token, year: _year, fs }: { token: string | null; year: number; fs: any }) {
  const tp = usePeriod('year')
  const [data, setData] = useState<Stats | null>(null)
  const [lastData, setLastData] = useState<Stats | null>(null)

  useEffect(() => {
    if (!token) return
    getTripStats({ year: tp.year, period: tp.period, period_value: tp.period !== 'year' ? tp.periodVal : undefined })
      .then(r => setData(r.data?.data || null)).catch(() => setData(null))
  }, [token, tp.year, tp.period, tp.periodVal])
  useEffect(() => {
    if (!token || tp.period !== 'year') { setLastData(null); return }
    getTripStats({ year: tp.year - 1, period: 'year' })
      .then(r => setLastData(r.data?.data || null)).catch(() => setLastData(null))
  }, [token, tp.year, tp.period])

  const isComparing = tp.period === 'year' && !!lastData
  const all12 = Array.from({ length: 12 }, (_, i) => {
    const m = i + 1
    const cur = data?.monthly_trend?.find((t: any) => t.month === m)
    const prev = lastData?.monthly_trend?.find((t: any) => t.month === m)
    return { label: `${m}月`, value: cur?.budget ?? 0, active: !!cur, compare: prev?.budget ?? 0 }
  })

  return (
    <div className="col-span-2 bg-white rounded-xl border border-gray-200 p-6 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <span className="text-gray-600 font-medium" style={fs.body}>
          {tp.period === 'year' ? `${tp.year} 年月度趋势` : tp.period === 'quarter' ? `${tp.year} Q${tp.periodVal}` : `${tp.year} 年${tp.periodVal}月`}
        </span>
        <PeriodControl year={tp.year} period={tp.period} periodVal={tp.periodVal}
          onYearChange={tp.setYear} onPeriodChange={tp.handlePeriodChange} onPeriodValChange={tp.setPeriodVal} />
      </div>
      <div className="flex-1 flex items-end" style={{ minHeight: 'clamp(180px, 20vw, 260px)' }}>
        {data ? <BarChart data={all12} fs={fs} compare={isComparing} year={tp.year} /> : <Loading fs={fs} />}
      </div>
    </div>
  )
}

// ==================== 分类占比卡片 ====================

function CategoryCard({ token, year: _year, fs }: { token: string | null; year: number; fs: any }) {
  const tp = usePeriod('year')
  const [data, setData] = useState<Stats | null>(null)

  useEffect(() => {
    if (!token) return
    getTripStats({ year: tp.year, period: tp.period, period_value: tp.period !== 'year' ? tp.periodVal : undefined })
      .then(r => setData(r.data?.data || null)).catch(() => setData(null))
  }, [token, tp.year, tp.period, tp.periodVal])

  return (
    <div className="col-span-1 bg-white rounded-xl border border-gray-200 p-6 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <span className="text-gray-600 font-medium" style={fs.body}>消费分类</span>
        <PeriodControl year={tp.year} period={tp.period} periodVal={tp.periodVal}
          onYearChange={tp.setYear} onPeriodChange={tp.handlePeriodChange} onPeriodValChange={tp.setPeriodVal} />
      </div>
      <div className="flex-1 flex items-center justify-center" style={{ minHeight: 'clamp(180px, 20vw, 260px)' }}>
        {data ? <DonutChart data={data.category_breakdown.filter(c => c.amount > 0)} fs={fs} /> : <Loading fs={fs} />}
      </div>
    </div>
  )
}

// ==================== 小工具 ====================

function Loading({ fs }: { fs: any }) {
  return <div className="flex-1 flex items-center justify-center text-gray-400" style={fs.small}>加载中...</div>
}

// ==================== 图表 ====================

const CHART_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#3b82f6', '#ec4899', '#8b5cf6', '#06b6d4', '#f97316', '#84cc16', '#14b8a6']
const THIS_YEAR_COLOR = '#6366f1'
const LAST_YEAR_COLOR = '#9ca3af'

interface BarItem { label: string; value: number; active?: boolean; compare?: number }

function BarChart({ data, fs, compare, year }: { data: BarItem[]; fs: any; compare?: boolean; year?: number }) {
  const maxVal = Math.max(...data.map(d => compare ? Math.max(d.value, d.compare ?? 0) : d.value), 1)
  const gridLines = 4; const step = maxVal / gridLines
  return (
    <div className="w-full h-full flex flex-col" style={{ minHeight: 'clamp(160px, 18vw, 230px)' }}>
      {compare && <ChartLegend year={year!} />}
      <div className="flex flex-1">
        <YAxis gridLines={gridLines} step={step} />
        <div className="flex-1 relative">
          <GridLines gridLines={gridLines} />
          <div className="absolute inset-0 flex items-end" style={{ gap: compare ? 'clamp(2px, 0.3vw, 4px)' : '3px', padding: '0 1px' }}>
            {data.map((d, i) => {
              const isActive = d.active !== false
              return compare
                ? <GroupBar key={i} d={d} maxVal={maxVal} isActive={isActive} />
                : <SingleBar key={i} d={d} i={i} maxVal={maxVal} isActive={isActive} />
            })}
          </div>
        </div>
      </div>
      <XAxis data={data} />
    </div>
  )
}
function ChartLegend({ year }: { year: number }) {
  return (
    <div className="flex items-center gap-4 mb-2" style={{ paddingLeft: 'clamp(44px, 5vw, 56px)' }}>
      <Legend color={THIS_YEAR_COLOR} label={String(year)} />
      <Legend color={LAST_YEAR_COLOR} label={String(year - 1)} muted />
    </div>
  )
}
function YAxis({ gridLines, step }: { gridLines: number; step: number }) {
  return (
    <div className="flex flex-col justify-between items-end pr-2 pb-5" style={{ minWidth: 'clamp(44px, 5vw, 56px)' }}>
      {Array.from({ length: gridLines + 1 }, (_, i) => (
        <span key={i} className="text-gray-500 leading-none" style={{ fontSize: 'clamp(0.625rem, 0.7vw, 0.75rem)' }}>
          ¥{(gridLines - i) * step >= 1000 ? `${((gridLines - i) * step / 1000).toFixed(1)}k` : (gridLines - i) * step}
        </span>
      ))}
    </div>
  )
}
function GridLines({ gridLines }: { gridLines: number }) {
  return <>{Array.from({ length: gridLines + 1 }, (_, i) => (
    <div key={i} className="absolute left-0 right-0 border-t border-gray-200" style={{ bottom: `${(i / gridLines) * 100}%` }} />
  ))}</>
}
function XAxis({ data }: { data: BarItem[] }) {
  return (
    <div className="flex" style={{ paddingLeft: 'clamp(44px, 5vw, 56px)' }}>
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex justify-center pt-1">
          <span className={(d.active !== false ? 'text-gray-500' : 'text-gray-400')} style={{ fontSize: 'clamp(0.6875rem, 0.75vw, 0.8125rem)' }}>{d.label}</span>
        </div>
      ))}
    </div>
  )
}
function GroupBar({ d, maxVal, isActive }: { d: BarItem; maxVal: number; isActive: boolean }) {
  const h1 = (d.value / maxVal) * 100; const h2 = ((d.compare ?? 0) / maxVal) * 100
  return (
    <div className="flex-1 flex items-end justify-center gap-[1px] h-full">
      <div className="flex-1 rounded-t-sm" style={{ maxWidth: '45%', height: `${h2}%`, minHeight: (d.compare ?? 0) > 0 ? '2px' : '0', backgroundColor: LAST_YEAR_COLOR, transition: 'height 0.3s ease' }} />
      <div className="flex-1 rounded-t-sm" style={{ maxWidth: '45%', height: `${h1}%`, minHeight: d.value > 0 ? '2px' : '0', backgroundColor: isActive ? THIS_YEAR_COLOR : '#d1d5db', transition: 'height 0.3s ease' }} />
    </div>
  )
}
function SingleBar({ d, i, maxVal, isActive }: { d: BarItem; i: number; maxVal: number; isActive: boolean }) {
  const h = (d.value / maxVal) * 100
  return (
    <div className="flex-1 flex flex-col items-center justify-end h-full">
      <div className="w-full rounded-t group relative"
        style={{ height: `${h}%`, minHeight: d.value > 0 ? '2px' : '0', backgroundColor: isActive ? CHART_COLORS[i % CHART_COLORS.length] : '#d1d5db', transition: 'height 0.3s ease' }}>
        {isActive && d.value > 0 && (
          <div className="absolute -top-5 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-gray-700 font-medium whitespace-nowrap" style={{ fontSize: 'clamp(0.6875rem, 0.75vw, 0.8125rem)' }}>¥{d.value.toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  )
}
function Legend({ color, label, muted }: { color: string; label: string; muted?: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: color }} />
      <span className={muted ? 'text-gray-500' : 'text-gray-700'} style={{ fontSize: 'clamp(0.6875rem, 0.75vw, 0.8125rem)' }}>{label}</span>
    </div>
  )
}

function DonutChart({ data, fs }: { data: { category: string; amount: number }[]; fs: any }) {
  const total = data.reduce((s, d) => s + d.amount, 0) || 1
  const size = 120; const cx = size / 2; const cy = size / 2
  const r = 40; const circ = 2 * Math.PI * r; const gap = 0.015
  if (total <= 0 || data.length === 0) return (
    <div className="flex flex-col items-center justify-center gap-3 h-full" style={{ minHeight: 'clamp(180px, 20vw, 260px)' }}>
      <div className="w-[100px] h-[100px] rounded-full border-[8px] border-gray-200 flex items-center justify-center"><span className="text-gray-400" style={fs.small}>¥0</span></div>
      <span className="text-gray-400" style={fs.small}>暂无数据</span>
    </div>
  )
  let off = 0; const sorted = [...data].sort((a, b) => b.amount - a.amount)
  return (
    <div className="flex items-center gap-4 h-full w-full" style={{ minHeight: 'clamp(180px, 20vw, 260px)' }}>
      <div className="relative flex-shrink-0" style={{ width: 'clamp(100px, 12vw, 130px)', height: 'clamp(100px, 12vw, 130px)' }}>
        <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-full -rotate-90">
          {sorted.map((d) => {
            const dash = circ * Math.max(d.amount / total - gap, 0); const sdo = -off; off += circ * (d.amount / total)
            return <circle key={d.category} cx={cx} cy={cy} r={r} fill="none"
              stroke={CAT_COLORS[d.category] || CHART_COLORS[sorted.indexOf(d) % CHART_COLORS.length]}
              strokeWidth="10" strokeLinecap="round" strokeDasharray={`${dash} ${circ - dash}`} strokeDashoffset={sdo} />
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-bold text-gray-800" style={{ fontSize: 'clamp(0.9375rem, 1.1vw, 1.125rem)' }}>¥{(total / 1000).toFixed(1)}k</span>
          <span className="text-gray-500" style={{ fontSize: 'clamp(0.6875rem, 0.75vw, 0.8125rem)' }}>总计</span>
        </div>
      </div>
      <div className="flex-1 flex flex-col gap-1.5 min-w-0">
        {sorted.map((d) => (
          <div key={d.category} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: CAT_COLORS[d.category] || CHART_COLORS[sorted.indexOf(d) % CHART_COLORS.length] }} />
            <span className="text-gray-600 truncate" style={fs.small}>{d.category}</span>
            <span className="text-gray-500 ml-auto flex-shrink-0 tabular-nums" style={{ fontSize: 'clamp(0.6875rem, 0.75vw, 0.8125rem)' }}>{((d.amount / total) * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
