import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCompetitions } from '../services/api'

const LEAGUE_LOGOS = {
  GB1: '/assets/logo/GB1.png',
  ES1: '/assets/logo/ES1.png',
  L1: '/assets/logo/L1.png',
  IT1: '/assets/logo/IT1.png',
  FR1: '/assets/logo/FR1.png',
  CL: '/assets/logo/CL.png',
  EL: '/assets/logo/EL.png',
  ALL5: '/assets/logo/ALL5.png',
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
        <div className="text-muted text-sm">Loading...</div>
      </div>
    )
  }

  const leagues = competitions.filter(c => c.type === 'domestic_league')
  const cups = competitions.filter(c => c.type !== 'domestic_league')
  const allLeagues = { competition_id: 'ALL5', name: 'All Leagues (Top 5)', type: 'combined' }
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <h1 className="text-2xl font-bold mb-10">Competitions</h1>

      {leagues.length > 0 && (
        <div className="mb-10">
          <p className="text-xs text-muted uppercase tracking-widest mb-4">Domestic Leagues</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <CompetitionCard comp={allLeagues} />
            {leagues.map(comp => (
              <CompetitionCard key={comp.competition_id} comp={comp} />
            ))}
          </div>
        </div>
      )}

      {cups.length > 0 && (
        <div>
          <p className="text-xs text-muted uppercase tracking-widest mb-4">International</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {cups.map(comp => (
              <CompetitionCard key={comp.competition_id} comp={comp} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function CompetitionCard({ comp }) {
  const id = comp.competition_id

  return (
    <Link
      to={`/standings/${id}`}
      className="flex items-center gap-3 px-4 py-4 rounded-xl bg-surface border border-border
                 hover:bg-surface-hover hover:border-white/10 transition-all group"
    >
      <img
        src={LEAGUE_LOGOS[id] || '/assets/logo/default.png'}
        alt={comp.name}
        className="w-7 h-7 object-contain opacity-80 group-hover:opacity-100 transition-opacity"
      />
      <span className="font-semibold text-sm text-white/90 group-hover:text-white transition-colors">
        {comp.name}
      </span>
    </Link>
  )
}