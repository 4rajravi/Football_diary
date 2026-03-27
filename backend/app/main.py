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
           WHERE competition_id = ? AND CAST(season AS TEXT) = ?
           ORDER BY goals DESC
           LIMIT ?""",
        (competition_id, str(season), limit),
    )
    return {"top_scorers": rows}


@app.get("/api/stats/{competition_id}/{season}")
def get_stats(competition_id: str, season: int, stat_type: str = "top_scorers", limit: int = 30):
    """Flexible stats endpoint. stat_type determines the query."""
    s = str(season)

    queries = {
        "top_scorers": """
            SELECT player_name, club_name, appearances, goals, minutes_played
            FROM v_top_scorers
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
            ORDER BY goals DESC LIMIT ?
        """,
        "top_assists": """
            SELECT player_name, club_name, appearances,
                   CAST(assists AS INTEGER) AS assists, minutes_played
            FROM v_top_scorers
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
            ORDER BY CAST(assists AS INTEGER) DESC LIMIT ?
        """,
        "most_appearances": """
            SELECT player_name, club_name, appearances, goals, assists, minutes_played
            FROM v_player_season_stats
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
            ORDER BY appearances DESC LIMIT ?
        """,
        "most_minutes": """
            SELECT player_name, club_name, total_minutes AS minutes,
                   appearances, goals, assists
            FROM v_player_season_stats
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
            ORDER BY CAST(total_minutes AS INTEGER) DESC LIMIT ?
        """,
        "most_cards": """
            SELECT player_name, club_name, appearances,
                   yellow_cards, red_cards,
                   CAST(yellow_cards AS INTEGER) + CAST(red_cards AS INTEGER) AS total_cards
            FROM v_player_season_stats
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
            ORDER BY total_cards DESC, CAST(red_cards AS INTEGER) DESC LIMIT ?
        """,
        "super_sub": """
            SELECT a.player_name,
                   MAX(CASE WHEN g.home_club_id = a.player_club_id THEN g.home_club_name
                            ELSE g.away_club_name END) AS club_name,
                   COUNT(*) AS sub_appearances,
                   SUM(CAST(a.goals AS INTEGER)) AS goals,
                   SUM(CAST(a.assists AS INTEGER)) AS assists,
                   SUM(CAST(a.goals AS INTEGER)) + SUM(CAST(a.assists AS INTEGER)) AS impact
            FROM appearances a
            JOIN games g ON a.game_id = g.game_id
            WHERE a.competition_id = ? AND CAST(g.season AS TEXT) = ?
              AND CAST(a.minutes_played AS INTEGER) > 0
              AND CAST(a.minutes_played AS INTEGER) < 45
            GROUP BY a.player_id
            HAVING impact > 0
            ORDER BY impact DESC, goals DESC LIMIT ?
        """,
        "goals_per_90": """
            SELECT player_name, club_name, appearances, goals,
                   total_minutes AS minutes, goals_per_90
            FROM v_player_season_stats
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
              AND CAST(total_minutes AS INTEGER) >= 900
            ORDER BY CAST(goals_per_90 AS REAL) DESC LIMIT ?
        """,
        "assists_per_90": """
            SELECT player_name, club_name, appearances, assists,
                   total_minutes AS minutes, assists_per_90
            FROM v_player_season_stats
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
              AND CAST(total_minutes AS INTEGER) >= 900
            ORDER BY CAST(assists_per_90 AS REAL) DESC LIMIT ?
        """,
        "contributions_per_90": """
            SELECT player_name, club_name, appearances,
                   goals, assists, goal_contributions,
                   total_minutes AS minutes, contributions_per_90
            FROM v_player_season_stats
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
              AND CAST(total_minutes AS INTEGER) >= 900
            ORDER BY CAST(contributions_per_90 AS REAL) DESC LIMIT ?
        """,
        "minutes_per_goal": """
            SELECT player_name, club_name, appearances, goals,
                   total_minutes AS minutes,
                   CASE WHEN CAST(goals AS INTEGER) > 0
                        THEN ROUND(CAST(total_minutes AS REAL) / CAST(goals AS INTEGER), 1)
                        ELSE NULL END AS mins_per_goal
            FROM v_player_season_stats
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
              AND CAST(goals AS INTEGER) >= 3
            ORDER BY mins_per_goal ASC LIMIT ?
        """,
        "win_rate": """
            SELECT player_name,
                   games_started,
                   wins_when_started,
                   CASE WHEN CAST(games_started AS INTEGER) > 0
                        THEN ROUND(CAST(wins_when_started AS REAL) / CAST(games_started AS INTEGER) * 100, 1)
                        ELSE 0 END AS start_win_pct,
                   games_as_sub,
                   wins_as_sub,
                   CASE WHEN CAST(games_as_sub AS INTEGER) > 0
                        THEN ROUND(CAST(wins_as_sub AS REAL) / CAST(games_as_sub AS INTEGER) * 100, 1)
                        ELSE 0 END AS sub_win_pct
            FROM v_player_impact
            WHERE competition_id = ? AND CAST(season AS TEXT) = ?
              AND CAST(games_started AS INTEGER) >= 5
            ORDER BY start_win_pct DESC LIMIT ?
        """,
        "clean_sheets": """
            SELECT a.player_name,
                   MAX(CASE WHEN g.home_club_id = a.player_club_id THEN g.home_club_name
                            ELSE g.away_club_name END) AS club_name,
                   COUNT(*) AS appearances,
                   SUM(CASE WHEN CAST(CASE WHEN g.home_club_id = a.player_club_id
                                          THEN g.away_club_goals ELSE g.home_club_goals END AS INTEGER) = 0
                       THEN 1 ELSE 0 END) AS clean_sheets,
                   ROUND(SUM(CASE WHEN CAST(CASE WHEN g.home_club_id = a.player_club_id
                                          THEN g.away_club_goals ELSE g.home_club_goals END AS INTEGER) = 0
                       THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) AS clean_sheet_pct
            FROM appearances a
            JOIN games g ON a.game_id = g.game_id
            JOIN players p ON a.player_id = p.player_id
            WHERE a.competition_id = ? AND CAST(g.season AS TEXT) = ?
              AND p.position = 'Goalkeeper'
              AND CAST(a.minutes_played AS INTEGER) >= 45
            GROUP BY a.player_id, a.player_name
            HAVING appearances >= 3
            ORDER BY clean_sheets DESC, clean_sheet_pct DESC LIMIT ?
        """,
        "head_to_head": """
            SELECT
                club_a_name, club_b_name,
                total_matches, club_a_wins, club_b_wins, draws,
                club_a_goals, club_b_goals
            FROM v_head_to_head
            WHERE competition_id = ? AND total_matches >= 3
            ORDER BY total_matches DESC LIMIT ?
        """,
    }

    if stat_type not in queries:
        raise HTTPException(status_code=400, detail=f"Unknown stat type: {stat_type}")

    sql = queries[stat_type]

    if stat_type == "head_to_head":
        rows = execute_readonly(sql, (competition_id, limit))
    else:
        rows = execute_readonly(sql, (competition_id, s, limit))

    return {"stats": rows, "stat_type": stat_type}

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

@app.get("/api/matches/{competition_id}/{season}")
def get_matches(competition_id: str, season: int, limit: int = 500, offset: int = 0):
    """Get matches for a competition/season, most recent first."""
    rows = execute_readonly(
        """SELECT game_id, date, round, home_club_name, away_club_name,
                  home_club_goals, away_club_goals, stadium, attendance, referee,
                  home_club_id, away_club_id
           FROM games
           WHERE competition_id = ? AND CAST(season AS TEXT) = ?
           ORDER BY date DESC
           LIMIT ? OFFSET ?""",
        (competition_id, str(season), limit, offset),
    )
    return {"matches": rows}


@app.get("/api/match/{game_id}")
def get_match_detail(game_id: int):
    """Get match detail including lineups."""
    game = execute_readonly(
        """SELECT game_id, date, round, home_club_name, away_club_name,
                  home_club_goals, away_club_goals, stadium, attendance, referee,
                  home_club_id, away_club_id, competition_id, season
           FROM games WHERE game_id = ?""",
        (str(game_id),),
    )
    if not game:
        raise HTTPException(status_code=404, detail="Match not found")

    match = game[0]

    home_id = match["home_club_id"]
    away_id = match["away_club_id"]

    home_lineup = execute_readonly(
        """SELECT player_name, position, number, type, team_captain
           FROM game_lineups
           WHERE game_id = ? AND club_id = ?
           ORDER BY CASE WHEN type = 'starting_lineup' THEN 0 ELSE 1 END, number""",
        (str(game_id), str(home_id)),
    )

    away_lineup = execute_readonly(
        """SELECT player_name, position, number, type, team_captain
           FROM game_lineups
           WHERE game_id = ? AND club_id = ?
           ORDER BY CASE WHEN type = 'starting_lineup' THEN 0 ELSE 1 END, number""",
        (str(game_id), str(away_id)),
    )

    excluded_types = ['Tactical', 'Not reported', 'Special achievement', 'Resting', 'Delay']
    events = execute_readonly(
        """SELECT ge.minute, ge.type, ge.player_id, ge.club_id, ge.description,
                  ge.player_in_id,
                  p1.name AS player_name,
                  p2.name AS player_in_name,
                  p3.name AS assist_player_name
           FROM game_events ge
           LEFT JOIN players p1 ON ge.player_id = p1.player_id
           LEFT JOIN players p2 ON ge.player_in_id = p2.player_id
           LEFT JOIN players p3 ON ge.player_assist_id = p3.player_id
           WHERE ge.game_id = ? AND ge.type NOT IN ({})
           ORDER BY CAST(ge.minute AS INTEGER)""".format(",".join(["?"] * len(excluded_types))),
        (str(game_id), *excluded_types),
    )

    # Build goal/assist lookup per player
    player_goals = {}
    player_assists = {}
    for ev in events:
        if ev.get("type") == "Goals":
            pid = ev.get("player_id")
            if pid:
                player_goals[pid] = player_goals.get(pid, 0) + 1
            assist_id = ev.get("player_assist_id")
            if assist_id:
                player_assists[assist_id] = player_assists.get(assist_id, 0) + 1

    return {
        "match": match,
        "home_lineup": home_lineup,
        "away_lineup": away_lineup,
        "events": events,
        "player_goals": player_goals,
        "player_assists": player_assists,
    }

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
