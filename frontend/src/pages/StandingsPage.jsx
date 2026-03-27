import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getStandings, getTopScorers, getSeasons, getRounds, getCompetitions, getMatches, getMatchDetail } from '../services/api'
import { ChevronDown, ExternalLink } from 'lucide-react'

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

  const [matches, setMatches] = useState([])
  const [allMatches, setAllMatches] = useState([])
  const [matchFilterTeam, setMatchFilterTeam] = useState('all')
  const [matchFilterRound, setMatchFilterRound] = useState('all')

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

  useEffect(() => {
    if (!season || view !== 'matches') return
    setLoading(true)
    setMatchFilterTeam('all')
    setMatchFilterRound('all')
    getMatches(competitionId, season)
      .then(data => {
        setAllMatches(data)
        setMatches(data)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [competitionId, season, view])

  useEffect(() => {
    let filtered = allMatches
    if (matchFilterTeam !== 'all') {
      filtered = filtered.filter(m =>
        m.home_club_name === matchFilterTeam || m.away_club_name === matchFilterTeam
      )
    }
    if (matchFilterRound !== 'all') {
      filtered = filtered.filter(m => m.round === matchFilterRound)
    }
    setMatches(filtered)
  }, [matchFilterTeam, matchFilterRound, allMatches])

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
          <option value="matches" className="bg-[#0a0a0a]">Matches</option>
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
      ) : view === 'matches' ? (
        <>
          <div className="flex gap-3 mb-6">
            <select
              value={matchFilterRound}
              onChange={e => setMatchFilterRound(e.target.value)}
              className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/20 cursor-pointer"
            >
              <option value="all" className="bg-[#0a0a0a]">All Rounds</option>
              {[...new Set(allMatches.map(m => m.round).filter(Boolean))].map(r => (
                <option key={r} value={r} className="bg-[#0a0a0a]">{r}</option>
              ))}
            </select>
            <select
              value={matchFilterTeam}
              onChange={e => setMatchFilterTeam(e.target.value)}
              className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/20 cursor-pointer"
            >
              <option value="all" className="bg-[#0a0a0a]">All Teams</option>
              {[...new Set(allMatches.flatMap(m => [m.home_club_name, m.away_club_name]).filter(Boolean))].sort().map(t => (
                <option key={t} value={t} className="bg-[#0a0a0a]">{t}</option>
              ))}
            </select>
          </div>
          <MatchesList data={matches} />
        </>
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

function MatchesList({ data }) {
  if (!data.length) return <p className="text-muted text-sm">No matches available.</p>

  // Group by round
  const grouped = data.reduce((acc, match) => {
    const round = match.round || 'Unknown'
    if (!acc[round]) acc[round] = []
    acc[round].push(match)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([round, matches]) => (
        <div key={round}>
          <p className="text-xs text-muted uppercase tracking-widest mb-3">{round}</p>
          <div className="bg-surface border border-border rounded-xl overflow-hidden divide-y divide-border/50">
            {matches.map(match => (
              <MatchCard key={match.game_id} match={match} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function MatchCard({ match }) {
  const [expanded, setExpanded] = useState(false)
  const [detail, setDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const handleExpand = () => {
    if (!expanded && !detail) {
      setLoadingDetail(true)
      getMatchDetail(match.game_id)
        .then(setDetail)
        .catch(console.error)
        .finally(() => setLoadingDetail(false))
    }
    setExpanded(!expanded)
  }

  const ytQuery = `${match.home_club_name} vs ${match.away_club_name} ${match.date} highlights`
  const ytLink = `https://www.youtube.com/results?search_query=${encodeURIComponent(ytQuery)}`

  return (
    <div>
      <div
        onClick={handleExpand}
        className="flex items-center gap-3 px-5 py-3.5 text-sm hover:bg-surface-hover transition-colors cursor-pointer"
      >
        <span className="text-muted text-xs w-20 shrink-0">{match.date}</span>
        <span className="flex-1 text-right font-medium text-white">{match.home_club_name}</span>
        <span className="px-3 py-1 bg-white/5 border border-border rounded font-bold text-gold min-w-[52px] text-center text-xs">
          {match.home_club_goals} – {match.away_club_goals}
        </span>
        <span className="flex-1 font-medium text-white">{match.away_club_name}</span>
        <ChevronDown
          size={14}
          className={`text-muted transition-transform ${expanded ? 'rotate-180' : ''}`}
        />
      </div>

      {expanded && (
        <div className="px-5 pb-4 animate-fade-in">
          {/* Match info */}
          <div className="flex gap-4 text-xs text-muted mb-4 pl-20">
            {match.stadium && <span>{match.stadium}</span>}
            {match.attendance && <span>Att: {Number(match.attendance).toLocaleString()}</span>}
            {match.referee && <span>Ref: {match.referee}</span>}
          </div>

          {loadingDetail ? (
            <div className="text-muted text-xs py-4 text-center">Loading lineups...</div>
          ) : detail ? (
            <>
              {/* Events timeline */}
              {detail.events && detail.events.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-muted uppercase tracking-widest mb-2">Match Events</p>
                  <div className="bg-white/[0.02] border border-border/50 rounded-lg divide-y divide-border/30">
                    {detail.events.map((ev, i) => (
                      <EventRow key={i} event={ev} homeClubId={detail.match.home_club_id} />
                    ))}
                  </div>
                </div>
              )}

              {/* Lineups */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-xs text-muted uppercase tracking-widest mb-2">
                    {detail.match.home_club_name}
                  </p>
                  <LineupList players={detail.home_lineup} goals={detail.player_goals} assists={detail.player_assists} />
                </div>
                <div>
                  <p className="text-xs text-muted uppercase tracking-widest mb-2">
                    {detail.match.away_club_name}
                  </p>
                  <LineupList players={detail.away_lineup} goals={detail.player_goals} assists={detail.player_assists} />
                </div>
              </div>
            </>
          ) : null}

          {/* YouTube highlights link */}
          
            <a href={ytLink} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-xs text-muted hover:text-white transition-colors mt-2">
            <ExternalLink size={12} />
            Watch highlights on YouTube
          </a>
        </div>
      )}
    </div>
  )
}

function EventRow({ event, homeClubId }) {
  const isHome = event.club_id === homeClubId
  const minute = event.minute ? `${event.minute}'` : ''

  const cardDesc = event.description?.toLowerCase() || ''
  const icon = event.type === 'Goals' ? '⚽'
    : event.type === 'Cards'
      ? (cardDesc.includes('second yellow') || cardDesc.includes('yellow-red')
        ? '🟨🟥'
        : cardDesc.includes('red') ? '🟥' : '🟨')
    : event.type === 'Substitutions' ? '🔄'
    : '•'

  let desc = ''
  if (event.type === 'Goals') {
    desc = event.player_name || 'Goal'
    if (event.assist_player_name) desc += ` (${event.assist_player_name})`
  } else if (event.type === 'Cards') {
    const d = event.description?.toLowerCase() || ''
    const cardType = d.includes('second yellow') || d.includes('yellow-red')
      ? 'Second Yellow → Red'
      : d.includes('red')
      ? 'Red'
      : 'Yellow'
    const cardIcon2 = d.includes('second yellow') || d.includes('yellow-red') ? '🟨🟥' : null
    desc = `${event.player_name || 'Unknown'} · ${cardType}`
  } else if (event.type === 'Substitutions') {
    const inPlayer = event.player_in_name || '?'
    const outPlayer = event.player_name || '?'
    const reason = event.description?.toLowerCase().includes('injur') ? ' (injury)' : ''
    desc = `${inPlayer} ↔ ${outPlayer}${reason}`
  } else {
    desc = event.player_name || event.description || event.type
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 text-xs ${isHome ? '' : 'flex-row-reverse text-right'}`}>
      <span className="text-muted w-8 shrink-0 text-center">{minute}</span>
      <span>{icon}</span>
      <span className="text-white/80">{desc}</span>
    </div>
  )
}

function LineupList({ players, goals = {}, assists = {} }) {
  if (!players || !players.length) return <p className="text-muted text-xs">No lineup data</p>

  const starters = players.filter(p => p.type === 'starting_lineup')
  const subs = players.filter(p => p.type !== 'starting_lineup')

  const badges = (playerId) => {
    const g = goals[playerId] || 0
    const a = assists[playerId] || 0
    if (!g && !a) return null
    return (
      <span className="ml-1.5 inline-flex gap-0.5">
        {Array.from({ length: g }).map((_, i) => (
          <span key={`g${i}`} className="text-[10px]">⚽</span>
        ))}
        {Array.from({ length: a }).map((_, i) => (
          <span key={`a${i}`} className="text-emerald-400 text-[10px] font-bold">A</span>
        ))}
      </span>
    )
  }

  return (
    <div className="space-y-1">
      {starters.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="text-muted w-5 text-right">{p.number || ''}</span>
          <span className="text-white">
            {p.player_name}
            {p.team_captain === '1' && <span className="text-gold ml-1">(C)</span>}
            {badges(p.player_id)}
          </span>
          {p.position && <span className="text-muted">{p.position}</span>}
        </div>
      ))}
      {subs.length > 0 && (
        <>
          <p className="text-[10px] text-muted uppercase tracking-widest pt-2">Substitutes</p>
          {subs.map((p, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className="text-muted w-5 text-right">{p.number || ''}</span>
              <span className="text-white/50">
                {p.player_name}
                {badges(p.player_id)}
              </span>
            </div>
          ))}
        </>
      )}
    </div>
  )
}