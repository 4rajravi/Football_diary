# Football Diary ⚽

A visually appealing football analytics platform powered by an AI chat agent.
Users explore match history, player stats, and club records through natural language
queries — the AI agent generates answers with auto-rendered charts inline.

## Tech Stack (Zero-Cost)

| Layer       | Technology            | Cost   |
|-------------|----------------------|--------|
| LLM         | Groq (Llama 3.3 70B) | Free   |
| Database    | SQLite               | Free   |
| Backend     | FastAPI (Python)     | Free   |
| Frontend    | React + Tailwind CSS | Free   |
| Charts      | Recharts             | Free   |
| Hosting BE  | Render free tier     | Free   |
| Hosting FE  | Vercel free tier     | Free   |
| Data Source  | transfermarkt-datasets (GitHub/Kaggle) | Free |


## Data Source

Uses [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets)
by dcaribou — 10 relational CSV tables, ~68K games, ~30K players, ~1.5M appearances,
refreshed weekly.

### Tables Used

| Table              | Rows     | Key Columns                                           |
|--------------------|----------|-------------------------------------------------------|
| competitions       | ~40      | competition_id, name, type, country_name              |
| clubs              | ~400     | club_id, name, stadium_name, squad_size               |
| players            | ~30,000  | player_id, name, position, market_value_in_eur        |
| games              | ~68,000  | game_id, home/away_club_id, home/away_club_goals, date|
| appearances        | ~1.5M   | player_id, game_id, goals, assists, minutes_played    |
| player_valuations  | ~400K   | player_id, date, market_value_in_eur                  |
| club_games         | ~136K   | club_id, game_id, own_goals, opponent_goals, is_win   |
| game_events        | ~500K   | game_id, player_id, type (Goals/Cards/Substitutions)  |
| game_lineups       | ~1M+    | game_id, player_id, type (starting/substitutes)       |
| transfers          | ~100K   | player_id, from/to_club_id, transfer_fee              |

### Competitions Covered

- **Top 5 Leagues**: Premier League, La Liga, Bundesliga, Serie A, Ligue 1
- **European Cups**: Champions League, Europa League
- **International**: FIFA World Cup, UEFA European Championship

## Database Design

### Layer 1 — Raw Tables
Direct mirrors of the 10 CSVs. No transformations. Schema in `backend/app/models/schema.sql`.

### Layer 2 — Indexes
Optimized for the AI agent's most common query patterns (JOIN on game_id, player_id, club_id, filtering by competition_id and season).

### Layer 3 — Derived Views
Pre-computed analytics that the agent (and the UI) can query directly:

| View                   | Purpose                                         |
|------------------------|------------------------------------------------ |
| `v_head_to_head`       | Club vs club record across all competitions     |
| `v_player_season_stats`| Per-90 stats, goal contributions per season     |
| `v_player_impact`      | Win rate when starting vs coming off bench      |
| `v_club_form`          | Recent results per club (W/D/L sequence)        |
| `v_standings`          | League table (points, GD, GF, GA)               |
| `v_top_scorers`        | Goals + assists ranking per competition/season  |

### Layer 4 — ETL Metadata
`_etl_metadata` table tracks every data load: row counts, checksums, timestamps, success/failure status. Powers the admin health dashboard.

## AI Agent Architecture

The agent uses **Groq (Llama 3.3 70B)** with tool-use / function calling.

### Flow:
1. User asks: "Compare Messi vs Ronaldo in Champions League"
2. Backend receives message at `POST /api/chat`
3. Agent receives the question + database schema context
4. Agent decides which SQL queries to run (tool calls)
5. Backend executes SQL against SQLite, returns results
6. Agent interprets results and generates:
   - Natural language answer
   - Chart configuration (type, data, labels)
7. Frontend renders the text + chart inline in the chat

### Agent Tools:
- `execute_sql(query)` — Run a read-only SQL query against the database
- `get_schema()` — Return table/view names and columns for context
- `get_competitions()` — List available competitions and seasons

### Chart Types the Agent Can Request:
- Bar chart (comparisons, rankings)
- Line chart (trends over time, market value history)
- Horizontal bar (top N lists)
- Table (detailed stats)

## ETL Pipeline

### Single-Click Refresh:
`POST /api/admin/refresh` triggers:
1. **Download** — Fetch latest CSVs from GitHub (gzipped R2 URLs)
2. **Validate** — Check row counts, null rates, schema consistency
3. **Backup** — Copy current .db file before overwriting
4. **Load** — Bulk insert CSVs into SQLite tables
5. **Rebuild** — Views are auto-refreshed (they're virtual)
6. **Log** — Write to _etl_metadata with status and counts

### Health Check:
`GET /api/admin/health` returns last refresh time, row counts, and staleness indicator.

## Setup & Run

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API key (free at console.groq.com)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GROQ_API_KEY
python -m app.etl.pipeline  # initial data load
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Docker (full stack)
```bash
docker-compose up --build
```

## Deployment

- **Backend**: Render.com free tier (Web Service, Docker)
- **Frontend**: Vercel (auto-deploy from GitHub)
- **Database**: SQLite file bundled with backend container
  - On Render, use a persistent disk ($0.25/GB/month for 1GB)
    OR use Turso (SQLite edge DB, free tier = 9GB storage)

