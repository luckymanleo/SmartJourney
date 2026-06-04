interface BudgetPanelProps {
  budget: {
    total_estimated: number
    total_actual: number
    categories: Array<{
      category: string
      estimated: number
      actual: number
      currency: string
    }>
  } | null
}

const catLabels: Record<string, string> = {
  transport: '交通',
  lodging: '住宿',
  food: '餐饮',
  tickets: '门票',
  other: '其他',
}

export default function BudgetPanel({ budget }: BudgetPanelProps) {
  if (!budget) return null

  const maxEst = Math.max(...budget.categories.map((c) => c.estimated), 1)

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800">预算概览</h3>
        <div className="text-lg font-bold text-primary-600">
          ¥{budget.total_estimated.toLocaleString()}
        </div>
      </div>

      <div className="space-y-2">
        {budget.categories.map((cat) => (
          <div key={cat.category}>
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>{catLabels[cat.category] || cat.category}</span>
              <span>¥{cat.estimated.toLocaleString()}</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all"
                style={{ width: `${(cat.estimated / maxEst) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
