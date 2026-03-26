import { Link, useLocation } from 'react-router-dom'
import { Trophy, MessageCircle } from 'lucide-react'

export default function Navbar() {
  const { pathname } = useLocation()

  const linkClass = (path) =>
    `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      pathname === path || (path !== '/' && pathname.startsWith(path))
        ? 'bg-white/10 text-white'
        : 'text-white/60 hover:text-white hover:bg-white/5'
    }`

  return (
    <nav className="border-b border-white/10 px-6 py-3 flex items-center justify-between">
      <Link to="/" className="flex items-center gap-2">
        <span className="text-2xl">⚽</span>
        <span className="text-lg font-semibold tracking-tight">Football Diary</span>
      </Link>

      <div className="flex items-center gap-2">
        <Link to="/" className={linkClass('/')}>
          <Trophy size={16} />
          Competitions
        </Link>
        <Link to="/chat" className={linkClass('/chat')}>
          <MessageCircle size={16} />
          Ask AI
        </Link>
      </div>
    </nav>
  )
}
