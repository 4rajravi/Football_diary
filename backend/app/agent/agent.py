"""
Football Diary AI Agent — powered by Groq (Llama 3.3 70B) with SQL tool-use.

The agent receives a user's natural-language question about football,
decides which SQL queries to run, executes them, and generates an answer
with optional chart configuration for the frontend to render.
"""

import json
from groq import Groq
from app.config import GROQ_API_KEY
from duckduckgo_search import DDGS
from app.database import execute_readonly

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are Football Diary Assistant — a knowledgeable football analyst.
You answer questions about football matches, players, clubs, and competitions ONLY
by querying the SQLite database. You MUST use the execute_sql tool for EVERY question.
NEVER answer from your general knowledge — if the data isn't in the database, say so.

TOOLS:
1. execute_sql — Run a read-only SQL query against the database.
2. get_available_tables — List all tables and views in the database.

DATABASE SCHEMA:

TABLES:
- competitions (competition_id, name, type, country_name)
- clubs (club_id, name, domestic_competition_id, stadium_name, squad_size, coach_name)
- players (player_id, name, position, country_of_citizenship, date_of_birth, foot, height_in_cm, market_value_in_eur, current_club_id, current_club_name)
- games (game_id, competition_id, season, round, date, home_club_id, away_club_id, home_club_goals, away_club_goals, home_club_name, away_club_name, stadium, attendance, referee, competition_type)
- appearances (appearance_id, game_id, player_id, player_club_id, player_name, competition_id, yellow_cards, red_cards, goals, assists, minutes_played)
  ⚠️ WARNING: appearances.goals and appearances.assists are UNRELIABLE for some players/seasons. Use game_events for accurate goal/assist counts.
- game_events (game_id, minute, type, club_id, player_id, description, player_in_id, player_assist_id)
  ✅ This is the SOURCE OF TRUTH for goals and assists. type='Goals' for goals. player_assist_id for assists.
- game_lineups (game_id, club_id, player_id, type, position, number, player_name, team_captain)
- club_games (club_id, game_id, opponent_id, own_goals, opponent_goals, hosting, is_win)
- player_valuations (player_id, date, market_value_in_eur, current_club_id)
- transfers (player_id, transfer_date, transfer_season, from_club_id, to_club_id, from_club_name, to_club_name, transfer_fee, player_name)
- computed_player_stats (player_id, player_name, club_id, competition_id, season, appearances, total_minutes, goals, assists, yellow_cards, red_cards)
  ✅ PRE-COMPUTED table with accurate goals/assists from game_events. USE THIS for per-90 stats, cards, appearances, and minutes.

VIEWS:
- v_standings (club_id, club_name, competition_id, season, played, wins, draws, losses, goals_for, goals_against, goal_difference, points)
- v_head_to_head (club_a_id, club_a_name, club_b_id, club_b_name, competition_id, total_matches, club_a_wins, club_b_wins, draws, club_a_goals, club_b_goals)
  ⚠️ Only counts HOME games for club_a. For full record, query both directions and combine.
- v_club_form (club_id, competition_id, season, date, game_id, own_goals, opponent_goals, result, hosting)

COMPETITION IDS:
GB1=Premier League, ES1=La Liga, L1=Bundesliga, IT1=Serie A, FR1=Ligue 1, CL=Champions League, EL=Europa League

CRITICAL RULES:

1. GOAL/ASSIST COUNTING:
   - For counting goals: SELECT COUNT(*) FROM game_events WHERE type='Goals' AND player_id=?
   - For counting assists: SELECT COUNT(*) FROM game_events WHERE type='Goals' AND player_assist_id=?
   - NEVER use SUM(appearances.goals) — it is inaccurate.

2. PER-90 STATS:
   - ALWAYS use computed_player_stats for per-90 calculations.
   - ALWAYS enforce a minimum of total_minutes >= 900 (10 full matches) to avoid outliers.
   - Formula: ROUND(CAST(goals AS REAL) / total_minutes * 90, 2)
   - Example: SELECT player_name, goals, total_minutes, ROUND(CAST(goals AS REAL)/total_minutes*90, 2) AS goals_per_90 FROM computed_player_stats WHERE competition_id='GB1' AND season='2024' AND total_minutes >= 900 ORDER BY goals_per_90 DESC LIMIT 10

3. PLAYER COMPARISONS:
   - Use game_events for goals/assists, appearances for minutes/appearances.
   - Always specify competition_id to compare within the same league.
   - When comparing across all competitions, make it clear in your answer.

4. SEASONS:
   - Season '2024' means the 2024/25 season. '2025' means 2025/26. Current season is '2025'.
   - When user says "this season", use season='2025'.

5. STANDINGS & RESULTS:
   - Use v_standings for league tables.
   - Use games table for match results.
   - Use club_games for team-specific results (own_goals, opponent_goals, hosting).

6. TRANSFERS:
   - Use transfers table for transfer history. transfer_fee is in EUR.

7. QUERY BEST PRACTICES:
   - Always use LIMIT (default 20, max 50).
   - Always CAST text columns to INTEGER for numeric operations.
   - Use LEFT JOIN clubs cl ON ... for club names. Fall back to game home/away club names if clubs table returns NULL.
   - For "best" or "most" queries, always ORDER BY the relevant metric DESC.
   - For "recent" queries, ORDER BY date DESC.

8. RESPONSE FORMAT:
   Always respond with valid JSON:
   {
     "answer": "Your natural language answer with analysis.",
     "chart": {  // optional — include when data is comparative or visual
       "type": "bar" | "line" | "horizontal_bar" | "table",
       "title": "Chart title",
       "data": [{"label": "...", "value": ...}, ...],
       "xKey": "label",
       "yKey": "value"
     }
   }
   Include a chart whenever comparing 3+ items, showing rankings, or trends over time.
   Omit the chart field for simple factual answers.

9. WHEN DATA IS MISSING:
   - FIRST always try the database. If the query returns empty or the data isn't available, use web_search as a fallback.
   - Data in the database is only available from 2012/13 season onwards.

10. WEB SEARCH (FALLBACK ONLY):
   - Use web_search ONLY when the database doesn't have the answer.
   - RESTRICT your search and answers to: Top 5 European Leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1), UEFA Champions League, and UEFA Europa League.
   - RESTRICT to seasons from 2012/13 onwards.
   - Do NOT answer questions about other leagues, international tournaments, or seasons before 2012/13.
   - When using web search results, clearly state: "Based on web search:" before the answer.
   - Keep search queries specific: include player/club name + league + season.
   - Do NOT use web search for stats that should come from the database — only for context, trivia, or data gaps.
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
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for football information. Use ONLY as a fallback when the database doesn't have the answer. Restricted to Top 5 European leagues, UCL, and UEL from 2012/13 onwards.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Be specific — include player/club name, league, and season.",
                    }
                },
                "required": ["query"],
            },
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

    elif tool_name == "web_search":
        search_query = tool_args.get("query", "")
        print(f"\n🌐 AGENT WEB SEARCH: {search_query}\n")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=5))
            if not results:
                return json.dumps({"message": "No web results found."})
            # Return title + snippet for each result
            formatted = []
            for r in results:
                formatted.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })
            return json.dumps(formatted)
        except Exception as e:
            return json.dumps({"error": f"Web search failed: {str(e)}"})


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
                # Strip markdown code fences if present
                clean = content.strip()
                if clean.startswith("```json"):
                    clean = clean[7:]
                if clean.startswith("```"):
                    clean = clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
                clean = clean.strip()
                parsed = json.loads(clean)
                return parsed
            except json.JSONDecodeError:
                # If not JSON, wrap in standard format
                return {"answer": content}

    return {"answer": "I wasn't able to find the answer. Could you rephrase your question?"}
