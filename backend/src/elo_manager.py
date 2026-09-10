"""
Sistema Elo dinamico per calcio.
- Rating persistente in SQLite (sopravvive ai riavvii)
- Tier di bootstrap per squadre mai viste
- Aggiornamento automatico a fine partita
- Export rating come feature per stats_engine
"""

import sqlite3
import math
import json
import os
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "predictions.db")

TIER_RATINGS = {
    "eng.1": 1650,   # Premier League
    "esp.1": 1620,   # La Liga
    "ita.1": 1620,   # Serie A
    "ger.1": 1620,   # Bundesliga
    "fra.1": 1580,   # Ligue 1
    "ned.1": 1520,
    "por.1": 1520,
    "tur.1": 1500,
    "bel.1": 1480,
    "sco.1": 1460,
    "rus.1": 1460,
    "ukr.1": 1450,
    "gre.1": 1440,
    "aut.1": 1430,
    "sui.1": 1430,
    "den.1": 1420,
    "nor.1": 1400,
    "swe.1": 1400,
    "cze.1": 1400,
    "pol.1": 1390,
    "rou.1": 1380,
    "cro.1": 1380,
    "ser.1": 1380,
    "eng.2": 1400,
    "esp.2": 1380,
    "ita.2": 1370,
    "ger.2": 1380,
    "fra.2": 1350,
    "ger.3": 1300,
    "usa.1": 1400,
    "bra.1": 1500,
    "arg.1": 1480,
    "mex.1": 1420,
    "uefa.champions": 1700,
    "uefa.europa": 1600,
    "uefa.conference": 1500,
}

ELITE_CLUBS = {
    "real madrid": +180, "barcelona": +170, "atletico madrid": +100,
    "manchester city": +180, "arsenal": +140, "liverpool": +150,
    "manchester united": +80, "chelsea": +90, "tottenham": +60,
    "bayern munich": +200, "borussia dortmund": +100, "bayer leverkusen": +90,
    "rb leipzig": +60,
    "inter milan": +130, "internazionale": +130, "ac milan": +100,
    "juventus": +110, "napoli": +100, "atalanta": +80, "roma": +60, "lazio": +50,
    "paris saint-germain": +180, "psg": +180,
    "ajax": +80, "psv eindhoven": +60, "feyenoord": +50,
    "benfica": +80, "porto": +70, "sporting cp": +60,
    "galatasaray": +50, "fenerbahce": +40, "besiktas": +30,
    "flamengo": +80, "palmeiras": +70, "boca juniors": +60, "river plate": +60,
}

BASE_K = 20
HOME_ADVANTAGE = 65
GOAL_DIFF_WEIGHT = True
SEASON_REGRESSION = 0.10
MEAN_RATING = 1500

class EloManager:
    def __init__(self, db_path=None, conn=None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._shared_conn = conn
        self._ensure_table()

    def _get_conn(self):
        if self._shared_conn:
            return self._shared_conn
        return sqlite3.connect(self.db_path, timeout=60.0)

    def _close_conn(self, conn):
        if not self._shared_conn and conn:
            try: conn.close()
            except: pass

    def _ensure_table(self):
        conn = self._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS elo_ratings (
                team_name TEXT PRIMARY KEY,
                rating REAL NOT NULL DEFAULT 1500,
                matches_played INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                goals_for INTEGER NOT NULL DEFAULT 0,
                goals_against INTEGER NOT NULL DEFAULT 0,
                league TEXT,
                last_match_date TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS elo_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                match_id TEXT,
                rating_before REAL,
                rating_after REAL,
                rating_change REAL,
                opponent TEXT,
                result TEXT,
                match_date TEXT,
                created_at TEXT
            )
        ''')
        conn.commit()
        self._close_conn(conn)

    @staticmethod
    def normalize_name(name):
        if not name:
            return ""
        n = name.strip().lower()
        aliases = {
            "inter milan": "internazionale",
            "inter": "internazionale",
            "fc internazionale milano": "internazionale",
            "man city": "manchester city",
            "man utd": "manchester united",
            "man united": "manchester united",
            "spurs": "tottenham",
            "tottenham hotspur": "tottenham",
            "atletico de madrid": "atletico madrid",
            "atlético madrid": "atletico madrid",
            "atlético de madrid": "atletico madrid",
            "fc barcelona": "barcelona",
            "fc bayern munich": "bayern munich",
            "fc bayern münchen": "bayern munich",
            "bayern münchen": "bayern munich",
            "borussia mönchengladbach": "monchengladbach",
            "paris saint germain": "paris saint-germain",
            "paris sg": "paris saint-germain",
            "ac milan": "ac milan",
            "milan": "ac milan",
            "as roma": "roma",
            "ss lazio": "lazio",
            "ssc napoli": "napoli",
        }
        return aliases.get(n, n)

    @staticmethod
    def _map_league_code(league):
        if not league: return None
        slug = str(league).lower()
        
        # Tier 1 & Second Divisions
        if "premier" in slug or "eng.1" in slug or "english" in slug:
            if "championship" in slug or "eng.2" in slug: return "eng.2"
            return "eng.1"
        if "serie-a" in slug or "italian-serie-a" in slug or "ita.1" in slug: return "ita.1"
        if "laliga" in slug or "spanish-laliga" in slug or "esp.1" in slug:
            if "secunda" in slug or "esp.2" in slug or "hypermotion" in slug: return "esp.2"
            return "esp.1"
        if "bundesliga" in slug or "german-bundesliga" in slug or "ger.1" in slug:
            if "2." in slug or "ger.2" in slug: return "ger.2"
            if "3." in slug or "ger.3" in slug: return "ger.3"
            return "ger.1"
        if "ligue-1" in slug or "french-ligue-1" in slug or "fra.1" in slug: return "fra.1"
        if "ligue-2" in slug or "fra.2" in slug: return "fra.2"
        if "serie-b" in slug or "ita.2" in slug: return "ita.2"
        
        # Tier 2
        if "eredivisie" in slug or "ned.1" in slug or "dutch" in slug: return "ned.1"
        if "primeira" in slug or "por.1" in slug or "portuguese" in slug: return "por.1"
        if "super-lig" in slug or "tur.1" in slug or "turkish" in slug: return "tur.1"
        if "pro-league" in slug or "bel.1" in slug or "belgian" in slug: return "bel.1"
        if "premiership" in slug or "sco.1" in slug or "scottish" in slug: return "sco.1"
        if "russian" in slug or "rus.1" in slug: return "rus.1"
        if "ukrainian" in slug or "ukr.1" in slug: return "ukr.1"
        if "greek" in slug or "gre.1" in slug: return "gre.1"
        
        # Tier 3
        if "austrian" in slug or "aut.1" in slug: return "aut.1"
        if "swiss" in slug or "sui.1" in slug: return "sui.1"
        if "danish" in slug or "den.1" in slug: return "den.1"
        if "eliteserien" in slug or "nor.1" in slug or "norwegian" in slug: return "nor.1"
        if "allsvenskan" in slug or "swe.1" in slug or "swedish" in slug: return "swe.1"
        if "czech" in slug or "cze.1" in slug: return "cze.1"
        if "ekstraklasa" in slug or "pol.1" in slug or "polish" in slug: return "pol.1"
        if "romanian" in slug or "rou.1" in slug: return "rou.1"
        if "croatian" in slug or "cro.1" in slug: return "cro.1"
        if "serbian" in slug or "ser.1" in slug: return "ser.1"
        
        # Tier 5 Americas & World
        if "brasileirao" in slug or "bra.1" in slug or "brazil" in slug: return "bra.1"
        if "argentine" in slug or "arg.1" in slug or "argentina" in slug: return "arg.1"
        if "liga-mx" in slug or "mex.1" in slug or "mexican" in slug: return "mex.1"
        if "mls" in slug or "usa.1" in slug or "major-league" in slug: return "usa.1"
        if "saudi" in slug or "sau.1" in slug: return "sau.1"
        
        # Cups
        if "champions" in slug: return "uefa.champions"
        if "europa" in slug: return "uefa.europa"
        if "conference" in slug: return "uefa.conference"
        
        return None
    def _bootstrap_rating(self, team_name, league=None):
        norm = self.normalize_name(team_name)
        code = self._map_league_code(league)
        if not code:
            # Check team name hints for MLS, Liga MX, top European clubs
            if any(w in norm for w in ["austin", "philadelphia", "columbus", "lafc", "timbers", "dallas", "whitecaps", "sounders", "rapids", "earthquakes", "galaxy", "revolution", "fire", "dynamo", "nashville", "salt lake", "orlando", "toronto", "atlanta", "inter miami"]):
                code = "usa.1"
            elif any(w in norm for w in ["puebla", "santos", "cruz azul", "atlas", "tigres", "america", "monterrey", "chivas", "toluca", "pumas", "pachuca", "leon", "necaxa", "juarez", "queretaro", "tijuana"]):
                code = "mex.1"
        base = TIER_RATINGS.get(code, MEAN_RATING) if code else MEAN_RATING
        bonus = 0
        for club_key, club_bonus in ELITE_CLUBS.items():
            if club_key in norm or norm in club_key:
                bonus = club_bonus
                break
        return base + bonus

    def get_rating(self, team_name, league=None, conn=None):
        norm = self.normalize_name(team_name)
        c = conn or self._get_conn()
        row = c.execute(
            "SELECT rating, matches_played FROM elo_ratings WHERE team_name = ?",
            (norm,)
        ).fetchone()
        if not conn:
            self._close_conn(c)

        if row:
            return {"rating": row[0], "matches_played": row[1], "is_bootstrap": False}

        bootstrap = self._bootstrap_rating(team_name, league)
        self._create_team(norm, bootstrap, league, conn=conn)
        return {"rating": bootstrap, "matches_played": 0, "is_bootstrap": True}

    def _create_team(self, norm_name, rating, league=None, conn=None):
        now = datetime.utcnow().isoformat()
        c = conn or self._get_conn()
        c.execute('''
            INSERT OR IGNORE INTO elo_ratings
            (team_name, rating, matches_played, wins, draws, losses,
             goals_for, goals_against, league, created_at, updated_at)
            VALUES (?, ?, 0, 0, 0, 0, 0, 0, ?, ?, ?)
        ''', (norm_name, rating, league, now, now))
        if not conn:
            c.commit()
            self._close_conn(c)

    @staticmethod
    def expected_score(rating_a, rating_b, home_advantage=HOME_ADVANTAGE):
        dr = rating_a - rating_b + home_advantage
        return 1.0 / (1.0 + 10.0 ** (-dr / 400.0))

    @staticmethod
    def goal_diff_multiplier(goal_diff):
        gd = abs(goal_diff)
        if gd <= 1:
            return 1.0
        elif gd == 2:
            return 1.5
        elif gd == 3:
            return 1.75
        else:
            return 1.75 + (gd - 3) * 0.4

    def calculate_k(self, goal_diff, league=None):
        k = BASE_K
        if league and "uefa" in str(league).lower():
            k = 30
        if GOAL_DIFF_WEIGHT:
            k *= self.goal_diff_multiplier(goal_diff)
        return k

    def update_after_match(self, home_team, away_team, home_goals=None, away_goals=None,
                           league=None, match_id=None, match_date=None,
                           home_score=None, away_score=None):
        if home_goals is None and home_score is not None:
            home_goals = home_score
        if away_goals is None and away_score is not None:
            away_goals = away_score
        
        conn = self._get_conn()
        if match_id:
            row = conn.execute("SELECT id FROM elo_history WHERE match_id = ?", (match_id,)).fetchone()
            if row:
                self._close_conn(conn)
                return None

        h_norm = self.normalize_name(home_team)
        a_norm = self.normalize_name(away_team)

        h_data = self.get_rating(home_team, league, conn=conn)
        a_data = self.get_rating(away_team, league, conn=conn)

        r_h = h_data["rating"]
        r_a = a_data["rating"]

        if home_goals > away_goals:
            s_h, s_a = 1.0, 0.0
            result_h, result_a = "W", "L"
        elif home_goals < away_goals:
            s_h, s_a = 0.0, 1.0
            result_h, result_a = "L", "W"
        else:
            s_h, s_a = 0.5, 0.5
            result_h, result_a = "D", "D"

        e_h = self.expected_score(r_h, r_a, HOME_ADVANTAGE)
        e_a = 1.0 - e_h

        goal_diff = home_goals - away_goals
        k = self.calculate_k(goal_diff, league)

        delta_h = round(k * (s_h - e_h), 2)
        delta_a = round(k * (s_a - e_a), 2)

        new_r_h = round(r_h + delta_h, 2)
        new_r_a = round(r_a + delta_a, 2)

        now = datetime.utcnow().isoformat()
        date_str = match_date or now[:10]

        if result_h == "W":
            conn.execute('''
                UPDATE elo_ratings SET rating=?, matches_played=matches_played+1,
                wins=wins+1, goals_for=goals_for+?, goals_against=goals_against+?,
                league=COALESCE(?, league), last_match_date=?, updated_at=?
                WHERE team_name=?
            ''', (new_r_h, home_goals, away_goals, league, date_str, now, h_norm))
        elif result_h == "L":
            conn.execute('''
                UPDATE elo_ratings SET rating=?, matches_played=matches_played+1,
                losses=losses+1, goals_for=goals_for+?, goals_against=goals_against+?,
                league=COALESCE(?, league), last_match_date=?, updated_at=?
                WHERE team_name=?
            ''', (new_r_h, home_goals, away_goals, league, date_str, now, h_norm))
        else:
            conn.execute('''
                UPDATE elo_ratings SET rating=?, matches_played=matches_played+1,
                draws=draws+1, goals_for=goals_for+?, goals_against=goals_against+?,
                league=COALESCE(?, league), last_match_date=?, updated_at=?
                WHERE team_name=?
            ''', (new_r_h, home_goals, away_goals, league, date_str, now, h_norm))

        if result_a == "W":
            conn.execute('''
                UPDATE elo_ratings SET rating=?, matches_played=matches_played+1,
                wins=wins+1, goals_for=goals_for+?, goals_against=goals_against+?,
                league=COALESCE(?, league), last_match_date=?, updated_at=?
                WHERE team_name=?
            ''', (new_r_a, away_goals, home_goals, league, date_str, now, a_norm))
        elif result_a == "L":
            conn.execute('''
                UPDATE elo_ratings SET rating=?, matches_played=matches_played+1,
                losses=losses+1, goals_for=goals_for+?, goals_against=goals_against+?,
                league=COALESCE(?, league), last_match_date=?, updated_at=?
                WHERE team_name=?
            ''', (new_r_a, away_goals, home_goals, league, date_str, now, a_norm))
        else:
            conn.execute('''
                UPDATE elo_ratings SET rating=?, matches_played=matches_played+1,
                draws=draws+1, goals_for=goals_for+?, goals_against=goals_against+?,
                league=COALESCE(?, league), last_match_date=?, updated_at=?
                WHERE team_name=?
            ''', (new_r_a, away_goals, home_goals, league, date_str, now, a_norm))

        conn.execute('''
            INSERT INTO elo_history
            (team_name, match_id, rating_before, rating_after, rating_change,
             opponent, result, match_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (h_norm, match_id, r_h, new_r_h, delta_h, a_norm, result_h, date_str, now))

        conn.execute('''
            INSERT INTO elo_history
            (team_name, match_id, rating_before, rating_after, rating_change,
             opponent, result, match_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (a_norm, match_id, r_a, new_r_a, delta_a, h_norm, result_a, date_str, now))

        conn.commit()
        self._close_conn(conn)

        return {
            "home": {"before": r_h, "after": new_r_h, "delta": delta_h},
            "away": {"before": r_a, "after": new_r_a, "delta": delta_a}
        }

    def predict_match(self, home_team, away_team, league=None):
        h = self.get_rating(home_team, league)
        a = self.get_rating(away_team, league)

        r_h = h["rating"]
        r_a = a["rating"]
        dr = r_h - r_a + HOME_ADVANTAGE

        p_home_win_base = 1.0 / (1.0 + 10.0 ** (-dr / 400.0))

        draw_base = 0.28 * math.exp(-(dr ** 2) / (2 * 300 ** 2))
        p_draw = max(0.08, min(0.30, draw_base))

        remaining = 1.0 - p_draw
        p_home = remaining * p_home_win_base
        p_away = remaining * (1.0 - p_home_win_base)

        total = p_home + p_draw + p_away
        p_home /= total
        p_draw /= total
        p_away /= total

        min_matches = min(h["matches_played"], a["matches_played"])
        if min_matches >= 20:
            confidence = "high"
        elif min_matches >= 8:
            confidence = "medium"
        elif min_matches >= 3:
            confidence = "low"
        else:
            confidence = "bootstrap"

        return {
            "home_rating": round(r_h, 1),
            "away_rating": round(r_a, 1),
            "rating_diff": round(dr, 1),
            "elo_p_home": round(p_home, 4),
            "elo_p_draw": round(p_draw, 4),
            "elo_p_away": round(p_away, 4),
            "elo_confidence": confidence,
            "home_matches": h["matches_played"],
            "away_matches": a["matches_played"],
            "home_is_bootstrap": h["is_bootstrap"],
            "away_is_bootstrap": a["is_bootstrap"],
        }

    def apply_season_regression(self, league=None):
        conn = self._get_conn()
        if league:
            rows = conn.execute(
                "SELECT team_name, rating FROM elo_ratings WHERE league = ?", (league,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT team_name, rating FROM elo_ratings").fetchall()

        now = datetime.utcnow().isoformat()
        league_mean = sum(r[1] for r in rows) / len(rows) if rows else MEAN_RATING

        for name, rating in rows:
            new_rating = round(rating * (1 - SEASON_REGRESSION) + league_mean * SEASON_REGRESSION, 2)
            conn.execute(
                "UPDATE elo_ratings SET rating = ?, updated_at = ? WHERE team_name = ?",
                (new_rating, now, name)
            )

        conn.commit()
        conn.close()
        print(f"[ELO] Regressione stagionale applicata: {len(rows)} squadre, media lega {league_mean:.0f}")

    def get_rankings(self, league=None, limit=50):
        conn = self._get_conn()
        if league:
            rows = conn.execute('''
                SELECT team_name, rating, matches_played, wins, draws, losses,
                       goals_for, goals_against, last_match_date
                FROM elo_ratings WHERE league = ?
                ORDER BY rating DESC LIMIT ?
            ''', (league, limit)).fetchall()
        else:
            rows = conn.execute('''
                SELECT team_name, rating, matches_played, wins, draws, losses,
                       goals_for, goals_against, last_match_date
                FROM elo_ratings
                ORDER BY rating DESC LIMIT ?
            ''', (limit,)).fetchall()
        conn.close()

        return [{
            "rank": i + 1,
            "team": r[0],
            "rating": r[1],
            "played": r[2],
            "w": r[3], "d": r[4], "l": r[5],
            "gf": r[6], "ga": r[7],
            "last_match": r[8]
        } for i, r in enumerate(rows)]

    def get_strength_modifier(self, home_team, away_team, league=None):
        pred = self.predict_match(home_team, away_team, league)
        dr = pred["rating_diff"]

        home_mod = max(-0.50, min(0.50, dr * 0.001))
        away_mod = -home_mod

        return {
            "home_xg_modifier": round(home_mod, 3),
            "away_xg_modifier": round(away_mod, 3),
            "elo_prediction": pred
        }
