import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
})

export async function getCompetitions() {
  const { data } = await api.get('/api/competitions')
  return data.competitions
}

export async function getSeasons(competitionId) {
  const { data } = await api.get(`/api/seasons/${competitionId}`)
  return data.seasons
}

export async function getStandings(competitionId, season, stage = 'all') {
  const { data } = await api.get(`/api/standings/${competitionId}/${season}?stage=${stage}`)
  return data
}

export async function getTopScorers(competitionId, season) {
  const { data } = await api.get(`/api/top-scorers/${competitionId}/${season}`)
  return data.top_scorers
}

export async function sendChatMessage(message, history = []) {
  const { data } = await api.post('/api/chat', { message, history })
  return data
}

export async function refreshData() {
  const { data } = await api.post('/api/admin/refresh')
  return data
}

export async function getRounds(competitionId, season) {
  const { data } = await api.get(`/api/rounds/${competitionId}/${season}`)
  return data.rounds
}

export async function getHealth() {
  const { data } = await api.get('/api/admin/health')
  return data
}

export async function getMatches(competitionId, season, limit = 500, offset = 0) {
  const { data } = await api.get(`/api/matches/${competitionId}/${season}?limit=${limit}&offset=${offset}`)
  return data.matches
}

export async function getMatchDetail(gameId) {
  const { data } = await api.get(`/api/match/${gameId}`)
  return data
}

export async function getStats(competitionId, season, statType, team = 'all') {
  const { data } = await api.get(`/api/stats/${competitionId}/${season}?stat_type=${statType}&team=${encodeURIComponent(team)}`)
  return data.stats
}

export async function searchPlayers(query) {
  const { data } = await api.get(`/api/players/search?q=${encodeURIComponent(query)}`)
  return data.players
}

export async function getPlayerStats(playerId, season = 'all') {
  const { data } = await api.get(`/api/players/${playerId}/stats?season=${season}`)
  return data
}

export async function getTopPlayers(season = 'all') {
  const { data } = await api.get(`/api/players/top?season=${season}`)
  return data.players
}