/**
 * 搜索结果骨架屏 — 搜索加载中显示
 */
export function SearchSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-white border border-gray-100 rounded-xl p-4 animate-pulse">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-gray-200 rounded-lg flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-gray-200 rounded w-3/5" />
              <div className="h-3 bg-gray-100 rounded w-full" />
              <div className="h-3 bg-gray-100 rounded w-4/5" />
            </div>
            <div className="text-right space-y-1 flex-shrink-0">
              <div className="h-5 bg-gray-200 rounded w-16" />
              <div className="h-3 bg-gray-100 rounded w-12 ml-auto" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
