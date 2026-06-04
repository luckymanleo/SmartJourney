import { Search } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function SearchBar() {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/plan?q=${encodeURIComponent(query.trim())}`)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="flex items-center bg-gray-100 rounded-2xl px-4 py-3">
        <Search size={20} className="text-gray-400 mr-3 flex-shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="想去哪里？试试说「三亚5天亲子游」"
          className="flex-1 bg-transparent outline-none text-gray-700 placeholder-gray-400 text-sm"
        />
      </div>
    </form>
  )
}
