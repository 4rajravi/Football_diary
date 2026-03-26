import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getStandings, getTopScorers, getSeasons, getRounds } from '../services/api'

const CUP_COMPETITIONS = ['CL', 'EL', 'WC', 'EURO']

export default function StandingsPage() {
  const { competitionId } = useParams()
  const [seasons, setSeasons] = useState([])
  const [season, setSeason] = useState(null)
  const [standings, setStandings] = useState([])
  const [scorers, setScorers] = useState([])
  const [tab, setTab] = useState('standings')
  const [loading, setLoading] = useState(true)
  const [groups, setGroups] = useState([])
  const [selectedStage, setSelectedStage] = useState('all')
  const [knockout, setKnockout] = useState([])
  const isCup = CUP_COMPETITIONS.includes(competitionId)
  useEffect(() => {
    getSeasons(competitionId).then(s => {
      setSeasons(s)
      if (s.length > 0) setSeason(s[0])
    })
  }, [competitionId])

  useEffect(() => {
    if (!season) return
    if (isCup) {
      getRounds(competitionId, season).then(rounds => {
        const grps = rounds.filter(r => r && r.startsWith('Group'))
        setGroups([...new Set(grps)].sort())
        if (grps.length > 0) setSelectedStage(grps[0])
        else setSelectedStage('knockout')
      })
    } else {
      setSelectedStage('all')
      setGroups([])
    }
  }, [competitionId, season])

  useEffect(() => {
    if (!season || !selectedStage) return
    setLoading(true)

    const promises = [getTopScorers(competitionId, season)]

    if (selectedStage === 'knockout') {
      promises.push(getStandings(competitionId, season, 'knockout'))
    } else {
      promises.push(getStandings(competitionId, season, selectedStage))
    }

    Promise.all(promises)
      .then(([sc, data]) => {
        setScorers(sc)
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
  }, [competitionId, season, selectedStage])

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header with season picker */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{competitionId}</h1>
        <select
          value={season || ''}
          onChange={e => setSeason(Number(e.target.value))}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm
                     focus:outline-none focus:border-white/30"
        >
          {seasons.map(s => (
            <option key={s} value={s} className="bg-pitch">
              {s}/{(Number(s) + 1).toString().slice(-2)}
            </option>
          ))}
        </select>
      </div>

      {/* Tabs */}
      {/* Stage selector for cups */}
      {isCup && (
        <div className="flex gap-2 mb-4 flex-wrap">
          {groups.map(g => (
            <button
              key={g}
              onClick={() => setSelectedStage(g)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                selectedStage === g ? 'bg-white/15 text-white' : 'bg-white/5 text-white/40 hover:text-white'
              }`}
            >
              {g}
            </button>
          ))}
          <button
            onClick={() => setSelectedStage('knockout')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedStage === 'knockout' ? 'bg-white/15 text-white' : 'bg-white/5 text-white/40 hover:text-white'
            }`}
          >
            Knockout
          </button>
        </div>
      )}

      {/* Tabs */}
      {/* Stage selector for cups */}
      {isCup && (
        <div className="flex gap-2 mb-4 flex-wrap">
          {groups.map(g => (
            <button
              key={g}
              onClick={() => setSelectedStage(g)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                selectedStage === g ? 'bg-white/15 text-white' : 'bg-white/5 text-white/40 hover:text-white'
              }`}
            >
              {g}
            </button>
          ))}
          <button
            onClick={() => setSelectedStage('knockout')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedStage === 'knockout' ? 'bg-white/15 text-white' : 'bg-white/5 text-white/40 hover:text-white'
            }`}
          >
            Knockout
          </button>
        </div>
      )}

      {/* Tabs */}
      {/* Stage selector for cups */}
      {isCup && (
        <div className="flex gap-2 mb-4 flex-wrap">
          {groups.map(g => (
            <button
              key={g}
              onClick={() => setSelectedStage(g)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                selectedStage === g ? 'bg-white/15 text-white' : 'bg-white/5 text-white/40 hover:text-white'
              }`}
            >
              {g}
            </button>
          ))}
          <button
            onClick={() => setSelectedStage('knockout')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedStage === 'knockout' ? 'bg-white/15 text-white' : 'bg-white/5 text-white/40 hover:text-white'
            }`}
          >
            Knockout
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-white/5 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab('standings')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'standings' ? 'bg-white/10 text-white' : 'text-white/50 hover:text-white'
          }`}
        >
          {selectedStage === 'knockout' ? 'Results' : 'Standings'}
        </button>
        <button
          onClick={() => setTab('scorers')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'scorers' ? 'bg-white/10 text-white' : 'text-white/50 hover:text-white'
          }`}
        >
          Top Scorers
        </button>
      </div>

      {loading ? (
        <div className="text-white/40 animate-pulse py-20 text-center">Loading...</div>
      ) : tab === 'standings' ? (
        selectedStage === 'knockout' ? (
          <KnockoutTable data={knockout} />
        ) : (
          <StandingsTable data={standings} />
        )
      ) : (
        <ScorersTable data={scorers} />
      )}
    </div>
  )
}

function StandingsTable({ data }) {
  if (!data.length) return <p className="text-white/40">No standings data available.</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-white/40 text-xs uppercase border-b border-white/10">
            <th className="text-left py-3 px-2 w-8">#</th>
            <th className="text-left py-3 px-2">Club</th>
            <th className="text-center py-3 px-2">P</th>
            <th className="text-center py-3 px-2">W</th>
            <th className="text-center py-3 px-2">D</th>
            <th className="text-center py-3 px-2">L</th>
            <th className="text-center py-3 px-2">GF</th>
            <th className="text-center py-3 px-2">GA</th>
            <th className="text-center py-3 px-2">GD</th>
            <th className="text-center py-3 px-2 font-semibold">Pts</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={row.club_id}
              className="border-b border-white/5 hover:bg-white/5 transition-colors"
            >
              <td className="py-3 px-2 text-white/50">{i + 1}</td>
              <td className="py-3 px-2 font-medium">{row.club_name}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.played}</td>
              <td className="text-center py-3 px-2 text-green-400">{row.wins}</td>
              <td className="text-center py-3 px-2 text-white/50">{row.draws}</td>
              <td className="text-center py-3 px-2 text-red-400">{row.losses}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.goals_for}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.goals_against}</td>
              <td className="text-center py-3 px-2">
                <span className={row.goal_difference > 0 ? 'text-green-400' : row.goal_difference < 0 ? 'text-red-400' : 'text-white/50'}>
                  {row.goal_difference > 0 ? '+' : ''}{row.goal_difference}
                </span>
              </td>
              <td className="text-center py-3 px-2 font-bold text-gold">{row.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ScorersTable({ data }) {
  if (!data.length) return <p className="text-white/40">No scorer data available.</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-white/40 text-xs uppercase border-b border-white/10">
            <th className="text-left py-3 px-2 w-8">#</th>
            <th className="text-left py-3 px-2">Player</th>
            <th className="text-left py-3 px-2">Club</th>
            <th className="text-center py-3 px-2">Apps</th>
            <th className="text-center py-3 px-2 font-semibold">Goals</th>
            <th className="text-center py-3 px-2">Assists</th>
            <th className="text-center py-3 px-2">Mins</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={`${row.player_id}-${i}`}
              className="border-b border-white/5 hover:bg-white/5 transition-colors"
            >
              <td className="py-3 px-2 text-white/50">{i + 1}</td>
              <td className="py-3 px-2 font-medium">{row.player_name}</td>
              <td className="py-3 px-2 text-white/60">{row.club_name}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.appearances}</td>
              <td className="text-center py-3 px-2 font-bold text-gold">{row.goals}</td>
              <td className="text-center py-3 px-2 text-white/60">{row.assists}</td>
              <td className="text-center py-3 px-2 text-white/40">{row.minutes_played}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function KnockoutTable({ data }) {
  if (!data.length) return <p className="text-white/40">No knockout data available.</p>

  const rounds = [...new Set(data.map(r => r.round))]

  return (
    <div className="space-y-6">
      {rounds.map(round => (
        <div key={round}>
          <h3 className="text-sm font-medium text-white/50 uppercase tracking-wider mb-3">{round}</h3>
          <div className="space-y-2">
            {data.filter(r => r.round === round).map((match, i) => (
              <div key={i} className="flex items-center gap-3 bg-white/5 rounded-lg px-4 py-3 text-sm">
                <span className="flex-1 text-right font-medium">{match.home_club_name}</span>
                <span className="px-3 py-1 bg-white/10 rounded font-bold text-gold min-w-[48px] text-center">
                  {match.home_club_goals} - {match.away_club_goals}
                </span>
                <span className="flex-1 font-medium">{match.away_club_name}</span>
                {match.aggregate && (
                  <span className="text-white/30 text-xs">agg: {match.aggregate}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}