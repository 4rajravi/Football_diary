import { useState, useEffect } from 'react'
import { Search } from 'lucide-react'
import { searchPlayers, getPlayerStats, getTopPlayers } from '../services/api'

export default function IndividualPage() {
  const [tab, setTab] = useState('search')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selectedPlayer, setSelectedPlayer] = useState(null)
  const [playerData, setPlayerData] = useState(null)
  const [playerSeason, setPlayerSeason] = useState('all')
  const [loadingProfile, setLoadingProfile] = useState(false)

  // Top players state
  const [topPlayers, setTopPlayers] = useState([])
  const [topSeason, setTopSeason] = useState('all')
  const [loadingTop, setLoadingTop] = useState(false)

  // Search
  useEffect(() => {
    if (query.length < 1) { setResults([]); return }
    const timer = setTimeout(() => {
      searchPlayers(query).then(setResults).catch(console.error)
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  // Load player profile
  useEffect(() => {
    if (!selectedPlayer) return
    setLoadingProfile(true)
    getPlayerStats(selectedPlayer, playerSeason)
      .then(setPlayerData)
      .catch(console.error)
      .finally(() => setLoadingProfile(false))
  }, [selectedPlayer, playerSeason])

  // Load top players
  useEffect(() => {
    if (tab !== 'top') return
    setLoadingTop(true)
    getTopPlayers(topSeason)
      .then(setTopPlayers)
      .catch(console.error)
      .finally(() => setLoadingTop(false))
  }, [tab, topSeason])

  const handleSelectPlayer = (player) => {
    setSelectedPlayer(player.player_id)
    setPlayerSeason('all')
    setQuery('')
    setResults([])
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold mb-8">Individual</h1>

      {/* Tabs */}
      <div className="flex gap-3 mb-6">
        <select
          value={tab}
          onChange={e => { setTab(e.target.value); setSelectedPlayer(null); setPlayerData(null) }}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/20 cursor-pointer"
        >
          <option value="search" className="bg-[#0a0a0a]">Search Player</option>
          <option value="top" className="bg-[#0a0a0a]">Top Players</option>
        </select>

        {tab === 'top' && (
          <select
            value={topSeason}
            onChange={e => setTopSeason(e.target.value)}
            className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/20 cursor-pointer"
          >
            <option value="all" className="bg-[#0a0a0a]">All Time</option>
            {Array.from({ length: 14 }, (_, i) => 2025 - i).map(y => (
              <option key={y} value={y} className="bg-[#0a0a0a]">{y}/{(y + 1).toString().slice(-2)}</option>
            ))}
          </select>
        )}
      </div>

      {tab === 'search' && !selectedPlayer && (
        <div>
          {/* Search input */}
          <div className="relative mb-4">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search player name..."
              className="w-full bg-surface border border-border rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder:text-muted focus:outline-none focus:border-white/20"
            />
          </div>

          {/* Results */}
          {results.length > 0 && (
            <div className="bg-surface border border-border rounded-xl overflow-hidden divide-y divide-border/50 max-h-[400px] overflow-y-auto">
              {results.map(p => (
                <div
                  key={p.player_id}
                  onClick={() => handleSelectPlayer(p)}
                  className="flex items-center justify-between px-4 py-3 hover:bg-surface-hover cursor-pointer transition-colors"
                >
                  <div>
                    <span className="text-sm font-medium text-white">{p.name}</span>
                    {p.position && <span className="text-xs text-muted ml-2">{p.position}</span>}
                  </div>
                  <div className="text-xs text-muted">
                    {p.current_club && <span>{p.current_club}</span>}
                    {p.country_of_citizenship && <span className="ml-2">{p.country_of_citizenship}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'search' && selectedPlayer && (
        <div>
          <button
            onClick={() => { setSelectedPlayer(null); setPlayerData(null) }}
            className="text-xs text-muted hover:text-white mb-4 transition-colors"
          >
            ← Back to search
          </button>

          {loadingProfile ? (
            <div className="text-muted text-sm py-20 text-center">Loading player profile...</div>
          ) : playerData ? (
            <PlayerProfile data={playerData} season={playerSeason} onSeasonChange={setPlayerSeason} />
          ) : null}
        </div>
      )}

      {tab === 'top' && (
        loadingTop ? (
          <div className="text-muted text-sm py-20 text-center">Loading...</div>
        ) : (
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
                {topPlayers.map((p, i) => (
                  <tr
                    key={p.player_id}
                    className="border-b border-border/50 last:border-0 hover:bg-surface-hover transition-colors cursor-pointer"
                    onClick={() => { setTab('search'); handleSelectPlayer(p) }}
                  >
                    <td className="py-3 px-4 text-muted">{i + 1}</td>
                    <td className="py-3 px-4 font-medium text-white">{p.player_name}</td>
                    <td className="py-3 px-4 text-white/50">{p.current_club}</td>
                    <td className="text-center py-3 px-2 text-white/60">{p.appearances}</td>
                    <td className="text-center py-3 px-2 font-bold text-gold">{p.goals}</td>
                    <td className="text-center py-3 px-2 text-white/60">{p.assists}</td>
                    <td className="text-center py-3 px-4 text-white/40">{p.minutes_played}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  )
}

const COMP_NAMES = {
  GB1: 'Premier League', ES1: 'La Liga', L1: 'Bundesliga', IT1: 'Serie A', FR1: 'Ligue 1',
  CL: 'Champions League', EL: 'Europa League',
  UCOL: 'Conference League', CLQ: 'UCL Qualifying', ELQ: 'UEL Qualifying',
}

function PlayerProfile({ data, season, onSeasonChange }) {
  const { player, stats, seasons } = data

  return (
    <div>
      {/* Player header */}
      <div className="bg-surface border border-border rounded-xl p-5 mb-6">
        <h2 className="text-lg font-bold text-white">{player.name}</h2>
        <div className="flex gap-4 text-xs text-muted mt-2 flex-wrap">
          {player.position && <span>{player.position}</span>}
          {player.current_club && <span>{player.current_club}</span>}
          {player.country_of_citizenship && <span>{player.country_of_citizenship}</span>}
          {player.date_of_birth && <span>Born: {player.date_of_birth}</span>}
          {player.foot && <span>Foot: {player.foot}</span>}
          {player.height_in_cm && <span>{player.height_in_cm}cm</span>}
        </div>
      </div>

      {/* Season selector */}
      <div className="flex gap-3 mb-6">
        <select
          value={season}
          onChange={e => onSeasonChange(e.target.value)}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-white/20 cursor-pointer"
        >
          <option value="all" className="bg-[#0a0a0a]">Overall</option>
          {seasons.map(s => (
            <option key={s} value={s} className="bg-[#0a0a0a]">{s}/{(Number(s) + 1).toString().slice(-2)}</option>
          ))}
        </select>
      </div>

      {/* Stats table */}
      {stats.length > 0 ? (
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted text-xs uppercase border-b border-border">
                <th className="text-left py-3 px-4">Competition</th>
                <th className="text-left py-3 px-4">Club</th>
                <th className="text-center py-3 px-2">Apps</th>
                <th className="text-center py-3 px-2 font-semibold">Goals</th>
                <th className="text-center py-3 px-2">Assists</th>
                <th className="text-center py-3 px-4">Mins</th>
              </tr>
            </thead>
            <tbody>
              {stats.map((s, i) => (
                <tr key={i} className="border-b border-border/50 last:border-0 hover:bg-surface-hover transition-colors">
                  <td className="py-3 px-4 font-medium text-white">{COMP_NAMES[s.competition_id] || s.competition_id}</td>
                  <td className="py-3 px-4 text-white/50">{s.club_name}</td>
                  <td className="text-center py-3 px-2 text-white/60">{s.appearances}</td>
                  <td className="text-center py-3 px-2 font-bold text-gold">{s.goals}</td>
                  <td className="text-center py-3 px-2 text-white/60">{s.assists}</td>
                  <td className="text-center py-3 px-4 text-white/40">{s.minutes_played}</td>
                </tr>
              ))}
              {/* Totals row */}
              <tr className="border-t border-border bg-white/[0.02]">
                <td className="py-3 px-4 font-bold text-white" colSpan={2}>Total</td>
                <td className="text-center py-3 px-2 font-bold text-white">{stats.reduce((s, r) => s + (Number(r.appearances) || 0), 0)}</td>
                <td className="text-center py-3 px-2 font-bold text-gold">{stats.reduce((s, r) => s + (Number(r.goals) || 0), 0)}</td>
                <td className="text-center py-3 px-2 font-bold text-white">{stats.reduce((s, r) => s + (Number(r.assists) || 0), 0)}</td>
                <td className="text-center py-3 px-4 font-bold text-white">{stats.reduce((s, r) => s + (Number(r.minutes_played) || 0), 0)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-muted text-sm">No stats available for this period.</p>
      )}
    </div>
  )
}