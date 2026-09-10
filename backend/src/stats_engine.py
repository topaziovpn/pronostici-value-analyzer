import math
from data_collectors import DataCollector
from advanced_scraper import AdvancedScraper
from elo_manager import EloManager
from config import config

class StatsEngine:
    def __init__(self):
        self.scraper = AdvancedScraper()
        self.elo = EloManager()

    def _poisson(self, k, lamb):
        return (math.exp(-lamb) * (lamb ** k)) / math.factorial(k)

    def _calculate_fair_odd(self, prob):
        if prob <= 0: return 99.0
        return round(1 / prob, 2)

    def calculate_match_probabilities(self, xg_a, xg_b, rho=-0.1):
        exact_scores = {}
        MAX_GOALS = 9
        
        for i in range(MAX_GOALS):
            for j in range(MAX_GOALS):
                base_prob = self._poisson(i, xg_a) * self._poisson(j, xg_b)
                
                if i == 0 and j == 0:
                    prob = base_prob * (1 - (xg_a * xg_b * rho))
                elif i == 0 and j == 1:
                    prob = base_prob * (1 + (xg_a * rho))
                elif i == 1 and j == 0:
                    prob = base_prob * (1 + (xg_b * rho))
                elif i == 1 and j == 1:
                    prob = base_prob * (1 - rho)
                else:
                    prob = base_prob
                    
                exact_scores[f"{i}-{j}"] = prob

        total_prob = sum(exact_scores.values())
        for k in exact_scores: exact_scores[k] /= total_prob

        def p_sum(condition):
            return sum(p for score, p in exact_scores.items() if condition(int(score.split('-')[0]), int(score.split('-')[1])))

        prob_1 = p_sum(lambda h, a: h > a)
        prob_x = p_sum(lambda h, a: h == a)
        prob_2 = p_sum(lambda h, a: h < a)
        
        ou_probs = {}
        for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
            ou_probs[f"O {line}"] = p_sum(lambda h, a: h + a > line)
            ou_probs[f"U {line}"] = p_sum(lambda h, a: h + a < line)
            
        prob_gg = p_sum(lambda h, a: h > 0 and a > 0)
        prob_ng = 1 - prob_gg
        
        team_goals = {
            "Casa O 0.5": p_sum(lambda h, a: h >= 1),
            "Casa O 1.5": p_sum(lambda h, a: h >= 2),
            "Casa O 2.5": p_sum(lambda h, a: h >= 3),
            "Trasf O 0.5": p_sum(lambda h, a: a >= 1),
            "Trasf O 1.5": p_sum(lambda h, a: a >= 2),
        }

        multigols = {
            "MG 1-4": p_sum(lambda h, a: 1 <= h + a <= 4),
            "MG 2-5": p_sum(lambda h, a: 2 <= h + a <= 5),
            "MG 2-4": p_sum(lambda h, a: 2 <= h + a <= 4),
            "MG 1-3": p_sum(lambda h, a: 1 <= h + a <= 3),
            "MG 0-2": p_sum(lambda h, a: 0 <= h + a <= 2),
        }
        
        combos = {
            "1X + U 3.5": p_sum(lambda h, a: (h >= a) and (h + a <= 3)),
            "1X + U 2.5": p_sum(lambda h, a: (h >= a) and (h + a <= 2)),
            "1X + GG": p_sum(lambda h, a: (h >= a) and (h > 0 and a > 0)),
            "12 + O 1.5": p_sum(lambda h, a: (h != a) and (h + a >= 2)),
            "1X + O 1.5": p_sum(lambda h, a: (h >= a) and (h + a >= 2)),
            "1X + O 0.5": p_sum(lambda h, a: (h >= a) and (h + a >= 1)),
            "X2 + O 0.5": p_sum(lambda h, a: (a >= h) and (h + a >= 1)),
            "X2 + O 1.5": p_sum(lambda h, a: (a >= h) and (h + a >= 2)),
            "X2 + U 3.5": p_sum(lambda h, a: (a >= h) and (h + a <= 3)),
            "X2 + U 2.5": p_sum(lambda h, a: (a >= h) and (h + a <= 2)),
            "X2 + GG": p_sum(lambda h, a: (a >= h) and (h > 0 and a > 0)),
            "1 + O 1.5": p_sum(lambda h, a: (h > a) and (h + a >= 2)),
            "2 + O 1.5": p_sum(lambda h, a: (a > h) and (h + a >= 2)),
            "1 + GG": p_sum(lambda h, a: (h > a) and (h > 0 and a > 0)),
            "2 + GG": p_sum(lambda h, a: (a > h) and (h > 0 and a > 0)),
        }

        res = {
            "exact_scores": exact_scores,
            "1": prob_1, "X": prob_x, "2": prob_2,
            "1X": prob_1 + prob_x, "X2": prob_x + prob_2, "12": prob_1 + prob_2,
            "GG": prob_gg, "NG": prob_ng,
        }
        res.update(ou_probs)
        res.update(team_goals)
        res.update(multigols)
        res.update(combos)
        
        return res

    def _anchor_to_market(self, xg_h, xg_a, book_odds):
        target_line, mkt_over = None, None
        for line in (2.5, 1.5, 3.5):
            ok = book_odds.get(f"O {line}", 0) > 1.01 and book_odds.get(f"U {line}", 0) > 1.01
            if ok:
                so = 1/book_odds[f"O {line}"] + 1/book_odds[f"U {line}"]
                target_line, mkt_over = line, (1/book_odds[f"O {line}"]) / so
                break
        o1, ox, o2 = book_odds.get("1"), book_odds.get("X"), book_odds.get("2")
        mkt_draw = None
        if o1 and ox and o2 and all(v > 1.01 for v in (o1, ox, o2)):
            s = 1/o1 + 1/ox + 1/o2
            mkt_draw = (1/ox) / s
        if mkt_over is None and mkt_draw is None:
            return xg_h, xg_a, -0.1
        if mkt_over is not None:
            for _ in range(60):
                p = self.calculate_match_probabilities(xg_h, xg_a, rho=0.0)[f"O {target_line}"]
                f = (mkt_over / max(p, 1e-6)) ** 0.15
                xg_h *= f; xg_a *= f
        best_rho, best_err = -0.1, 9.9
        if mkt_draw is not None:
            for i in range(-20, 21, 2):
                r = i / 100
                err = abs(self.calculate_match_probabilities(xg_h, xg_a, rho=r)["X"] - mkt_draw)
                if err < best_err:
                    best_err, best_rho = err, r
        return xg_h, xg_a, best_rho

    def calculate_metrics(self, match):
        team_a = match['home_team']
        team_b = match['away_team']
        odds = match.get('odds', {})
        league_slug = match.get('league', None)
        
        stats = self.scraper.get_real_stats(team_a, team_b, league_slug, odds)
        
        if not stats:
            return {
                "teamA": team_a, "teamB": team_b, "no_bet": True, "data_quality": 0,
                "best_exact_score": "N/D", "bookmaker_odds": odds, "probs": {}
            }
            
        xg_a = stats.get('xg_a', stats.get('xg_home', 1.3))
        xg_b = stats.get('xg_b', stats.get('xg_away', 1.3))
        data_quality = stats.get('data_quality', 50)
        
        # ELO MODIFIER
        elo_data = self.elo.get_strength_modifier(team_a, team_b, league_slug)
        elo_mod = elo_data["elo_prediction"]
        
        elo_h = elo_mod.get("home_rating", 1500)
        elo_a = elo_mod.get("away_rating", 1500)
        elo_diff = elo_h - elo_a + 65.0
        
        xg_a = max(0.2, xg_a * (1.0 + elo_diff * 0.0012))
        xg_b = max(0.2, xg_b * (1.0 - elo_diff * 0.0012))

        # ANCHOR TO MARKET if dq < 50
        rho = -0.1
        if stats.get('data_quality', 50) < 50:
            xg_a, xg_b, rho = self._anchor_to_market(xg_a, xg_b, odds)

        probs = self.calculate_match_probabilities(xg_a, xg_b, rho=rho)
        
        exact_scores = probs['exact_scores']
        best_score = max(exact_scores, key=exact_scores.get)
        best_exact_score = f"{best_score} ({round(exact_scores[best_score] * 100, 1)}%)"

        return {
            "teamA": team_a,
            "teamB": team_b,
            "no_bet": False,
            "xg_home": xg_a,
            "xg_away": xg_b,
            "xg_a": round(xg_a, 2),
            "xg_b": round(xg_b, 2),
            "xg_tot": round(xg_a + xg_b, 2),
            "forma_a": round(stats.get('forma_a', 0), 2),
            "forma_b": round(stats.get('forma_b', 0), 2),
            "angoli_tot": round(stats.get('angoli', 9.5), 2),
            "cartelli_tot": round(stats.get('cartellini', 4.5), 2),
            "rigore_pct": round(stats.get('rigore_pct', 15), 2),
            "xg_diff": xg_a - xg_b,
            "possession_diff": stats.get('possession_a', 50) - stats.get('possession_b', 50),
            "forma_diff": stats.get('forma_a', 10) - stats.get('forma_b', 10),
            "casa_trasf": stats.get('casa_trasf', 0.2),
            "angoli": stats.get('angoli', 9.5),
            "cartellini": stats.get('cartellini', 4.5),
            "rigori": stats.get('rigore_pct', 15),
            "btts": probs['GG'] * 100,
            "gol_attesi": xg_a + xg_b,
            "data_quality": data_quality,
            "stats_source": stats.get('stats_source', 'market_implied' if data_quality < 50 else 'fbref'),
            "h2h_home_wins": stats.get('h2h_home_wins', 0),
            "h2h_away_wins": stats.get('h2h_away_wins', 0),
            "h2h_draws": stats.get('h2h_draws', 0),
            "missing_key_home": stats.get('missing_key_home', False),
            "missing_key_away": stats.get('missing_key_away', False),
            "probs": probs,
            "elo": elo_mod,
            "best_exact_score": best_exact_score,
            "bookmaker_odds": match.get("odds", {}),
            "raw_stats": stats
        }

    def generate_value_predictions(self, metrics, smart_money_data=None, home_team=""):
        MIN_MAIN_ODD = 1.45
        MAX_MAIN_ODD = 3.50
        LONGSHOT_ODD = 6.00

        if metrics.get("no_bet"):
            return [{
                "market": "NO BET (Dati non disponibili)",
                "prob": 0, "odd": 0, "ev": 0, "edge": 0, "value_level": "NO BET"
            }]

        smart_money = None
        if smart_money_data:
            import difflib
            for k, v in smart_money_data.items():
                if difflib.SequenceMatcher(None, k.lower(), home_team.lower()).ratio() >= 0.85 or k in home_team.lower() or home_team.lower() in k:
                    smart_money = v
                    break

        probs = metrics['probs'].copy()
        
        if smart_money and smart_money.get("smart_money") in ("1", "X", "2"):
            side = smart_money["smart_money"]
            pct = smart_money.get("percentages", {}).get(side, 0) / 100.0
            if pct >= 0.65:
                shift = 0.08 * (pct - 0.5) * 2
                for k in ("1", "X", "2"):
                    probs[k] = probs[k] * (1 - shift) + (pct if k == side else probs[k]) * shift
                tot = probs["1"] + probs["X"] + probs["2"]
                for k in ("1", "X", "2"):
                    probs[k] /= tot
                probs["1X"] = probs["1"] + probs["X"]
                probs["X2"] = probs["X"] + probs["2"]
                probs["12"] = probs["1"] + probs["2"]

        book_odds = metrics['bookmaker_odds'].copy()
        
        # Generazione quote sintetiche per mercati mancanti
        o1 = book_odds.get("1")
        ox = book_odds.get("X")
        o2 = book_odds.get("2")
        
        if not (o1 and ox and o2 and all(isinstance(v, (int, float)) and v > 1.01 for v in (o1, ox, o2))):
            book_odds["1"] = round((1 / max(0.05, probs["1"])) * 0.93, 2)
            book_odds["X"] = round((1 / max(0.05, probs["X"])) * 0.93, 2)
            book_odds["2"] = round((1 / max(0.05, probs["2"])) * 0.93, 2)
            o1, ox, o2 = book_odds["1"], book_odds["X"], book_odds["2"]
            
        if "1X" not in book_odds and o1 and ox: book_odds["1X"] = round(1 / ((1/o1) + (1/ox)) * 0.95, 2)
        if "X2" not in book_odds and ox and o2: book_odds["X2"] = round(1 / ((1/ox) + (1/o2)) * 0.95, 2)
        if "12" not in book_odds and o1 and o2: book_odds["12"] = round(1 / ((1/o1) + (1/o2)) * 0.95, 2)

        if "GG" not in book_odds: book_odds["GG"] = round((1 / max(0.05, probs["GG"])) * 0.94, 2)
        if "NG" not in book_odds: book_odds["NG"] = round((1 / max(0.05, probs["NG"])) * 0.94, 2)
        if "U 3.5" not in book_odds: book_odds["U 3.5"] = round((1 / max(0.05, probs["U 3.5"])) * 0.94, 2)
        if "O 1.5" not in book_odds: book_odds["O 1.5"] = round((1 / max(0.05, probs["O 1.5"])) * 0.94, 2)
        if "U 2.5" not in book_odds: book_odds["U 2.5"] = round((1 / max(0.05, probs["U 2.5"])) * 0.94, 2)
        if "O 2.5" not in book_odds: book_odds["O 2.5"] = round((1 / max(0.05, probs["O 2.5"])) * 0.94, 2)
            
        real_odds = set(metrics['bookmaker_odds'].keys())
        
        candidates = []
        markets_to_eval = [
            ("1", probs["1"]), ("X", probs["X"]), ("2", probs["2"]),
            ("1X", probs["1X"]), ("X2", probs["X2"]), ("12", probs["12"]),
            ("GG", probs["GG"]), ("NG", probs["NG"])
        ]
        
        for key in probs:
            if key in ["exact_scores", "1", "X", "2", "1X", "X2", "12", "GG", "NG"]: continue
            markets_to_eval.append((key, probs[key]))

        # Coerenza col mercato: favorito >= 70% no-vig => lato opposto vietato
        if o1 and ox and o2 and all(isinstance(v, (int, float)) and v > 1.01 for v in (o1, ox, o2)):
            s = 1/o1 + 1/ox + 1/o2
            mp1, mp2 = (1/o1)/s, (1/o2)/s
            if max(mp1, mp2) >= 0.70 and metrics.get("data_quality", 50) < 70:
                forbidden = "2" if mp1 > mp2 else "1"
                markets_to_eval = [
                    m for m in markets_to_eval 
                    if m[0] != forbidden 
                    and not m[0].startswith(forbidden + " ") 
                    and not m[0].startswith(forbidden + "X") 
                    and not m[0].startswith("X" + forbidden)
                ]

        elo = metrics.get("elo", {})
        elo_p_home = elo.get("elo_p_home", 0.5)
        elo_p_away = elo.get("elo_p_away", 0.5)
        
        if elo_p_home >= 0.60:
            markets_to_eval = [m for m in markets_to_eval if m[0] != "2" and not m[0].startswith("2 ") and not m[0].startswith("X2")]
        elif elo_p_away >= 0.60:
            markets_to_eval = [m for m in markets_to_eval if m[0] != "1" and not m[0].startswith("1 ") and not m[0].startswith("1X")]

        for market_name, prob in markets_to_eval:
            if prob < 0.10: continue
            
            fair_odd = self._calculate_fair_odd(prob)
            has_real_odd = market_name in real_odds
            
            actual_odd = None
            if market_name in book_odds:
                actual_odd = book_odds[market_name]
            elif "+" in market_name:
                parts = market_name.split(" + ")
                if len(parts) == 2:
                    p1, p2 = parts[0], parts[1]
                    if p1 in book_odds and p2 in book_odds:
                        o1_val = book_odds[p1]
                        o2_val = book_odds[p2]
                        if isinstance(o1_val, (int, float)) and isinstance(o2_val, (int, float)):
                            if o1_val > 1.0 and o2_val > 1.0:
                                actual_odd = round((o1_val * o2_val) * 0.90, 2)
            
            if actual_odd and isinstance(actual_odd, (int, float)) and 1.10 < actual_odd <= LONGSHOT_ODD:
                implied_prob = 1 / actual_odd
                edge_pct = (prob - implied_prob) * 100
                base_ev_pct = ((prob * actual_odd) - 1) * 100
                quality_factor = max(0.5, metrics.get('data_quality', 50) / 100.0)
                ev_pct = base_ev_pct * quality_factor
                
                if not has_real_odd:
                    level = "TEORICO 🟡 (quota simulata)"
                elif ev_pct >= config.MIN_EV and edge_pct >= config.MIN_EDGE:
                    level = "VALUE FORTE 🟢"
                elif ev_pct > 0 and edge_pct > 0:
                    level = "VALUE MODERATO 🟡"
                else:
                    level = "STATISTICA MODERATA 🟡"
            else:
                if prob < 0.55: continue
                actual_odd = f"Cerca > {round(fair_odd * 1.05, 2)}"
                edge_pct = 0
                ev_pct = 0
                level = "STATISTICA MODERATA 🟡 (Senza Quota)"
                
            candidates.append({
                "market": market_name,
                "prob": round(prob * 100, 1),
                "odd": actual_odd,
                "fair_odd": fair_odd,
                "edge": round(edge_pct, 1),
                "ev": round(ev_pct, 1),
                "value_level": level,
                "is_real_odd": has_real_odd
            })
            
        # Selezione SCELTA MIGLIORE vincolata (quota main tra MIN_MAIN_ODD 1.45 e MAX_MAIN_ODD 3.50)
        best_bet = None
        
        # Tier 1: promuove a main solo valore reale verificato.
        tier1 = [
            c for c in candidates 
            if c['is_real_odd'] 
            and isinstance(c['odd'], (int, float)) 
            and MIN_MAIN_ODD <= c['odd'] <= MAX_MAIN_ODD
            and c['ev'] >= config.MIN_EV
            and c['edge'] >= config.MIN_EDGE
            and c['market'] in ["1", "X", "2", "1X", "X2", "12", "O 2.5", "U 2.5", "GG", "NG"]
        ]
        tier1.sort(key=lambda c: c['ev'] + (15 if c['market'] in ["1", "X", "2"] else (10 if c['market'] in ["1X", "X2"] else 5)), reverse=True)
        
        if tier1:
            best_bet = tier1[0]
        else:
            # Tier 2: valore reale con probabilità sufficiente, anche se non ancora forte.
            tier2 = [
                c for c in candidates 
                if c['is_real_odd']
                and isinstance(c['odd'], (int, float)) 
                and MIN_MAIN_ODD <= c['odd'] <= MAX_MAIN_ODD
                and c['prob'] >= 45.0
                and c['market'] in ["1", "X", "2", "1X", "X2", "12", "O 2.5", "U 2.5", "GG", "NG"]
            ]
            tier2.sort(key=lambda c: c['prob'] * (float(c['odd']) ** 0.5), reverse=True)
            if tier2:
                best_bet = tier2[0]
            else:
                # Tier 3: Fallback con quota >= 1.25
                tier3 = [
                    c for c in candidates 
                    if c['is_real_odd']
                    and isinstance(c['odd'], (int, float)) 
                    and 1.25 <= c['odd'] <= MAX_MAIN_ODD
                    and c['prob'] >= 50.0
                ]
                tier3.sort(key=lambda c: c['prob'], reverse=True)
                if tier3:
                    best_bet = tier3[0]
                elif candidates:
                    candidates.sort(key=lambda c: c['prob'], reverse=True)
                    best_bet = candidates[0]
                
        if best_bet:
            best_bet['is_main'] = True
            
        other_bets = [c for c in candidates if c != best_bet]
        def _sort_odd(x):
            try: return float(x['odd']) if isinstance(x['odd'], (int, float)) else 999.0
            except: return 999.0
        other_bets_sorted = sorted(other_bets, key=_sort_odd)
        
        final_bets = []
        if best_bet: final_bets.append(best_bet)
        final_bets.extend(other_bets_sorted)
        
        for bet in final_bets:
            confidence = 1
            if bet['prob'] >= 80: confidence += 2
            elif bet['prob'] >= 65: confidence += 1
            if bet['is_real_odd'] and bet['ev'] >= config.MIN_EV: confidence += 1
            if bet['is_real_odd'] and bet['edge'] >= config.MIN_EDGE: confidence += 1
            if confidence > 5: confidence = 5
            if not bet['is_real_odd'] and confidence > 2: confidence = 2
            bet['confidence'] = confidence
            
        return final_bets[:6]
