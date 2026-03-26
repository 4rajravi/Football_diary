import os
from dotenv import load_dotenv
import pathlib

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/football_diary.db")
DATA_BASE_URL = os.getenv(
    "DATA_BASE_URL",
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data",
)
ENV = os.getenv("ENV", "development")

# CSV table names matching the transfermarkt-datasets repo
CSV_TABLES = [
    "competitions",
    "clubs",
    "players",
    "games",
    "appearances",
    "player_valuations",
    "club_games",
    "game_events",
    "game_lineups",
    "transfers",
]

# Competitions to keep (filter after loading)
TARGET_COMPETITIONS = [
    "GB1",   # Premier League
    "ES1",   # La Liga
    "L1",    # Bundesliga
    "IT1",   # Serie A
    "FR1",   # Ligue 1
    "CL",    # Champions League
    "EL",    # Europa League
    "WC",    # FIFA World Cup
    "EURO",  # UEFA Euros
]
