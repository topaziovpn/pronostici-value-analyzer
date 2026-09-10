import soccerdata as sd
import pandas as pd
import math
import difflib
from datetime import datetime

class AdvancedScraper:
    def __init__(self):
        self._cache = {}

    def _map_league(self, league_slug):
        if not league_slug: return None
        slug = league_slug.lower()
        if "premier-league" in slug or "eng.1" in slug: return "ENG-Premier League"
        if "serie-a" in slug or "ita.1" in slug: return "ITA-Serie A"
        if "laliga" in slug or "esp.1" in slug: return "ESP-La Liga"
        if "bundesliga" in slug or "ger.1" in slug: return "GER-Bundesliga"
        if "ligue-1" in slug or "fra.1" in slug: return "FRA-Ligue 1"
        return None

    def _derive_stats_from_odds(self, odds):
        if not odds or '1' not in odds or '2' not in odds: return None
        try:
            o1, ox, o2 = float(odds['1']), float(odds.get('X', 3.0)), float(odds['2'])
            if o1 <= 1.01 or o2 <= 1.01: return None
            
            p1, px, p2 = 1/o1, 1/ox, 1/o2
            vig = p1 + px + p2
            true_p1 = p1 / vig
            true_p2 = p2 / vig
            
            total_xg = 2.6
            xg_h = total_xg * (true_p1 / (true_p1 + true_p2)) + 0.2
            xg_a = total_xg * (true_p2 / (true_p1 + true_p2))
            
            return {
                "xg_a": round(xg_h, 2), "xg_b": round(xg_a, 2),
                "xg_against_a": round(xg_a, 2), "xg_against_b": round(xg_h, 2),
                "possession_a": round(true_p1 * 100), "possession_b": round(true_p2 * 100),
                "forma_a": round(min(15.0, max(3.0, (0.5) * 7.5)), 1), "forma_b": round(min(15.0, max(3.0, (0.5) * 7.5)), 1), "casa_trasf": 0.2, "btts_prob": 50,
                "angoli": 9.5, "cartellini": 4.5, "rigore_pct": 15,
                "h2h_home_wins": int(xg_h * 2.0), "h2h_away_wins": int(xg_a * 2.0),
                "h2h_draws": max(0, 5 - int(xg_h*2.0) - int(xg_a*2.0)),
                "missing_key_home": False, "missing_key_away": False,
                "data_quality": 40,
                "stats_source": "market_implied"
            }
        except: return None

    def get_real_stats(self, home_team, away_team, league_slug, odds=None):
        fallback = self._derive_stats_from_odds(odds)
        fbref_league = self._map_league(league_slug)
        
        if not fbref_league:
            return fallback

        # Fase 2 reale!
        if isinstance(self._cache.get(fbref_league), str) and self._cache.get(fbref_league) == "ERROR":
            return fallback

        try:
            if fbref_league not in self._cache:
                print(f"[ADVANCED] Scaricamento FBref per {fbref_league}...")
                current_year = datetime.now().year
                season = str(current_year if datetime.now().month >= 7 else current_year - 1)
                fbref = sd.FBref(leagues=fbref_league, seasons=season, headless=True)
                stats = fbref.read_team_season_stats(stat_type="standard")
                self._cache[fbref_league] = stats
                
            df = self._cache[fbref_league]
            df = df.reset_index()
            
            # Fuzzy match team names
            def find_team(tname, df):
                teams = df['team'].unique()
                matches = difflib.get_close_matches(tname, teams, n=1, cutoff=0.5)
                return matches[0] if matches else None
                
            h_match = find_team(home_team, df)
            a_match = find_team(away_team, df)
            
            if h_match and a_match:
                h_stats = df[df['team'] == h_match].iloc[0]
                a_stats = df[df['team'] == a_match].iloc[0]
                
                # Prendi gli xG per 90 (Expected Goals / 90)
                try: xg_h_real = float(h_stats[('Expected', 'xG')]) / float(h_stats[('Playing Time', '90s')])
                except: xg_h_real = 1.3
                
                try: xg_a_real = float(a_stats[('Expected', 'xG')]) / float(a_stats[('Playing Time', '90s')])
                except: xg_a_real = 1.3
                
                real_stats = {
                    "xg_a": round(xg_h_real + 0.2, 2), # +0.2 home advantage
                    "xg_b": round(xg_a_real, 2),
                    "possession_a": 50, "possession_b": 50,
                    "forma_a": round(min(15.0, max(3.0, (0.5) * 7.5)), 1), "forma_b": round(min(15.0, max(3.0, (0.5) * 7.5)), 1), "casa_trasf": 0.2, "btts_prob": 50,
                    "angoli": 9.5, "cartellini": 4.5, "rigore_pct": 15,
                    "h2h_home_wins": 1, "h2h_away_wins": 1, "h2h_draws": 1,
                    "missing_key_home": False, "missing_key_away": False,
                    "data_quality": 85
                }
                
                # Blending
                if fallback:
                    w = (85 - 40) / 60.0 # w = 0.75 per stats reali, 0.25 mercato
                    for k in ["xg_a", "xg_b"]:
                        real_stats[k] = round(real_stats[k] * w + fallback[k] * (1 - w), 2)
                
                return real_stats
        except Exception as e:
            print(f"[ADVANCED] Errore FBref per {fbref_league}: {e}")
            self._cache[fbref_league] = "ERROR" # Salva l'errore per non riprovare all'infinito!
            
        return fallback
