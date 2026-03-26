"""
Football Diary — FastAPI Backend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.database import execute_readonly
from app.agent.agent import chat as agent_chat
from app.config import TARGET_COMPETITIONS

app = FastAPI(title="Football Diary", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# COMPETITIONS & STANDINGS
# ------------------------------------------------------------------

@app.get("/api/competitions")
def list_competitions():
    """List all available competitions."""
    placeholders = ",".join(["?"] * len(TARGET_COMPETITIONS))
    rows = execute_readonly(
        f"SELECT * FROM competitions WHERE competition_id IN ({placeholders})",
        tuple(TARGET_COMPETITIONS),
    )
    return {"competitions": rows}


@app.get("/api/standings/{competition_id}/{season}")
def get_standings(competition_id: str, season: int, stage: str = "all"):
    """Get standings for a competition and season.
    stage: 'all' for leagues, 'Group A' etc for cup groups, 'knockout' for knockout results."""
    if stage == "knockout":
        rows = execute_readonly(
            """SELECT g.game_id, g.round, g.date, g.home_club_name, g.away_club_name,
                      g.home_club_goals, g.away_club_goals, g.home_club_id, g.away_club_id, g.stadium
               FROM games g
               WHERE g.competition_id = ? AND CAST(g.season AS TEXT) = ?
                 AND g.round NOT LIKE 'Group%'
                 AND g.round NOT LIKE 'Matchday%'
                 AND g.round NOT LIKE '%.%Spieltag%'
               ORDER BY g.date""",
            (competition_id, str(season)),
        )
        # Compute real aggregates by pairing 1st/2nd legs
        for row in rows:
            row["aggregate"] = None
            rnd = row.get("round", "")
            rnd_lower = rnd.lower()
            if "1st leg" in rnd_lower or "2nd leg" in rnd_lower:
                base_round = rnd_lower.replace("1st leg", "").replace("2nd leg", "").strip()
                home_id = row["home_club_id"]
                away_id = row["away_club_id"]
                # Find the other leg (teams are swapped)
                other = [r for r in rows
                         if r["game_id"] != row["game_id"]
                         and r.get("round", "").lower().replace("1st leg", "").replace("2nd leg", "").strip() == base_round
                         and r["home_club_id"] == away_id
                         and r["away_club_id"] == home_id]
                if other:
                    leg1_home = int(row["home_club_goals"] or 0)
                    leg1_away = int(row["away_club_goals"] or 0)
                    leg2_home = int(other[0]["home_club_goals"] or 0)
                    leg2_away = int(other[0]["away_club_goals"] or 0)
                    # Aggregate from home team's perspective in THIS row
                    agg_home = leg1_home + leg2_away
                    agg_away = leg1_away + leg2_home
                    row["aggregate"] = f"{agg_home}:{agg_away}"
        return {"knockout": rows, "competition_id": competition_id, "season": season}
    elif stage.startswith("Group"):
        rows = execute_readonly(
            """SELECT cg.club_id,
                      COALESCE(cl.name,
                        MAX(CASE WHEN g.home_club_id = cg.club_id THEN g.home_club_name ELSE NULL END),
                        MAX(CASE WHEN g.away_club_id = cg.club_id THEN g.away_club_name ELSE NULL END)
                      ) AS club_name,
                      COUNT(*) AS played,
                      SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS wins,
                      SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS draws,
                      SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) < CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS losses,
                      SUM(CAST(cg.own_goals AS INTEGER)) AS goals_for,
                      SUM(CAST(cg.opponent_goals AS INTEGER)) AS goals_against,
                      SUM(CAST(cg.own_goals AS INTEGER)) - SUM(CAST(cg.opponent_goals AS INTEGER)) AS goal_difference,
                      SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 3
                               WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1
                               ELSE 0 END) AS points
               FROM club_games cg
               JOIN games g ON cg.game_id = g.game_id
               LEFT JOIN clubs cl ON cg.club_id = cl.club_id
               WHERE g.competition_id = ? AND CAST(g.season AS TEXT) = ? AND g.round = ?
               GROUP BY cg.club_id, cl.name
               ORDER BY points DESC, goal_difference DESC, goals_for DESC""",
            (competition_id, str(season), stage),
        )
        return {"standings": rows, "competition_id": competition_id, "season": season, "stage": stage}
    else:
        rows = execute_readonly(
            """SELECT * FROM v_standings
               WHERE competition_id = ? AND CAST(season AS TEXT) = ?
               ORDER BY points DESC, goal_difference DESC, goals_for DESC""",
            (competition_id, str(season)),
        )
        return {"standings": rows, "competition_id": competition_id, "season": season}


@app.get("/api/top-scorers/{competition_id}/{season}")
def get_top_scorers(competition_id: str, season: int, limit: int = 20):
    """Get top scorers for a competition and season."""
    rows = execute_readonly(
        """SELECT * FROM v_top_scorers
           WHERE competition_id = ? AND season = ?
           ORDER BY goals DESC, assists DESC
           LIMIT ?""",
        (competition_id, season, limit),
    )
    return {"top_scorers": rows}

@app.get("/api/rounds/{competition_id}/{season}")
def get_rounds(competition_id: str, season: int):
    """Get distinct rounds for a competition/season."""
    rows = execute_readonly(
        """SELECT DISTINCT round FROM games
           WHERE competition_id = ? AND season = ?
           ORDER BY date""",
        (competition_id, str(season)),
    )
    return {"rounds": [r["round"] for r in rows if r["round"]]}

@app.get("/api/seasons/{competition_id}")
def get_seasons(competition_id: str):
    """List available seasons for a competition."""
    rows = execute_readonly(
        "SELECT DISTINCT season FROM games WHERE competition_id = ? ORDER BY season DESC",
        (competition_id,),
    )
    return {"seasons": [r["season"] for r in rows]}


# ------------------------------------------------------------------
# AI CHAT AGENT
# ------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    answer: str
    chart: dict | None = None


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """Send a message to the AI football analyst."""
    try:
        result = agent_chat(req.message, req.history)
        return ChatResponse(
            answer=result.get("answer", ""),
            chart=result.get("chart"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# ADMIN / ETL
# ------------------------------------------------------------------

@app.post("/api/admin/refresh")
def refresh_data():
    """Trigger a full data refresh (single-click update)."""
    from app.etl.pipeline import run_pipeline

    try:
        run_pipeline()
        return {"status": "success", "message": "Data refresh complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/health")
def health_check():
    """Return ETL status and data freshness."""
    try:
        meta = execute_readonly(
            """SELECT table_name, rows_loaded, loaded_at, status
               FROM _etl_metadata
               WHERE id IN (
                   SELECT MAX(id) FROM _etl_metadata GROUP BY table_name
               )
               ORDER BY loaded_at DESC"""
        )
        total_rows = sum(r["rows_loaded"] or 0 for r in meta)
        last_refresh = meta[0]["loaded_at"] if meta else None
        return {
            "status": "healthy",
            "last_refresh": last_refresh,
            "total_rows": total_rows,
            "tables": meta,
        }
    except Exception:
        return {"status": "no_data", "message": "Run ETL pipeline first"}
