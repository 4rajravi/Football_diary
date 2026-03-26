import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCompetitions } from '../services/api'

const LEAGUE_ICONS = {
  GB1: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', ES1: '🇪🇸', L1: '🇩🇪', IT1: '🇮🇹', FR1: '🇫🇷',
  CL: '🏆', EL: '🏆', WC: '🌍', EURO: '🇪🇺',
}

const LEAGUE_COLORS = {
  GB1: 'from-purple-600/20 to-purple-900/20 border-purple-500/30',
  ES1: 'from-red-600/20 to-red-900/20 border-red-500/30',
  L1: 'from-red-600/20 to-yellow-900/20 border-red-500/30',
  IT1: 'from-blue-600/20 to-blue-900/20 border-blue-500/30',
  FR1: 'from-blue-600/20 to-red-900/20 border-blue-500/30',
  CL: 'from-blue-700/20 to-indigo-900/20 border-blue-400/30',
  EL: 'from-orange-600/20 to-orange-900/20 border-orange-500/30',
  WC: 'from-green-600/20 to-green-900/20 border-green-500/30',
  EURO: 'from-blue-500/20 to-blue-800/20 border-blue-400/30',
}

export default function CompetitionsPage() {
  const [competitions, setCompetitions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCompetitions()
      .then(setCompetitions)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="animate-pulse text-white/40 text-lg">Loading competitions...</div>
      </div>
    )
  }

  const leagues = competitions.filter(c => c.type === 'domestic_league')
  const cups = competitions.filter(c => c.type !== 'domestic_league')

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="mb-10">
        <h1 className="text-3xl font-bold mb-2">Competitions</h1>
        <p className="text-white/50">Select a competition to explore standings, stats, and history.</p>
      </div>

      {leagues.length > 0 && (
        <>
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-4">
            Domestic Leagues
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
            {leagues.map(comp => (
              <CompetitionCard key={comp.competition_id} comp={comp} />
            ))}
          </div>
        </>
      )}

      {cups.length > 0 && (
        <>
          <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-4">
            International Cups
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {cups.map(comp => (
              <CompetitionCard key={comp.competition_id} comp={comp} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function CompetitionCard({ comp }) {
  const id = comp.competition_id
  const colorClass = LEAGUE_COLORS[id] || 'from-gray-600/20 to-gray-900/20 border-gray-500/30'

  return (
    <Link
      to={`/standings/${id}`}
      className={`block p-5 rounded-xl border bg-gradient-to-br ${colorClass}
                  hover:scale-[1.02] transition-transform duration-200`}
    >
      <div className="flex items-center gap-3">
        <span className="text-2xl">{LEAGUE_ICONS[id] || '⚽'}</span>
        <div>
          <div className="font-semibold">{comp.name}</div>
          <div className="text-sm text-white/40">
            {comp.country_name || comp.type?.replace(/_/g, ' ')}
          </div>
        </div>
      </div>
    </Link>
  )
}
