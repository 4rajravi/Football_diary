import { Link, useLocation } from 'react-router-dom'
import { Trophy, MessageCircle, User } from 'lucide-react'

export default function Navbar() {
  const { pathname } = useLocation()

  const linkClass = (path) =>
    `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
      pathname === path || (path !== '/' && pathname.startsWith(path))
        ? 'text-white'
        : 'text-muted hover:text-white'
    }`

  return (
    <nav className="border-b border-border px-6 py-4 flex items-center justify-between">
      <Link to="/" className="flex items-center gap-2.5">
        <span className="text-xl">⚽</span>
        <span className="text-base font-semibold tracking-tight">Football Diary</span>
      </Link>

      <div className="flex items-center gap-1 overflow-x-auto">
        <Link to="/" className={linkClass('/')}>
          <Trophy size={15} />
          Competitions
        </Link>
        <Link to="/chat" className={linkClass('/chat')}>
          <MessageCircle size={15} />
          Ask AI
        </Link>
        <Link to="/individual" className={linkClass('/individual')}>
          <User size={15} />
          Individual
        </Link>
      </div>
    </nav>
  )
}