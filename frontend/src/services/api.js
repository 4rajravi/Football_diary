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
