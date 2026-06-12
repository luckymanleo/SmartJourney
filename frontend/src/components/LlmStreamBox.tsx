import { memo } from 'react'
import { usePlanStore } from '../stores/planStore'

/**
 * 独立的 LLM 打字机组件 — 只在 llmStream 变化时渲染
 * 父组件不会因为它而变化，消除抖动。
 */
const LlmStreamBox = memo(function LlmStreamBox() {
  const llmStream = usePlanStore(s => s.llmStream)
  const toolPhase = usePlanStore(s => s.toolPhase)
  const tripData = usePlanStore(s => s.tripData)

  if (toolPhase !== 'done' || tripData || !llmStream) return null

  return (
    <div className="bg-gray-50 rounded-lg p-3 mt-2 h-44 overflow-y-auto">
      <div className="text-gray-600 leading-relaxed whitespace-pre-wrap font-mono text-[11px]">
        {llmStream.split('\n').slice(-8).join('\n')}
      </div>
    </div>
  )
})

export default LlmStreamBox
