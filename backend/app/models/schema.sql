-- ============================================================
-- Football Diary — SQLite Schema
-- Based on dcaribou/transfermarkt-datasets (10 CSV tables)
-- ============================================================

-- ============================================================
-- LAYER 1: RAW TABLES (mirror the CSVs exactly)
-- ============================================================

CREATE TABLE IF NOT EXISTS competitions (
    competition_id   TEXT PRIMARY KEY,
    competition_code TEXT,
    name             TEXT NOT NULL,
    sub_type         TEXT,            -- e.g. 'first_tier', 'cup'
    type             TEXT,            -- 'domestic_league', 'international_cup', etc.
    country_id       INTEGER,
    country_name     TEXT,
    domestic_league_code TEXT,
    confederation    TEXT,
    url              TEXT
);

CREATE TABLE IF NOT EXISTS clubs (
    club_id                INTEGER PRIMARY KEY,
    club_code              TEXT,
    name                   TEXT NOT NULL,
    domestic_competition_id TEXT REFERENCES competitions(competition_id),
    total_market_value     REAL,
    squad_size             INTEGER,
    average_age            REAL,
    foreigners_number      INTEGER,
    foreigners_percentage  REAL,
    national_team_players  INTEGER,
    stadium_name           TEXT,
    stadium_seats          INTEGER,
    net_transfer_record    TEXT,
    coach_name             TEXT,
    last_season            INTEGER,
    url                    TEXT
);

CREATE TABLE IF NOT EXISTS players (
    player_id              INTEGER PRIMARY KEY,
    first_name             TEXT,
    last_name              TEXT,
    name                   TEXT NOT NULL,
    last_season            INTEGER,
    current_club_id        INTEGER REFERENCES clubs(club_id),
    player_code            TEXT,
    country_of_birth       TEXT,
    city_of_birth          TEXT,
    country_of_citizenship TEXT,
    date_of_birth          DATE,
    sub_position           TEXT,
    position               TEXT,           -- 'Attack', 'Midfield', 'Defender', 'Goalkeeper'
    foot                   TEXT,           -- 'right', 'left', 'both'
    height_in_cm           INTEGER,
    market_value_in_eur    REAL,
    highest_market_value_in_eur REAL,
    contract_expiration_date DATE,
    agent_name             TEXT,
    image_url              TEXT,
    url                    TEXT,
    current_club_domestic_competition_id TEXT,
    current_club_name      TEXT
);

CREATE TABLE IF NOT EXISTS games (
    game_id               INTEGER PRIMARY KEY,
    competition_id        TEXT REFERENCES competitions(competition_id),
    season                INTEGER NOT NULL,      -- e.g. 2023
    round                 TEXT,                   -- 'Matchday 1', 'Quarter-Finals', etc.
    date                  DATE,
    home_club_id          INTEGER REFERENCES clubs(club_id),
    away_club_id          INTEGER REFERENCES clubs(club_id),
    home_club_goals       INTEGER,
    away_club_goals       INTEGER,
    home_club_position    INTEGER,
    away_club_position    INTEGER,
    home_club_manager_name TEXT,
    away_club_manager_name TEXT,
    stadium               TEXT,
    attendance            INTEGER,
    referee               TEXT,
    url                   TEXT,
    home_club_name        TEXT,
    away_club_name        TEXT,
    aggregate             TEXT,                   -- for two-legged ties
    competition_type      TEXT                    -- 'domestic_league', 'international_cup', etc.
);

CREATE TABLE IF NOT EXISTS appearances (
    appearance_id          TEXT PRIMARY KEY,
    game_id                INTEGER NOT NULL REFERENCES games(game_id),
    player_id              INTEGER NOT NULL REFERENCES players(player_id),
    player_club_id         INTEGER REFERENCES clubs(club_id),
    player_current_club_id INTEGER,
    date                   DATE,
    player_name            TEXT,
    competition_id         TEXT REFERENCES competitions(competition_id),
    yellow_cards           INTEGER DEFAULT 0,
    red_cards              INTEGER DEFAULT 0,
    goals                  INTEGER DEFAULT 0,
    assists                INTEGER DEFAULT 0,
    minutes_played         INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player_valuations (
    player_id         INTEGER NOT NULL REFERENCES players(player_id),
    date              DATE NOT NULL,
    market_value_in_eur REAL,
    current_club_id   INTEGER REFERENCES clubs(club_id),
    player_club_domestic_competition_id TEXT,
    PRIMARY KEY (player_id, date)
);

CREATE TABLE IF NOT EXISTS club_games (
    club_id           INTEGER NOT NULL REFERENCES clubs(club_id),
    game_id           INTEGER NOT NULL REFERENCES games(game_id),
    opponent_id       INTEGER REFERENCES clubs(club_id),
    opponent_goals    INTEGER,
    own_goals         INTEGER,
    own_position      INTEGER,
    opponent_position INTEGER,
    own_manager_name  TEXT,
    opponent_manager_name TEXT,
    hosting           TEXT,              -- 'Home' or 'Away'
    is_win            INTEGER,           -- 1 = win, 0 = not
    PRIMARY KEY (club_id, game_id)
);

CREATE TABLE IF NOT EXISTS game_events (
    game_id           INTEGER NOT NULL REFERENCES games(game_id),
    minute            INTEGER,
    type              TEXT,              -- 'Goals', 'Cards', 'Substitutions'
    club_id           INTEGER REFERENCES clubs(club_id),
    player_id         INTEGER REFERENCES players(player_id),
    description       TEXT,
    player_in_id      INTEGER,           -- for substitutions
    player_assist_id  INTEGER
);

CREATE TABLE IF NOT EXISTS game_lineups (
    game_id           INTEGER NOT NULL REFERENCES games(game_id),
    club_id           INTEGER NOT NULL REFERENCES clubs(club_id),
    player_id         INTEGER NOT NULL REFERENCES players(player_id),
    type              TEXT,              -- 'starting_lineup' or 'substitutes'
    position          TEXT,
    number            INTEGER,
    player_name       TEXT,
    team_captain      INTEGER DEFAULT 0,
    PRIMARY KEY (game_id, club_id, player_id)
);

CREATE TABLE IF NOT EXISTS transfers (
    player_id              INTEGER NOT NULL REFERENCES players(player_id),
    transfer_date          DATE,
    transfer_season        INTEGER,
    from_club_id           INTEGER,
    to_club_id             INTEGER,
    from_club_name         TEXT,
    to_club_name           TEXT,
    transfer_fee           REAL,
    market_value_in_eur    REAL,
    player_name            TEXT
);


-- ============================================================
-- LAYER 2: INDEXES (critical for query performance)
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_games_competition    ON games(competition_id);
CREATE INDEX IF NOT EXISTS idx_games_season         ON games(season);
CREATE INDEX IF NOT EXISTS idx_games_date           ON games(date);
CREATE INDEX IF NOT EXISTS idx_games_home_club      ON games(home_club_id);
CREATE INDEX IF NOT EXISTS idx_games_away_club      ON games(away_club_id);

CREATE INDEX IF NOT EXISTS idx_appearances_game     ON appearances(game_id);
CREATE INDEX IF NOT EXISTS idx_appearances_player   ON appearances(player_id);
CREATE INDEX IF NOT EXISTS idx_appearances_club     ON appearances(player_club_id);
CREATE INDEX IF NOT EXISTS idx_appearances_comp     ON appearances(competition_id);

CREATE INDEX IF NOT EXISTS idx_events_game          ON game_events(game_id);
CREATE INDEX IF NOT EXISTS idx_events_player        ON game_events(player_id);
CREATE INDEX IF NOT EXISTS idx_events_type          ON game_events(type);

CREATE INDEX IF NOT EXISTS idx_lineups_game         ON game_lineups(game_id);
CREATE INDEX IF NOT EXISTS idx_lineups_player       ON game_lineups(player_id);

CREATE INDEX IF NOT EXISTS idx_valuations_player    ON player_valuations(player_id);
CREATE INDEX IF NOT EXISTS idx_valuations_date      ON player_valuations(date);

CREATE INDEX IF NOT EXISTS idx_club_games_club      ON club_games(club_id);
CREATE INDEX IF NOT EXISTS idx_club_games_opponent  ON club_games(opponent_id);

CREATE INDEX IF NOT EXISTS idx_transfers_player     ON transfers(player_id);
CREATE INDEX IF NOT EXISTS idx_transfers_to_club    ON transfers(to_club_id);
CREATE INDEX IF NOT EXISTS idx_transfers_from_club  ON transfers(from_club_id);

CREATE INDEX IF NOT EXISTS idx_players_club         ON players(current_club_id);
CREATE INDEX IF NOT EXISTS idx_players_position     ON players(position);
CREATE INDEX IF NOT EXISTS idx_players_country      ON players(country_of_citizenship);


-- ============================================================
-- LAYER 3: DERIVED VIEWS (power the analytics & AI agent)
-- ============================================================

-- 3a. HEAD-TO-HEAD: club vs club across all competitions
CREATE VIEW IF NOT EXISTS v_head_to_head AS
SELECT
    g.home_club_id   AS club_a_id,
    g.home_club_name AS club_a_name,
    g.away_club_id   AS club_b_id,
    g.away_club_name AS club_b_name,
    g.competition_id,
    c.name           AS competition_name,
    COUNT(*)         AS total_matches,
    SUM(CASE WHEN g.home_club_goals > g.away_club_goals THEN 1 ELSE 0 END)  AS club_a_wins,
    SUM(CASE WHEN g.home_club_goals < g.away_club_goals THEN 1 ELSE 0 END)  AS club_b_wins,
    SUM(CASE WHEN g.home_club_goals = g.away_club_goals THEN 1 ELSE 0 END)  AS draws,
    SUM(g.home_club_goals) AS club_a_goals,
    SUM(g.away_club_goals) AS club_b_goals
FROM games g
JOIN competitions c ON g.competition_id = c.competition_id
GROUP BY g.home_club_id, g.away_club_id, g.competition_id;


-- 3b. PLAYER CAREER STATS: aggregated per player per competition per season
CREATE VIEW IF NOT EXISTS v_player_season_stats AS
SELECT
    a.player_id,
    a.player_name,
    a.competition_id,
    g.season,
    a.player_club_id                         AS club_id,
    cl.name                                  AS club_name,
    COUNT(DISTINCT a.game_id)                AS appearances,
    SUM(a.goals)                             AS goals,
    SUM(a.assists)                           AS assists,
    SUM(a.goals) + SUM(a.assists)            AS goal_contributions,
    SUM(a.minutes_played)                    AS total_minutes,
    SUM(a.yellow_cards)                      AS yellow_cards,
    SUM(a.red_cards)                         AS red_cards,
    -- Per 90 metrics
    CASE
        WHEN SUM(a.minutes_played) > 0
        THEN ROUND(CAST(SUM(a.goals) AS REAL) / SUM(a.minutes_played) * 90, 2)
        ELSE 0
    END AS goals_per_90,
    CASE
        WHEN SUM(a.minutes_played) > 0
        THEN ROUND(CAST(SUM(a.assists) AS REAL) / SUM(a.minutes_played) * 90, 2)
        ELSE 0
    END AS assists_per_90,
    CASE
        WHEN SUM(a.minutes_played) > 0
        THEN ROUND(CAST(SUM(a.goals) + SUM(a.assists) AS REAL) / SUM(a.minutes_played) * 90, 2)
        ELSE 0
    END AS contributions_per_90
FROM appearances a
JOIN games g ON a.game_id = g.game_id
LEFT JOIN clubs cl ON a.player_club_id = cl.club_id
GROUP BY a.player_id, a.player_name, a.competition_id, g.season, a.player_club_id;


-- 3c. PLAYER WIN RATE: win rate when player starts vs comes off bench
CREATE VIEW IF NOT EXISTS v_player_impact AS
SELECT
    a.player_id,
    a.player_name,
    g.season,
    a.competition_id,
    -- Started (played >= 45 minutes as proxy for starting)
    COUNT(CASE WHEN a.minutes_played >= 45 THEN 1 END)  AS games_started,
    COUNT(CASE WHEN a.minutes_played >= 45
               AND ((cg.hosting = 'Home' AND g.home_club_goals > g.away_club_goals)
                 OR (cg.hosting = 'Away' AND g.away_club_goals > g.home_club_goals))
          THEN 1 END)                                    AS wins_when_started,
    -- Sub appearances (played < 45 minutes)
    COUNT(CASE WHEN a.minutes_played > 0 AND a.minutes_played < 45 THEN 1 END) AS games_as_sub,
    COUNT(CASE WHEN a.minutes_played > 0 AND a.minutes_played < 45
               AND ((cg.hosting = 'Home' AND g.home_club_goals > g.away_club_goals)
                 OR (cg.hosting = 'Away' AND g.away_club_goals > g.home_club_goals))
          THEN 1 END)                                    AS wins_as_sub
FROM appearances a
JOIN games g ON a.game_id = g.game_id
JOIN club_games cg ON cg.game_id = g.game_id AND cg.club_id = a.player_club_id
GROUP BY a.player_id, a.player_name, g.season, a.competition_id;


-- 3d. CLUB FORM: recent results per club per competition
CREATE VIEW IF NOT EXISTS v_club_form AS
SELECT
    cg.club_id,
    cl.name AS club_name,
    g.competition_id,
    g.season,
    g.date,
    g.game_id,
    cg.own_goals,
    cg.opponent_goals,
    cg.opponent_id,
    CASE
        WHEN cg.own_goals > cg.opponent_goals THEN 'W'
        WHEN cg.own_goals < cg.opponent_goals THEN 'L'
        ELSE 'D'
    END AS result,
    cg.hosting
FROM club_games cg
JOIN games g ON cg.game_id = g.game_id
JOIN clubs cl ON cg.club_id = cl.club_id
ORDER BY cg.club_id, g.date DESC;


-- 3e. COMPETITION STANDINGS: points table per season
CREATE VIEW IF NOT EXISTS v_standings AS
SELECT
    cg.club_id,
    cl.name                                  AS club_name,
    g.competition_id,
    g.season,
    COUNT(*)                                 AS played,
    SUM(CASE WHEN cg.own_goals > cg.opponent_goals THEN 1 ELSE 0 END)  AS wins,
    SUM(CASE WHEN cg.own_goals = cg.opponent_goals THEN 1 ELSE 0 END)  AS draws,
    SUM(CASE WHEN cg.own_goals < cg.opponent_goals THEN 1 ELSE 0 END)  AS losses,
    SUM(cg.own_goals)                        AS goals_for,
    SUM(cg.opponent_goals)                   AS goals_against,
    SUM(cg.own_goals) - SUM(cg.opponent_goals) AS goal_difference,
    SUM(CASE WHEN cg.own_goals > cg.opponent_goals THEN 3
             WHEN cg.own_goals = cg.opponent_goals THEN 1
             ELSE 0 END)                     AS points
FROM club_games cg
JOIN games g ON cg.game_id = g.game_id
JOIN clubs cl ON cg.club_id = cl.club_id
WHERE g.competition_type = 'domestic_league'
GROUP BY cg.club_id, g.competition_id, g.season
ORDER BY points DESC, goal_difference DESC, goals_for DESC;


-- 3f. TOP SCORERS: per competition per season
CREATE VIEW IF NOT EXISTS v_top_scorers AS
SELECT
    a.player_id,
    a.player_name,
    p.position,
    p.country_of_citizenship,
    a.player_club_id                    AS club_id,
    cl.name                             AS club_name,
    a.competition_id,
    g.season,
    SUM(a.goals)                        AS goals,
    SUM(a.assists)                      AS assists,
    SUM(a.goals) + SUM(a.assists)       AS goal_contributions,
    COUNT(DISTINCT a.game_id)           AS appearances,
    SUM(a.minutes_played)               AS minutes_played
FROM appearances a
JOIN games g ON a.game_id = g.game_id
JOIN players p ON a.player_id = p.player_id
LEFT JOIN clubs cl ON a.player_club_id = cl.club_id
GROUP BY a.player_id, a.competition_id, g.season
HAVING SUM(a.goals) > 0
ORDER BY goals DESC;


-- ============================================================
-- LAYER 4: METADATA TABLE (for data pipeline health tracking)
-- ============================================================

CREATE TABLE IF NOT EXISTS _etl_metadata (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name    TEXT NOT NULL,
    rows_loaded   INTEGER,
    loaded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_hash   TEXT,                -- checksum of source CSV
    status        TEXT DEFAULT 'success'  -- 'success' or 'failed'
);
