"""
Football Diary — FastAPI Backend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.database import execute_readonly
from app.agent.agent import chat as agent_chat
from app.config import TARGET_COMPETITIONS, TOP_5_LEAGUES

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
def get_competition_filter(competition_id):
    """Returns (placeholders, params) for SQL IN clause."""
    if competition_id == "ALL5":
        return ",".join(["?"] * len(TOP_5_LEAGUES)), TOP_5_LEAGUES
    return "?", [competition_id]

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
def get_standings(competition_id: str, season: str, stage: str = "all"):
    """Get standings for a competition and season.
    stage: 'all' for leagues, 'Group A' etc for cup groups, 'knockout' for knockout results."""
    if stage == "knockout":
        rows = execute_readonly(
            """SELECT g.game_id, g.round, g.date, g.home_club_name, g.away_club_name,
                      g.home_club_goals, g.away_club_goals, g.home_club_id, g.away_club_id, g.stadium
               FROM games g
               WHERE g.competition_id = ? AND (CAST(g.season AS TEXT) = ? OR ? = 'all')
                 AND g.round NOT LIKE 'Group%'
                 AND g.round NOT LIKE 'Matchday%'
                 AND g.round NOT LIKE '%.%Spieltag%'
               ORDER BY g.date""",
            (competition_id, str(season), str(season)),
        )
        # Compute real aggregates by pairing 1st/2nd legs
        for row in rows:
            row["aggregate"] = None
            rnd = row.get("round", "")
            rnd_lower = rnd.lower()
            if "2nd leg" in rnd_lower:
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
               WHERE g.competition_id = ? AND (CAST(g.season AS TEXT) = ? OR ? = 'all') AND g.round = ?
               GROUP BY cg.club_id, cl.name
               ORDER BY points DESC, goal_difference DESC, goals_for DESC""",
            (competition_id, str(season), str(season), stage),
        )
        return {"standings": rows, "competition_id": competition_id, "season": season, "stage": stage}
    else:
        ph, comp_params = get_competition_filter(competition_id)
        if str(season) == "all":
            is_cup = competition_id in ['CL', 'EL']
            if is_cup:
                rows = execute_readonly(
                    f"""SELECT cg.club_id,
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
                       WHERE g.competition_id IN ({ph}) AND g.round LIKE 'Group%'
                       GROUP BY cg.club_id
                       ORDER BY points DESC, goal_difference DESC, goals_for DESC""",
                    tuple(comp_params),
                )
            else:
                rows = execute_readonly(
                    f"""SELECT club_id, club_name,
                              SUM(played) AS played, SUM(wins) AS wins, SUM(draws) AS draws,
                              SUM(losses) AS losses, SUM(goals_for) AS goals_for,
                              SUM(goals_against) AS goals_against,
                              SUM(goals_for) - SUM(goals_against) AS goal_difference,
                              SUM(points) AS points
                       FROM v_standings
                       WHERE competition_id IN ({ph})
                       GROUP BY club_id, club_name
                       ORDER BY points DESC, goal_difference DESC, goals_for DESC""",
                    tuple(comp_params),
                )
        else:
            rows = execute_readonly(
                f"""SELECT * FROM v_standings
                   WHERE competition_id IN ({ph}) AND CAST(season AS TEXT) = ?
                   ORDER BY points DESC, goal_difference DESC, goals_for DESC""",
                (*comp_params, str(season)),
            )
        if competition_id == "ALL5":
            rows = rows[:20]
        return {"standings": rows, "competition_id": competition_id, "season": season}

@app.get("/api/top-scorers/{competition_id}/{season}")
def get_top_scorers(competition_id: str, season: str, limit: int = 20):
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
def get_stats(competition_id: str, season: str, stat_type: str = "top_scorers", limit: int = 30, team: str = "all"):
    """Flexible stats endpoint. stat_type determines the query."""
    s = str(season)

    queries = {
        "top_scorers": """
            SELECT p.name AS player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT ge2.club_id FROM game_events ge2
                       JOIN games g2 ON ge2.game_id = g2.game_id
                       WHERE ge2.player_id = ge.player_id AND ge2.type = 'Goals'
                         AND g2.competition_id = g.competition_id
                       ORDER BY g2.date DESC LIMIT 1
                   )), '') AS club_name,
                   COUNT(*) AS goals,
                   COUNT(DISTINCT ge.game_id) AS games_with_goal,
                   (SELECT COUNT(DISTINCT a.game_id) FROM appearances a
                    JOIN games g2 ON a.game_id = g2.game_id
                    WHERE a.player_id = ge.player_id
                      AND CAST(g2.competition_id AS TEXT) = CAST(g.competition_id AS TEXT)
                      AND CAST(g2.season AS TEXT) = CAST(MIN(g.season) AS TEXT)) AS appearances
            FROM game_events ge
            JOIN games g ON ge.game_id = g.game_id
            JOIN players p ON ge.player_id = p.player_id
            WHERE g.competition_id = ? AND CAST(g.season AS TEXT) = ?
              AND ge.type = 'Goals'
            GROUP BY ge.player_id
            ORDER BY goals DESC LIMIT ?
        """,
        "top_assists": """
            SELECT p.name AS player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT ge2.club_id FROM game_events ge2
                       JOIN games g2 ON ge2.game_id = g2.game_id
                       WHERE ge2.player_assist_id = ge.player_assist_id AND ge2.type = 'Goals'
                         AND g2.competition_id = g.competition_id
                       ORDER BY g2.date DESC LIMIT 1
                   )), '') AS club_name,
                   COUNT(*) AS assists,
                   COUNT(DISTINCT ge.game_id) AS games_with_assist,
                   (SELECT COUNT(DISTINCT a.game_id) FROM appearances a
                    JOIN games g2 ON a.game_id = g2.game_id
                    WHERE a.player_id = ge.player_assist_id
                      AND CAST(g2.competition_id AS TEXT) = CAST(g.competition_id AS TEXT)
                      AND CAST(g2.season AS TEXT) = CAST(MIN(g.season) AS TEXT)) AS appearances
            FROM game_events ge
            JOIN games g ON ge.game_id = g.game_id
            JOIN players p ON ge.player_assist_id = p.player_id
            WHERE g.competition_id = ? AND CAST(g.season AS TEXT) = ?
              AND ge.type = 'Goals' AND ge.player_assist_id IS NOT NULL
            GROUP BY ge.player_assist_id
            ORDER BY assists DESC LIMIT ?
        """,
        "most_appearances": """
            SELECT c.player_name, COALESCE(cl.name, '') AS club_name,
                   c.appearances, c.total_minutes AS minutes_played
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ? AND CAST(c.season AS TEXT) = ?
            ORDER BY c.appearances DESC LIMIT ?
        """,
        "most_minutes": """
            SELECT c.player_name, COALESCE(cl.name, '') AS club_name,
                   c.total_minutes AS minutes, c.appearances, c.goals, c.assists
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ? AND CAST(c.season AS TEXT) = ?
            ORDER BY c.total_minutes DESC LIMIT ?
        """,
        "most_cards": """
            SELECT c.player_name, COALESCE(cl.name, '') AS club_name, c.appearances,
                   c.yellow_cards, c.red_cards,
                   c.yellow_cards + c.red_cards AS total_cards
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ? AND CAST(c.season AS TEXT) = ?
            ORDER BY total_cards DESC, c.red_cards DESC LIMIT ?
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
            GROUP BY a.player_id, a.player_club_id
            HAVING impact > 0
            ORDER BY impact DESC, goals DESC LIMIT ?
        """,
        "goals_per_90": """
            SELECT c.player_name, COALESCE(cl.name, '') AS club_name,
                   c.appearances, c.goals, c.total_minutes AS minutes,
                   ROUND(CAST(c.goals AS REAL) / c.total_minutes * 90, 2) AS goals_per_90
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ? AND CAST(c.season AS TEXT) = ?
              AND c.total_minutes >= 900
            ORDER BY goals_per_90 DESC LIMIT ?
        """,
        "assists_per_90": """
            SELECT c.player_name, COALESCE(cl.name, '') AS club_name,
                   c.appearances, c.assists, c.total_minutes AS minutes,
                   ROUND(CAST(c.assists AS REAL) / c.total_minutes * 90, 2) AS assists_per_90
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ? AND CAST(c.season AS TEXT) = ?
              AND c.total_minutes >= 900
            ORDER BY assists_per_90 DESC LIMIT ?
        """,
        "contributions_per_90": """
            SELECT c.player_name, COALESCE(cl.name, '') AS club_name,
                   c.appearances, c.goals, c.assists,
                   c.goals + c.assists AS goal_contributions,
                   c.total_minutes AS minutes,
                   ROUND(CAST(c.goals + c.assists AS REAL) / c.total_minutes * 90, 2) AS contributions_per_90
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ? AND CAST(c.season AS TEXT) = ?
              AND c.total_minutes >= 900
            ORDER BY contributions_per_90 DESC LIMIT ?
        """,
        "minutes_per_goal": """
            SELECT c.player_name, COALESCE(cl.name, '') AS club_name,
                   c.appearances, c.goals, c.total_minutes AS minutes,
                   ROUND(CAST(c.total_minutes AS REAL) / c.goals, 1) AS mins_per_goal
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ? AND CAST(c.season AS TEXT) = ?
              AND c.goals >= 3
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
            GROUP BY a.player_id, a.player_name, a.player_club_id
            HAVING appearances >= 3
            ORDER BY clean_sheets DESC, clean_sheet_pct DESC LIMIT ?
        """,
        "home_record": """
            SELECT cg.club_id,
                   COALESCE(cl.name,
                     MAX(CASE WHEN g.home_club_id = cg.club_id THEN g.home_club_name ELSE NULL END)
                   ) AS club_name,
                   COUNT(*) AS played,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS draws,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) < CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS losses,
                   SUM(CAST(cg.own_goals AS INTEGER)) AS goals_for,
                   SUM(CAST(cg.opponent_goals AS INTEGER)) AS goals_against,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 3
                            WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1
                            ELSE 0 END) AS points
            FROM club_games cg
            JOIN games g ON cg.game_id = g.game_id
            LEFT JOIN clubs cl ON cg.club_id = cl.club_id
            WHERE g.competition_id = ? AND CAST(g.season AS TEXT) = ? AND cg.hosting = 'Home'
            GROUP BY cg.club_id
            ORDER BY points DESC, goals_for DESC LIMIT ?
        """,
        "away_record": """
            SELECT cg.club_id,
                   COALESCE(cl.name,
                     MAX(CASE WHEN g.away_club_id = cg.club_id THEN g.away_club_name ELSE NULL END)
                   ) AS club_name,
                   COUNT(*) AS played,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS draws,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) < CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS losses,
                   SUM(CAST(cg.own_goals AS INTEGER)) AS goals_for,
                   SUM(CAST(cg.opponent_goals AS INTEGER)) AS goals_against,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 3
                            WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1
                            ELSE 0 END) AS points
            FROM club_games cg
            JOIN games g ON cg.game_id = g.game_id
            LEFT JOIN clubs cl ON cg.club_id = cl.club_id
            WHERE g.competition_id = ? AND CAST(g.season AS TEXT) = ? AND cg.hosting = 'Away'
            GROUP BY cg.club_id
            ORDER BY points DESC, goals_for DESC LIMIT ?
        """,
        "top_scorers_home": """
            SELECT p.name AS player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT ge2.club_id FROM game_events ge2
                       JOIN games g2 ON ge2.game_id = g2.game_id
                       WHERE ge2.player_id = ge.player_id AND ge2.type = 'Goals'
                         AND g2.competition_id = g.competition_id AND ge2.club_id = g2.home_club_id
                       ORDER BY g2.date DESC LIMIT 1
                   )), '') AS club_name,
                   COUNT(*) AS goals,
                   COUNT(DISTINCT ge.game_id) AS games_with_goal,
                   (SELECT COUNT(DISTINCT a.game_id) FROM appearances a
                    JOIN games g2 ON a.game_id = g2.game_id
                    WHERE a.player_id = ge.player_id
                      AND g2.competition_id = g.competition_id
                      AND g2.home_club_id = a.player_club_id
                      AND CAST(g2.season AS TEXT) = CAST(MIN(g.season) AS TEXT)) AS appearances
            FROM game_events ge
            JOIN games g ON ge.game_id = g.game_id
            JOIN players p ON ge.player_id = p.player_id
            WHERE g.competition_id = ? AND CAST(g.season AS TEXT) = ?
              AND ge.type = 'Goals'
              AND ge.club_id = g.home_club_id
            GROUP BY ge.player_id
            ORDER BY goals DESC LIMIT ?
        """,
        "top_scorers_away": """
            SELECT p.name AS player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT ge2.club_id FROM game_events ge2
                       JOIN games g2 ON ge2.game_id = g2.game_id
                       WHERE ge2.player_id = ge.player_id AND ge2.type = 'Goals'
                         AND g2.competition_id = g.competition_id AND ge2.club_id = g2.away_club_id
                       ORDER BY g2.date DESC LIMIT 1
                   )), '') AS club_name,
                   COUNT(*) AS goals,
                   COUNT(DISTINCT ge.game_id) AS games_with_goal,
                   (SELECT COUNT(DISTINCT a.game_id) FROM appearances a
                    JOIN games g2 ON a.game_id = g2.game_id
                    WHERE a.player_id = ge.player_id
                      AND g2.competition_id = g.competition_id
                      AND g2.away_club_id = a.player_club_id
                      AND CAST(g2.season AS TEXT) = CAST(MIN(g.season) AS TEXT)) AS appearances
            FROM game_events ge
            JOIN games g ON ge.game_id = g.game_id
            JOIN players p ON ge.player_id = p.player_id
            WHERE g.competition_id = ? AND CAST(g.season AS TEXT) = ?
              AND ge.type = 'Goals'
              AND ge.club_id = g.away_club_id
            GROUP BY ge.player_id
            ORDER BY goals DESC LIMIT ?
        """,
        "head_to_head": """
            SELECT
                h1.club_a_name,
                h1.club_b_name,
                CAST(h1.total_matches AS INTEGER) + COALESCE(CAST(h2.total_matches AS INTEGER), 0) AS total_matches,
                CAST(h1.club_a_wins AS INTEGER) + COALESCE(CAST(h2.club_b_wins AS INTEGER), 0) AS club_a_wins,
                CAST(h1.club_b_wins AS INTEGER) + COALESCE(CAST(h2.club_a_wins AS INTEGER), 0) AS club_b_wins,
                CAST(h1.draws AS INTEGER) + COALESCE(CAST(h2.draws AS INTEGER), 0) AS draws,
                CAST(h1.club_a_goals AS INTEGER) + COALESCE(CAST(h2.club_b_goals AS INTEGER), 0) AS club_a_goals,
                CAST(h1.club_b_goals AS INTEGER) + COALESCE(CAST(h2.club_a_goals AS INTEGER), 0) AS club_b_goals
            FROM v_head_to_head h1
            LEFT JOIN v_head_to_head h2
                ON h1.club_a_id = h2.club_b_id
                AND h1.club_b_id = h2.club_a_id
                AND h1.competition_id = h2.competition_id
            WHERE h1.competition_id = ?
              AND h1.club_a_id < h1.club_b_id
              AND (CAST(h1.total_matches AS INTEGER) + COALESCE(CAST(h2.total_matches AS INTEGER), 0)) >= 5
            ORDER BY total_matches DESC LIMIT ?
        """,
    }

    # Aggregated versions for Overall mode
    
    all_queries = {
        "most_appearances": """
            SELECT c.player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT c2.club_id FROM computed_player_stats c2
                       WHERE c2.player_id = c.player_id AND c2.competition_id = c.competition_id
                       ORDER BY c2.season DESC LIMIT 1)), '') AS club_name,
                   SUM(c.appearances) AS appearances,
                   SUM(c.total_minutes) AS minutes_played
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ?
            GROUP BY c.player_id
            ORDER BY appearances DESC LIMIT ?
        """,
        "most_minutes": """
            SELECT c.player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT c2.club_id FROM computed_player_stats c2
                       WHERE c2.player_id = c.player_id AND c2.competition_id = c.competition_id
                       ORDER BY c2.season DESC LIMIT 1)), '') AS club_name,
                   SUM(c.total_minutes) AS minutes,
                   SUM(c.appearances) AS appearances,
                   SUM(c.goals) AS goals,
                   SUM(c.assists) AS assists
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ?
            GROUP BY c.player_id
            ORDER BY minutes DESC LIMIT ?
        """,
        "most_cards": """
            SELECT c.player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT c2.club_id FROM computed_player_stats c2
                       WHERE c2.player_id = c.player_id AND c2.competition_id = c.competition_id
                       ORDER BY c2.season DESC LIMIT 1)), '') AS club_name,
                   SUM(c.appearances) AS appearances,
                   SUM(c.yellow_cards) AS yellow_cards,
                   SUM(c.red_cards) AS red_cards,
                   SUM(c.yellow_cards) + SUM(c.red_cards) AS total_cards
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ?
            GROUP BY c.player_id
            ORDER BY total_cards DESC, red_cards DESC LIMIT ?
        """,
        "goals_per_90": """
            SELECT c.player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT c2.club_id FROM computed_player_stats c2
                       WHERE c2.player_id = c.player_id AND c2.competition_id = c.competition_id
                       ORDER BY c2.season DESC LIMIT 1)), '') AS club_name,
                   SUM(c.appearances) AS appearances,
                   SUM(c.goals) AS goals,
                   SUM(c.total_minutes) AS minutes,
                   ROUND(CAST(SUM(c.goals) AS REAL) / SUM(c.total_minutes) * 90, 2) AS goals_per_90
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ?
            GROUP BY c.player_id
            HAVING SUM(c.total_minutes) >= 900
            ORDER BY goals_per_90 DESC LIMIT ?
        """,
        "assists_per_90": """
            SELECT c.player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT c2.club_id FROM computed_player_stats c2
                       WHERE c2.player_id = c.player_id AND c2.competition_id = c.competition_id
                       ORDER BY c2.season DESC LIMIT 1)), '') AS club_name,
                   SUM(c.appearances) AS appearances,
                   SUM(c.assists) AS assists,
                   SUM(c.total_minutes) AS minutes,
                   ROUND(CAST(SUM(c.assists) AS REAL) / SUM(c.total_minutes) * 90, 2) AS assists_per_90
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ?
            GROUP BY c.player_id
            HAVING SUM(c.total_minutes) >= 900
            ORDER BY assists_per_90 DESC LIMIT ?
        """,
        "contributions_per_90": """
            SELECT c.player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT c2.club_id FROM computed_player_stats c2
                       WHERE c2.player_id = c.player_id AND c2.competition_id = c.competition_id
                       ORDER BY c2.season DESC LIMIT 1)), '') AS club_name,
                   SUM(c.appearances) AS appearances,
                   SUM(c.goals) AS goals,
                   SUM(c.assists) AS assists,
                   SUM(c.goals) + SUM(c.assists) AS goal_contributions,
                   SUM(c.total_minutes) AS minutes,
                   ROUND(CAST(SUM(c.goals) + SUM(c.assists) AS REAL) / SUM(c.total_minutes) * 90, 2) AS contributions_per_90
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ?
            GROUP BY c.player_id
            HAVING SUM(c.total_minutes) >= 900
            ORDER BY contributions_per_90 DESC LIMIT ?
        """,
        "minutes_per_goal": """
            SELECT c.player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT c2.club_id FROM computed_player_stats c2
                       WHERE c2.player_id = c.player_id AND c2.competition_id = c.competition_id
                       ORDER BY c2.season DESC LIMIT 1)), '') AS club_name,
                   SUM(c.appearances) AS appearances,
                   SUM(c.goals) AS goals,
                   SUM(c.total_minutes) AS minutes,
                   ROUND(CAST(SUM(c.total_minutes) AS REAL) / SUM(c.goals), 1) AS mins_per_goal
            FROM computed_player_stats c
            LEFT JOIN clubs cl ON c.club_id = cl.club_id
            WHERE c.competition_id = ?
            GROUP BY c.player_id
            HAVING SUM(c.goals) >= 3
            ORDER BY mins_per_goal ASC LIMIT ?
        """,
        "win_rate": """
            SELECT player_name,
                   SUM(CAST(games_started AS INTEGER)) AS games_started,
                   SUM(CAST(wins_when_started AS INTEGER)) AS wins_when_started,
                   CASE WHEN SUM(CAST(games_started AS INTEGER)) > 0
                        THEN ROUND(CAST(SUM(CAST(wins_when_started AS INTEGER)) AS REAL) / SUM(CAST(games_started AS INTEGER)) * 100, 1)
                        ELSE 0 END AS start_win_pct,
                   SUM(CAST(games_as_sub AS INTEGER)) AS games_as_sub,
                   SUM(CAST(wins_as_sub AS INTEGER)) AS wins_as_sub,
                   CASE WHEN SUM(CAST(games_as_sub AS INTEGER)) > 0
                        THEN ROUND(CAST(SUM(CAST(wins_as_sub AS INTEGER)) AS REAL) / SUM(CAST(games_as_sub AS INTEGER)) * 100, 1)
                        ELSE 0 END AS sub_win_pct
            FROM v_player_impact
            WHERE competition_id = ?
            GROUP BY player_id, player_name
            HAVING SUM(CAST(games_started AS INTEGER)) >= 5
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
            WHERE a.competition_id = ?
              AND p.position = 'Goalkeeper'
              AND CAST(a.minutes_played AS INTEGER) >= 45
            GROUP BY a.player_id, a.player_name, a.player_club_id
            HAVING appearances >= 3
            ORDER BY clean_sheets DESC, clean_sheet_pct DESC LIMIT ?
        """,
        "top_scorers_home": """
            SELECT p.name AS player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT ge2.club_id FROM game_events ge2
                       JOIN games g2 ON ge2.game_id = g2.game_id
                       WHERE ge2.player_id = ge.player_id AND ge2.type = 'Goals'
                         AND g2.competition_id = g.competition_id AND ge2.club_id = g2.home_club_id
                       ORDER BY g2.date DESC LIMIT 1
                   )), '') AS club_name,
                   COUNT(*) AS goals,
                   COUNT(DISTINCT ge.game_id) AS games_with_goal,
                   (SELECT COUNT(DISTINCT a.game_id) FROM appearances a
                    JOIN games g2 ON a.game_id = g2.game_id
                    WHERE a.player_id = ge.player_id
                      AND g2.competition_id = g.competition_id
                      AND g2.home_club_id = a.player_club_id) AS appearances
            FROM game_events ge
            JOIN games g ON ge.game_id = g.game_id
            JOIN players p ON ge.player_id = p.player_id
            WHERE g.competition_id = ?
              AND ge.type = 'Goals'
              AND ge.club_id = g.home_club_id
            GROUP BY ge.player_id
            ORDER BY goals DESC LIMIT ?
        """,
        "top_scorers_away": """
            SELECT p.name AS player_name,
                   COALESCE((SELECT cl2.name FROM clubs cl2 WHERE cl2.club_id = (
                       SELECT ge2.club_id FROM game_events ge2
                       JOIN games g2 ON ge2.game_id = g2.game_id
                       WHERE ge2.player_id = ge.player_id AND ge2.type = 'Goals'
                         AND g2.competition_id = g.competition_id AND ge2.club_id = g2.away_club_id
                       ORDER BY g2.date DESC LIMIT 1
                   )), '') AS club_name,
                   COUNT(*) AS goals,
                   COUNT(DISTINCT ge.game_id) AS games_with_goal,
                   (SELECT COUNT(DISTINCT a.game_id) FROM appearances a
                    JOIN games g2 ON a.game_id = g2.game_id
                    WHERE a.player_id = ge.player_id
                      AND g2.competition_id = g.competition_id
                      AND g2.away_club_id = a.player_club_id) AS appearances
            FROM game_events ge
            JOIN games g ON ge.game_id = g.game_id
            JOIN players p ON ge.player_id = p.player_id
            WHERE g.competition_id = ?
              AND ge.type = 'Goals'
              AND ge.club_id = g.away_club_id
            GROUP BY ge.player_id
            ORDER BY goals DESC LIMIT ?
        """,
        "home_record": """
            SELECT cg.club_id,
                   COALESCE(cl.name, MAX(g.home_club_name)) AS club_name,
                   COUNT(*) AS played,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS draws,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) < CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS losses,
                   SUM(CAST(cg.own_goals AS INTEGER)) AS goals_for,
                   SUM(CAST(cg.opponent_goals AS INTEGER)) AS goals_against,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 3
                            WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1
                            ELSE 0 END) AS points
            FROM club_games cg
            JOIN games g ON cg.game_id = g.game_id
            LEFT JOIN clubs cl ON cg.club_id = cl.club_id
            WHERE g.competition_id = ? AND cg.hosting = 'Home'
            GROUP BY cg.club_id
            ORDER BY points DESC, goals_for DESC LIMIT ?
        """,
        "away_record": """
            SELECT cg.club_id,
                   COALESCE(cl.name, MAX(g.away_club_name)) AS club_name,
                   COUNT(*) AS played,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS draws,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) < CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END) AS losses,
                   SUM(CAST(cg.own_goals AS INTEGER)) AS goals_for,
                   SUM(CAST(cg.opponent_goals AS INTEGER)) AS goals_against,
                   SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 3
                            WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1
                            ELSE 0 END) AS points
            FROM club_games cg
            JOIN games g ON cg.game_id = g.game_id
            LEFT JOIN clubs cl ON cg.club_id = cl.club_id
            WHERE g.competition_id = ? AND cg.hosting = 'Away'
            GROUP BY cg.club_id
            ORDER BY points DESC, goals_for DESC LIMIT ?
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
            WHERE a.competition_id = ?
              AND CAST(a.minutes_played AS INTEGER) > 0
              AND CAST(a.minutes_played AS INTEGER) < 45
            GROUP BY a.player_id, a.player_club_id
            HAVING impact > 0
            ORDER BY impact DESC, goals DESC LIMIT ?
        """,
    }

    if stat_type not in queries and stat_type not in all_queries:
        raise HTTPException(status_code=400, detail=f"Unknown stat type: {stat_type}")

    if s == "all" and stat_type in all_queries:
        sql = all_queries[stat_type]
    else:
        sql = queries[stat_type]

    # Apply team filter by wrapping in a subquery
    import re

    # Resolve team name to club_ids
    club_ids = []
    if team != "all" and stat_type != "head_to_head":
        club_rows = execute_readonly(
            "SELECT DISTINCT club_id FROM clubs WHERE name = ?", (team,)
        )
        if not club_rows:
            club_rows = execute_readonly(
                """SELECT DISTINCT home_club_id AS club_id FROM games WHERE home_club_name = ?
                   UNION SELECT DISTINCT away_club_id FROM games WHERE away_club_name = ?""",
                (team, team)
            )
        club_ids = [r["club_id"] for r in club_rows]

    # Inject team filter into SQL
    if club_ids:
        placeholders = ",".join([f"'{cid}'" for cid in club_ids])
        # Find the right column to filter on
        if "FROM game_events ge" in sql:
            team_filter = f" AND ge.player_id IN (SELECT DISTINCT player_id FROM appearances WHERE player_club_id IN ({placeholders}))"
        elif "FROM appearances a" in sql:
            team_filter = f" AND a.player_club_id IN ({placeholders})"
        elif "FROM computed_player_stats c" in sql:
            team_filter = f" AND c.club_id IN ({placeholders})"
        elif "FROM club_games cg" in sql:
            team_filter = f" AND cg.club_id IN ({placeholders})"
        elif "FROM v_player_impact" in sql:
            team_filter = f" AND player_id IN (SELECT DISTINCT player_id FROM appearances WHERE player_club_id IN ({placeholders}))"
        else:
            team_filter = ""

        # Insert before GROUP BY, ORDER BY, or HAVING
        for kw in ["GROUP BY", "HAVING", "ORDER BY"]:
            if kw in sql:
                sql = sql.replace(kw, team_filter + " " + kw, 1)
                break

    # Remove LIMIT ? from SQL, handle it in Python
    sql = re.sub(r'LIMIT\s*\?', 'LIMIT 500', sql)

    # Execute
    # Handle ALL5 — replace single competition_id = ? with IN (?, ?, ...)
    if competition_id == "ALL5":
        ph = ",".join(["?"] * len(TOP_5_LEAGUES))
        sql = sql.replace("g.competition_id = ?", f"g.competition_id IN ({ph})") \
                  .replace("a.competition_id = ?", f"a.competition_id IN ({ph})") \
                  .replace("s.competition_id = ?", f"s.competition_id IN ({ph})") \
                  .replace("competition_id = ?", f"competition_id IN ({ph})")
        comp_params = tuple(TOP_5_LEAGUES)
    else:
        comp_params = (competition_id,)

    if stat_type == "head_to_head":
        rows = execute_readonly(sql, comp_params)
    elif s == "all":
        if stat_type not in all_queries:
            sql = sql.replace("AND CAST(season AS TEXT) = ?", "") \
                      .replace("AND CAST(s.season AS TEXT) = ?", "") \
                      .replace("AND CAST(g.season AS TEXT) = ?", "") \
                      .replace("AND g2.season = g.season", "") \
                      .replace("AND CAST(g2.season AS TEXT) = CAST(MIN(g.season) AS TEXT)", "")
        rows = execute_readonly(sql, comp_params)
    else:
        rows = execute_readonly(sql, (*comp_params, s))

    # Post-filter for head_to_head only
    if team != "all" and stat_type == "head_to_head" and rows:
        rows = [r for r in rows if
                r.get("club_a_name") == team or
                r.get("club_b_name") == team]

    rows = rows[:limit]
    return {"stats": rows, "stat_type": stat_type}

@app.get("/api/rounds/{competition_id}/{season}")
def get_rounds(competition_id: str, season: str):
    """Get distinct rounds for a competition/season."""
    rows = execute_readonly(
        """SELECT DISTINCT round FROM games
           WHERE competition_id = ? AND CAST(season AS TEXT) = ?
           ORDER BY date""",
        (competition_id, str(season)),
    )
    return {"rounds": [r["round"] for r in rows if r["round"]]}

@app.get("/api/seasons/{competition_id}")
def get_seasons(competition_id: str):
    """List available seasons for a competition."""
    ph, params = get_competition_filter(competition_id)
    rows = execute_readonly(
        f"SELECT DISTINCT season FROM games WHERE competition_id IN ({ph}) ORDER BY season DESC",
        tuple(params),
    )
    return {"seasons": [r["season"] for r in rows]}

@app.get("/api/matches/{competition_id}/{season}")
def get_matches(competition_id: str, season: str, limit: int = 500, offset: int = 0):
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
           ORDER BY CASE WHEN type = 'starting_lineup' THEN 0 ELSE 1 END, CAST(number AS INTEGER)""",
        (str(game_id), str(home_id)),
    )

    away_lineup = execute_readonly(
        """SELECT player_name, position, number, type, team_captain
           FROM game_lineups
           WHERE game_id = ? AND club_id = ?
           ORDER BY CASE WHEN type = 'starting_lineup' THEN 0 ELSE 1 END, CAST(number AS INTEGER)""",
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
@app.get("/api/players/search")
def search_players(q: str = "", limit: int = 20):
    """Search players by name prefix."""
    if len(q) < 1:
        return {"players": []}
    rows = execute_readonly(
        """SELECT DISTINCT p.player_id, p.name, p.position,
                  p.country_of_citizenship, COALESCE(cl.name, '') AS current_club
           FROM players p
           LEFT JOIN clubs cl ON p.current_club_id = cl.club_id
           WHERE p.name LIKE ?
           ORDER BY p.name LIMIT ?""",
        (f"{q}%", limit),
    )
    return {"players": rows}


@app.get("/api/players/{player_id}/stats")
def get_player_stats(player_id: str, season: str = "all"):
    """Get a player's stats across all competitions, season by season or overall."""
    # Player info
    player = execute_readonly(
        """SELECT p.player_id, p.name, p.position, p.country_of_citizenship,
                  p.date_of_birth, p.foot, p.height_in_cm,
                  COALESCE(cl.name, '') AS current_club
           FROM players p
           LEFT JOIN clubs cl ON p.current_club_id = cl.club_id
           WHERE p.player_id = ?""",
        (player_id,),
    )
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    if season == "all":
        # Overall stats per competition
        stats = execute_readonly(
            """SELECT g.competition_id, COALESCE(cl.name, '') AS club_name,
                      COUNT(DISTINCT a.game_id) AS appearances,
                      SUM(CAST(a.minutes_played AS INTEGER)) AS minutes_played,
                      (SELECT COUNT(*) FROM game_events ge
                       JOIN games g2 ON ge.game_id = g2.game_id
                       WHERE ge.player_id = a.player_id AND ge.type = 'Goals'
                         AND g2.competition_id = g.competition_id) AS goals,
                      (SELECT COUNT(*) FROM game_events ge2
                       JOIN games g3 ON ge2.game_id = g3.game_id
                       WHERE ge2.player_assist_id = a.player_id AND ge2.type = 'Goals'
                         AND g3.competition_id = g.competition_id) AS assists
               FROM appearances a
               JOIN games g ON a.game_id = g.game_id
               LEFT JOIN clubs cl ON a.player_club_id = cl.club_id
               WHERE a.player_id = ?
               GROUP BY g.competition_id, a.player_club_id
               ORDER BY appearances DESC""",
            (player_id,),
        )
    else:
        # Stats for a specific season per competition
        stats = execute_readonly(
            """SELECT g.competition_id, g.season, COALESCE(cl.name, '') AS club_name,
                      COUNT(DISTINCT a.game_id) AS appearances,
                      SUM(CAST(a.minutes_played AS INTEGER)) AS minutes_played,
                      (SELECT COUNT(*) FROM game_events ge
                       JOIN games g2 ON ge.game_id = g2.game_id
                       WHERE ge.player_id = a.player_id AND ge.type = 'Goals'
                         AND g2.competition_id = g.competition_id
                         AND CAST(g2.season AS TEXT) = ?) AS goals,
                      (SELECT COUNT(*) FROM game_events ge2
                       JOIN games g3 ON ge2.game_id = g3.game_id
                       WHERE ge2.player_assist_id = a.player_id AND ge2.type = 'Goals'
                         AND g3.competition_id = g.competition_id
                         AND CAST(g3.season AS TEXT) = ?) AS assists
               FROM appearances a
               JOIN games g ON a.game_id = g.game_id
               LEFT JOIN clubs cl ON a.player_club_id = cl.club_id
               WHERE a.player_id = ? AND CAST(g.season AS TEXT) = ?
               GROUP BY g.competition_id, a.player_club_id
               ORDER BY appearances DESC""",
            (season, season, player_id, season),
        )

    # Get available seasons for this player
    player_seasons = execute_readonly(
        """SELECT DISTINCT g.season FROM appearances a
           JOIN games g ON a.game_id = g.game_id
           WHERE a.player_id = ?
           ORDER BY g.season DESC""",
        (player_id,),
    )

    return {
        "player": player[0],
        "stats": stats,
        "seasons": [r["season"] for r in player_seasons],
    }


@app.get("/api/players/top")
def get_top_players(season: str = "all", limit: int = 30):
    """All-time or season-wise top players across ALL competitions."""
    if season == "all":
        rows = execute_readonly(
            """SELECT p.name AS player_name, COALESCE(cl.name, '') AS current_club,
                      (SELECT COUNT(*) FROM game_events ge WHERE ge.player_id = p.player_id AND ge.type = 'Goals') AS goals,
                      (SELECT COUNT(*) FROM game_events ge WHERE ge.player_assist_id = p.player_id AND ge.type = 'Goals') AS assists,
                      (SELECT SUM(CAST(a.minutes_played AS INTEGER)) FROM appearances a WHERE a.player_id = p.player_id) AS minutes_played,
                      (SELECT COUNT(DISTINCT a.game_id) FROM appearances a WHERE a.player_id = p.player_id) AS appearances,
                      p.player_id
               FROM players p
               LEFT JOIN clubs cl ON p.current_club_id = cl.club_id
               WHERE p.player_id IN (
                   SELECT ge.player_id FROM game_events ge WHERE ge.type = 'Goals'
                   GROUP BY ge.player_id ORDER BY COUNT(*) DESC LIMIT ?
               )
               ORDER BY goals DESC""",
            (limit,),
        )
    else:
        rows = execute_readonly(
            """SELECT p.name AS player_name, COALESCE(cl.name, '') AS current_club,
                      (SELECT COUNT(*) FROM game_events ge
                       JOIN games g ON ge.game_id = g.game_id
                       WHERE ge.player_id = p.player_id AND ge.type = 'Goals'
                         AND CAST(g.season AS TEXT) = ?) AS goals,
                      (SELECT COUNT(*) FROM game_events ge2
                       JOIN games g2 ON ge2.game_id = g2.game_id
                       WHERE ge2.player_assist_id = p.player_id AND ge2.type = 'Goals'
                         AND CAST(g2.season AS TEXT) = ?) AS assists,
                      (SELECT SUM(CAST(a.minutes_played AS INTEGER)) FROM appearances a
                       JOIN games g3 ON a.game_id = g3.game_id
                       WHERE a.player_id = p.player_id AND CAST(g3.season AS TEXT) = ?) AS minutes_played,
                      (SELECT COUNT(DISTINCT a.game_id) FROM appearances a
                       JOIN games g4 ON a.game_id = g4.game_id
                       WHERE a.player_id = p.player_id AND CAST(g4.season AS TEXT) = ?) AS appearances,
                      p.player_id
               FROM players p
               LEFT JOIN clubs cl ON p.current_club_id = cl.club_id
               WHERE p.player_id IN (
                   SELECT ge.player_id FROM game_events ge
                   JOIN games g ON ge.game_id = g.game_id
                   WHERE ge.type = 'Goals' AND CAST(g.season AS TEXT) = ?
                   GROUP BY ge.player_id ORDER BY COUNT(*) DESC LIMIT ?
               )
               ORDER BY goals DESC""",
            (season, season, season, season, season, limit),
        )
    return {"players": rows}

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
