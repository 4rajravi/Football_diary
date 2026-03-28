# ⚽ Football Diary

A full-stack football analytics platform with an AI-powered chat agent. Explore match history, player stats, club records, and unique insights across Europe's top football competitions — powered by real data from [Transfermarkt](https://www.transfermarkt.com/).

> **Data coverage:** 2012/13 season onwards · Premier League, La Liga, Bundesliga, Serie A, Ligue 1, UEFA Champions League & Europa League · 68,000+ matches · 30,000+ players · 1.5M+ appearances

---

## Features

### Competition Hub
- **League Standings** with UCL qualification & relegation zone indicators
- **Cup Competitions** — UCL/UEL group stage tables and knockout bracket with computed two-leg aggregates
- **Season Selector** with an "Overall" mode that combines all-time records
- **All Leagues** view comparing top 5 European leagues side by side

### Match Center
- Browse matches by round or team with filters
- Expandable match cards showing lineups (starters + substitutes), match events timeline (goals ⚽, cards 🟨🟥, substitutions 🔄), and goal/assist badges on player names
- YouTube highlights link for every match

### Stats Engine (17 stat types)
- **Basic:** Top Scorers, Top Assists, Most Appearances, Most Minutes, Most Cards, Super Subs (impact off bench)
- **Per-90:** Goals/90, Assists/90, Contributions/90, Minutes per Goal — all using accurate `game_events` data with a 900-minute minimum
- **Advanced:** Player Win Rate (start vs bench), Goalkeeper Clean Sheets, Head-to-Head club records
- **Home/Away:** Home Record, Away Record, Top Scorers Home, Top Scorers Away
- Team filter on all stats

### Individual Player Profiles
- Search any player by name
- Season-by-season breakdown across all competitions (leagues + UCL/UEL)
- Overall career totals with a summary row
- Top Players ranking (all-time and per-season)

### AI Chat Agent
- Full-screen conversational interface powered by Groq (Llama 3.3 70B)
- Ask natural language questions: *"Compare Messi vs Ronaldo in Champions League"*, *"Who has the best goals per 90 this season?"*
- Agent queries the database via SQL tool-use and generates inline charts (bar, line, table)
- Data-only responses — no hallucination from training data

### Data Pipeline
- One-click data refresh from [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) (updated weekly)
- Dynamic table creation — automatically adapts when the source adds new columns
- Pre-computed `computed_player_stats` table with accurate goals/assists from `game_events`
- ETL health tracking with row counts, checksums, and timestamps

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Add your GROQ_API_KEY
python -m app.etl.pipeline      # Downloads data & builds database (~3 min)
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Docker

```bash
docker-compose up --build
```

---

## Data Architecture

### Source
[dcaribou/transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) — 10 CSV tables refreshed weekly from Transfermarkt.

### Database Layers

| Layer | Purpose |
|-------|---------|
| **Raw Tables** | 10 tables dynamically created from CSV headers (competitions, clubs, players, games, appearances, player_valuations, club_games, game_events, game_lineups, transfers) |
| **Indexes** | Optimized for JOIN-heavy queries on game_id, player_id, club_id, competition_id |
| **Views** | v_standings, v_top_scorers, v_head_to_head, v_player_season_stats, v_player_impact, v_club_form |
| **Computed Table** | `computed_player_stats` — pre-aggregated per player/club/competition/season with accurate goals & assists from game_events |

### Data Accuracy
- **Goals & Assists**: Sourced from `game_events` table (event-level data), not from `appearances` (which has known inconsistencies)
- **Minutes & Appearances**: Sourced from `appearances` table (only reliable source for playing time)
- **Per-90 Metrics**: Computed using game_events goals/assists ÷ appearances minutes × 90

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/competitions` | List competitions |
| `GET /api/seasons/{comp}` | Available seasons |
| `GET /api/standings/{comp}/{season}?stage=` | Standings (league, group, knockout) |
| `GET /api/stats/{comp}/{season}?stat_type=&team=` | 17 stat types with team filter |
| `GET /api/matches/{comp}/{season}` | Match list |
| `GET /api/match/{game_id}` | Match detail with lineups & events |
| `GET /api/rounds/{comp}/{season}` | Round names for cups |
| `GET /api/players/search?q=` | Player search |
| `GET /api/players/{id}/stats?season=` | Player profile |
| `GET /api/players/top?season=` | Top players ranking |
| `POST /api/chat` | AI agent query |
| `POST /api/admin/refresh` | Trigger data refresh |
| `GET /api/admin/health` | ETL status |

---

## Screenshots

![alt text](<Screenshot 2026-03-28 at 5.34.03 PM.png>) ![alt text](<Screenshot 2026-03-28 at 5.35.02 PM.png>) ![alt text](<Screenshot 2026-03-28 at 5.33.31 PM.png>) ![alt text](<Screenshot 2026-03-28 at 5.32.59 PM.png>)

---

## Known Limitations

- Data available from **2012/13 season** onwards only
- `appearances` table has occasional gaps for the current season (goals/assists use `game_events` as the source of truth instead)
- Player club names may show their last club in the dataset, not their current real-world club, for players who moved outside the top 5 leagues
- Own goals in the dataset are attributed to the scoring player, not distinguished from regular goals

---

## Data Source & License

Football data sourced from [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) by [dcaribou](https://github.com/dcaribou), originally scraped from [Transfermarkt](https://www.transfermarkt.com/). This project is for educational and portfolio purposes only — not for commercial use.

---

## Author

**Ravi Raj**
- M.Sc. Data Science — TU Hamburg (TUHH)
- [LinkedIn](https://linkedin.com/in/your-profile) · [GitHub](https://github.com/your-username)
