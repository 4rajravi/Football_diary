"""
Football Diary AI Agent — powered by Groq (Llama 3.3 70B) with SQL tool-use.

The agent receives a user's natural-language question about football,
decides which SQL queries to run, executes them, and generates an answer
with optional chart configuration for the frontend to render.
"""

import json
from groq import Groq
from app.config import GROQ_API_KEY
from app.database import execute_readonly

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are Football Diary Assistant — a knowledgeable football analyst.
You answer questions about football matches, players, clubs, and competitions ONLY
by querying the SQLite database. You MUST use the execute_sql tool for EVERY question.
NEVER answer from your general knowledge — if the data isn't in the database, say so.
You have access to the following tools:

1. execute_sql — Run a read-only SQL query against the database.
2. get_available_tables — List all tables and views in the database.

DATABASE SCHEMA (key tables and views):

TABLES:
- competitions (competition_id, name, type, country_name, confederation)
- clubs (club_id, name, domestic_competition_id, stadium_name, squad_size, coach_name)
- players (player_id, name, position, country_of_citizenship, date_of_birth, foot, height_in_cm, market_value_in_eur, current_club_id, current_club_name)
- games (game_id, competition_id, season, round, date, home_club_id, away_club_id, home_club_goals, away_club_goals, home_club_name, away_club_name, stadium, attendance, referee, competition_type)
- appearances (appearance_id, game_id, player_id, player_club_id, player_name, competition_id, yellow_cards, red_cards, goals, assists, minutes_played)
- player_valuations (player_id, date, market_value_in_eur, current_club_id)
- club_games (club_id, game_id, opponent_id, own_goals, opponent_goals, hosting, is_win)
- game_events (game_id, minute, type, club_id, player_id, description, player_in_id, player_assist_id)
- game_lineups (game_id, club_id, player_id, type, position, number, player_name, team_captain)
- transfers (player_id, transfer_date, transfer_season, from_club_id, to_club_id, from_club_name, to_club_name, transfer_fee, player_name)

VIEWS (pre-computed analytics):
- v_head_to_head (club_a_id, club_a_name, club_b_id, club_b_name, competition_id, total_matches, club_a_wins, club_b_wins, draws, club_a_goals, club_b_goals)
- v_player_season_stats (player_id, player_name, competition_id, season, club_name, appearances, goals, assists, goal_contributions, total_minutes, goals_per_90, assists_per_90, contributions_per_90) — NOTE: this is PER SEASON. For career totals, SUM() and GROUP BY player_name. 
- v_player_impact (player_id, player_name, season, games_started, wins_when_started, games_as_sub, wins_as_sub)
- v_club_form (club_id, club_name, competition_id, season, date, own_goals, opponent_goals, result)
- v_standings (club_id, club_name, competition_id, season, played, wins, draws, losses, goals_for, goals_against, goal_difference, points)
- v_top_scorers (player_id, player_name, position, club_name, competition_id, season, goals, assists, goal_contributions, appearances, minutes_played) — NOTE: this is PER SEASON. For career totals, you MUST use SUM(goals) with GROUP BY player_name. 

COMPETITION IDS: GB1 (Premier League), ES1 (La Liga), L1 (Bundesliga), IT1 (Serie A), FR1 (Ligue 1), CL (Champions League), EL (Europa League), WC (World Cup), EURO (Euros)

RULES:
- Always use the pre-computed views when they fit the question (faster, pre-joined).
- For head-to-head, note v_head_to_head only counts HOME games for club_a. To get the full record, query both directions (club_a as home AND club_a as away) and combine.
- Use LIMIT to avoid huge result sets — max 50 rows unless the user asks for more.
- When comparing players, join on the same competition and season for fairness.
- For "recent" or "latest" queries, ORDER BY date DESC LIMIT N.
- IMPORTANT: If the user asks for a chart, include a `chart` field in your response JSON.

RESPONSE FORMAT:
Always respond with valid JSON containing:
{
  "answer": "Your natural language answer here.",
  "chart": {  // optional — include when visual data would help
    "type": "bar" | "line" | "horizontal_bar" | "table",
    "title": "Chart title",
    "data": [{"label": "...", "value": ...}, ...],
    "xKey": "label",
    "yKey": "value"
  }
}

If no chart is needed, omit the "chart" field entirely.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "Execute a read-only SQL query against the football database. Returns up to 50 rows as JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL SELECT query to execute.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_tables",
            "description": "List all tables and views in the database with their row counts.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def handle_tool_call(tool_name: str, tool_args: dict) -> str:
    """Execute a tool call and return the result as a string."""
    if tool_name == "execute_sql":
        query = tool_args.get("query", "")
        try:
            results = execute_readonly(query)
            if len(results) > 50:
                results = results[:50]
            return json.dumps(results, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    elif tool_name == "get_available_tables":
        try:
            tables = execute_readonly(
                "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name"
            )
            result = []
            for t in tables:
                count_result = execute_readonly(f"SELECT COUNT(*) as cnt FROM [{t['name']}]")
                result.append({
                    "name": t["name"],
                    "type": t["type"],
                    "rows": count_result[0]["cnt"] if count_result else 0,
                })
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def chat(user_message: str, history: list[dict] | None = None) -> dict:
    """Process a user message through the AI agent.

    Args:
        user_message: The user's natural language question.
        history: Previous conversation messages (optional).

    Returns:
        dict with 'answer' (str) and optionally 'chart' (dict).
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_message})

    # Agent loop — allow up to 5 tool calls
    for _ in range(5):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=2048,
        )

        message = response.choices[0].message

        if message.tool_calls:
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            # Execute each tool call and add results
            for tc in message.tool_calls:
                args = json.loads(tc.function.arguments)
                result = handle_tool_call(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            # No more tool calls — parse final answer
            content = message.content or ""
            try:
                # Try parsing as JSON (expected format)
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError:
                # If not JSON, wrap in standard format
                return {"answer": content}

    return {"answer": "I wasn't able to find the answer. Could you rephrase your question?"}
