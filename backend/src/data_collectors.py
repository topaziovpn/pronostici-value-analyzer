import urllib.request
import urllib.error
import json
from datetime import datetime


class DataCollector:
    def __init__(self):
        self.espn_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    # ---------- parsing quote robusto ----------
    @staticmethod
    def _to_dec(am_odds):
        """Americane -> decimali. Accetta intero diretto, dict nidificato, None."""
        if am_odds is None:
            return None
        if isinstance(am_odds, dict):
            am_odds = am_odds.get('close', am_odds)
            if isinstance(am_odds, dict):
                am_odds = am_odds.get('odds')
        try:
            o = int(am_odds)
        except (TypeError, ValueError):
            return None
        if o == 0:
            return None
        return round((o / 100) + 1, 2) if o > 0 else round((100 / abs(o)) + 1, 2)

    @staticmethod
    def _get_ml(ml, key):
        v = ml.get(key) if isinstance(ml, dict) else None
        if isinstance(v, dict):
            v = v.get('close', v)
            if isinstance(v, dict):
                v = v.get('odds')
        return v

    def fetch_todays_matches(self, date_str=None):
        try:
            url = self.espn_url
            if date_str:
                query_date = date_str.replace("-", "")
                if len(query_date) != 8 or not query_date.isdigit():
                    raise ValueError(f"Formato data non valido: {date_str}")
                url += f"?dates={query_date}"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
            matches = []
            for ev in data.get('events', []):
                try:
                    comp = ev['competitions'][0]
                    c0, c1 = comp['competitors'][0], comp['competitors'][1]
                    home = c0 if c0['homeAway'] == 'home' else c1
                    away = c1 if home is c0 else c0
                    home_team = home['team']['name']
                    away_team = away['team']['name']

                    odds_dict = {"1": None, "X": None, "2": None}
                    odds_data = comp.get('odds', [])
                    if odds_data and isinstance(odds_data[0], dict):
                        odds_dict['provider'] = odds_data[0].get('provider', {}).get('name', 'Unknown')
                        ml = odds_data[0].get('moneyline', {}) or {}
                        odds_dict['1'] = self._to_dec(self._get_ml(ml, 'home'))
                        odds_dict['2'] = self._to_dec(self._get_ml(ml, 'away'))
                        odds_dict['X'] = self._to_dec(self._get_ml(ml, 'draw'))

                        tot = odds_data[0].get('total', {}) or {}
                        over, under = tot.get('over'), tot.get('under')
                        line, o_o, u_o = "2.5", None, None
                        if isinstance(over, dict):
                            close_o = over.get('close', over)
                            if isinstance(close_o, dict):
                                line = str(close_o.get('line', 'o2.5'))
                                o_o = self._to_dec(close_o.get('odds'))
                        if isinstance(under, dict):
                            close_u = under.get('close', under)
                            if isinstance(close_u, dict):
                                u_o = self._to_dec(close_u.get('odds'))
                        for tag in ("1.5", "2.5", "3.5"):
                            if tag in line:
                                odds_dict[f'O {tag}'] = o_o
                                odds_dict[f'U {tag}'] = u_o
                                break

                    matches.append({
                        "match_id": f"{home_team} - {away_team}",
                        "home_team": home_team,
                        "away_team": away_team,
                        "league": ev['season']['slug'] if 'season' in ev else "League",
                        "start_time": comp['startDate'],
                        "status": comp['status']['type']['state'],
                        "completed": comp['status']['type'].get('completed', False),
                        "time_detail": comp['status']['type'].get('shortDetail', ''),
                        "home_score": int(home.get('score', 0)),
                        "away_score": int(away.get('score', 0)),
                        "odds": odds_dict,
                    })
                except Exception as e:
                    print(f"Exception in match: {e}")
            return matches
        except urllib.error.HTTPError as e:
            print(f"[SCRAPER] ESPN HTTP {e.code}: verifica rete/API e data richiesta")
            return []
        except Exception as e:
            print(f"[SCRAPER] Errore fetch matches: {e}")
            return []

    def fetch_match_stats(self, home_team, away_team, odds=None, league_slug=None):
        from advanced_scraper import AdvancedScraper
        if not hasattr(self, 'advanced_scraper'):
            self.advanced_scraper = AdvancedScraper()
        return self.advanced_scraper.get_real_stats(home_team, away_team, league_slug, odds)