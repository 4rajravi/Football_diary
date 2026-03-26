import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getStandings, getTopScorers, getSeasons, getRounds, getCompetitions } from '../services/api'

const CUP_COMPETITIONS = ['CL', 'EL', 'FIWC', 'EURO']

const LEAGUE_LOGOS = {
  GB1: '/assets/logo/GB1.png', ES1: '/assets/logo/ES1.png', L1: '/assets/logo/L1.png',
  IT1: '/assets/logo/IT1.png', FR1: '/assets/logo/FR1.png', CL: '/assets/logo/CL.png',
  EL: '/assets/logo/EL.png', FIWC: '/assets/logo/WC.png', EURO: '/assets/logo/EURO.png',
}

export default function StandingsPage() {
  const { competitionId } = useParams()
  const [seasons, setSeasons] = useState([])
  const [season, setSeason] = useState(null)
  const [view, setView] = useState('standings')
  const [loading, setLoading] = useState(true)
  const isCup = CUP_COMPETITIONS.includes(competitionId)

  const [stages, setStages] = useState([])
  const [selectedStage, setSelectedStage] = useState('all')
  const [standings, setStandings] = useState([])
  const [knockout, setKnockout] = useState([])

  const [statType, setStatType] = useState('top_scorers')
  const [scorers, setScorers] = useState([])
  const [compName, setCompName] = useState(competitionId)

  useEffect(() => {
    getSeasons(competitionId).then(s => {
      setSeasons(s)
      if (s.length > 0) setSeason(s[0])
    })
    getCompetitions().then(comps => {
      const match = comps.find(c => c.competition_id === competitionId)
      if (match) setCompName(match.name)
    })
  }, [competitionId])

  useEffect(() => {
    if (!season) return
    if (isCup) {
      getRounds(competitionId, season).then(rounds => {
        const grps = [...new Set(rounds.filter(r => r && r.startsWith('Group')))].sort()
        const stageList = [...grps, 'knockout']
        setStages(stageList)
        setSelectedStage(grps.length > 0 ? grps[0] : 'knockout')
      })
    } else {
      setStages([])
      setSelectedStage('all')
    }
  }, [competitionId, season])

  useEffect(() => {
    if (!season || view !== 'standings' || !selectedStage) return
    setLoading(true)
    getStandings(competitionId, season, selectedStage)
      .then(data => {
        if (selectedStage === 'knockout') {
          setKnockout(data.knockout || [])
          setStandings([])
        } else {
          setStandings(data.standings || [])
          setKnockout([])
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [competitionId, season, selectedStage, view])

  useEffect(() => {
    if (!season || view !== 'stats') return
    setLoading(true)
    if (statType === 'top_scorers') {
      getTopScorers(competitionId, season)
        .then(setScorers)
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [competitionId, season, view, statType])

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <img
            src={LEAGUE_LOGOS[competitionId] || '/assets/logo/default.png'}
            alt={compName}
            className="w-8 h-8 object-contain"
          />
          <h1 className="text-xl font-bold">{compName}</h1>
        </div>
        <select
          value={season || ''}
          onChange={e => setSeason(e.target.value)}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white
                     focus:outline-none focus:border-white/20 cursor-pointer"
        >
          {seasons.map(s => (
            <option key={s} value={s} className="bg-[#0a0a0a]">
              {s}/{(Number(s) + 1).toString().slice(-2)}
            </option>
          ))}
        </select>
      </div>

      {/* Controls */}
      <div className="flex gap-3 mb-6">
        <select
          value={view}
          onChange={e => setView(e.target.value)}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white
                     focus:outline-none focus:border-white/20 cursor-pointer"
        >
          <option value="standings" className="bg-[#0a0a0a]">Standings</option>
          <option value="stats" className="bg-[#0a0a0a]">Stats</option>
        </select>

        {view === 'standings' && isCup && stages.length > 0 && (
          <select
            value={selectedStage}
            onChange={e => setSelectedStage(e.target.value)}
            className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white
                       focus:outline-none focus:border-white/20 cursor-pointer"
          >
            {stages.map(s => (
              <option key={s} value={s} className="bg-[#0a0a0a]">
                {s === 'knockout' ? 'Knockout Rounds' : s}
              </option>
            ))}
          </select>
        )}

        {view === 'stats' && (
          <select
            value={statType}
            onChange={e => setStatType(e.target.value)}
            className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white
                       focus:outline-none focus:border-white/20 cursor-pointer"
          >
            <option value="top_scorers" className="bg-[#0a0a0a]">Top Scorers</option>
          </select>
        )}
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-muted text-sm py-20 text-center">Loading...</div>
      ) : view === 'standings' ? (
        selectedStage === 'knockout' ? (
          <KnockoutTable data={knockout} />
        ) : (
          <StandingsTable data={standings} />
        )
      ) : (
        statType === 'top_scorers' && <ScorersTable data={scorers} />
      )}
    </div>
  )
}

function StandingsTable({ data }) {
  if (!data.length) return <p className="text-muted text-sm">No standings data available.</p>

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted text-xs uppercase border-b border-border">
            <th className="text-left py-3 px-4 w-8">#</th>
            <th className="text-left py-3 px-4">Club</th>
            <th className="text-center py-3 px-2">P</th>
            <th className="text-center py-3 px-2">W</th>
            <th className="text-center py-3 px-2">D</th>
            <th className="text-center py-3 px-2">L</th>
            <th className="text-center py-3 px-2">GF</th>
            <th className="text-center py-3 px-2">GA</th>
            <th className="text-center py-3 px-2">GD</th>
            <th className="text-center py-3 px-4 font-semibold">Pts</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={row.club_id} className="border-b border-border/50 last:border-0 hover:bg-surface-hover transition-colors">
              <td className="py-3 px-4 text-muted">{i + 1}</td>
              <td className="py-3 px-4 font-medium text-white">{row.club_name}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.played}</td>
              <td className="text-center py-3 px-2 text-emerald-400">{row.wins}</td>
              <td className="text-center py-3 px-2 text-white/40">{row.draws}</td>
              <td className="text-center py-3 px-2 text-red-400">{row.losses}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.goals_for}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.goals_against}</td>
              <td className="text-center py-3 px-2">
                <span className={row.goal_difference > 0 ? 'text-emerald-400' : row.goal_difference < 0 ? 'text-red-400' : 'text-white/30'}>
                  {row.goal_difference > 0 ? '+' : ''}{row.goal_difference}
                </span>
              </td>
              <td className="text-center py-3 px-4 font-bold text-gold">{row.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ScorersTable({ data }) {
  if (!data.length) return <p className="text-muted text-sm">No scorer data available.</p>

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted text-xs uppercase border-b border-border">
            <th className="text-left py-3 px-4 w-8">#</th>
            <th className="text-left py-3 px-4">Player</th>
            <th className="text-left py-3 px-4">Club</th>
            <th className="text-center py-3 px-2">Apps</th>
            <th className="text-center py-3 px-2 font-semibold">Goals</th>
            <th className="text-center py-3 px-2">Assists</th>
            <th className="text-center py-3 px-4">Mins</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={`${row.player_id}-${i}`} className="border-b border-border/50 last:border-0 hover:bg-surface-hover transition-colors">
              <td className="py-3 px-4 text-muted">{i + 1}</td>
              <td className="py-3 px-4 font-medium text-white">{row.player_name}</td>
              <td className="py-3 px-4 text-white/50">{row.club_name}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.appearances}</td>
              <td className="text-center py-3 px-2 font-bold text-gold">{row.goals}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.assists}</td>
              <td className="text-center py-3 px-4 text-white/40">{row.minutes_played}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function KnockoutTable({ data }) {
  if (!data.length) return <p className="text-muted text-sm">No knockout data available.</p>

  const rounds = [...new Set(data.map(r => r.round))]

  return (
    <div className="space-y-6">
      {rounds.map(round => (
        <div key={round}>
          <p className="text-xs text-muted uppercase tracking-widest mb-3">{round}</p>
          <div className="bg-surface border border-border rounded-xl overflow-hidden divide-y divide-border/50">
            {data.filter(r => r.round === round).map((match, i) => (
              <div key={i} className="flex items-center gap-3 px-5 py-3.5 text-sm hover:bg-surface-hover transition-colors">
                <span className="flex-1 text-right font-medium text-white">{match.home_club_name}</span>
                <span className="px-3 py-1 bg-white/5 border border-border rounded font-bold text-gold min-w-[52px] text-center text-xs">
                  {match.home_club_goals} – {match.away_club_goals}
                </span>
                <span className="flex-1 font-medium text-white">{match.away_club_name}</span>
                {match.aggregate && (
                  <span className="text-muted text-xs ml-2">agg {match.aggregate}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}