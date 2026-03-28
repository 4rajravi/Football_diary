import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import CompetitionsPage from './pages/CompetitionsPage'
import StandingsPage from './pages/StandingsPage'
import ChatPage from './pages/ChatPage'
import IndividualPage from './pages/IndividualPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<CompetitionsPage />} />
            <Route path="/standings/:competitionId" element={<StandingsPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/individual" element={<IndividualPage />} />
          </Routes>
        </main>
        <footer className="border-t border-border px-6 py-3 text-center">
          <p className="text-[11px] text-muted">
            Stats available from 2012/13 season onwards · Data covers Top 5 European Leagues, UEFA Champions League & Europa League only
          </p>
        </footer>
      </div>
    </BrowserRouter>
  )
}
