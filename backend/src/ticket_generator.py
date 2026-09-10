from config import config

class TicketGenerator:
    def __init__(self):
        pass
        
    def _calc_kelly_stake(self, matches):
        prob = 1.0
        tot_odd = 1.0
        for m in matches:
            prob *= (m["prob"] / 100.0)
            tot_odd *= m["odd"]
            
        if tot_odd > 1.0:
            kelly = ((prob * tot_odd) - 1) / (tot_odd - 1)
            if kelly > 0:
                fractional = kelly * config.KELLY_MULT * 100
                stake = min(config.MAX_STAKE, max(0.1, round(fractional, 2)))
                return f"{stake}%"
        return "0.25%"

    def generate_tickets(self, predictions):
        """
        Genera schedine pronte (Singola, Raddoppio, Tris) a partire dalla lista di pronostici.
        """
        if not predictions:
            return []
            
        valid_bets = []
        for match in predictions:
            if match.get("status") in ["post", "in", "LIVE", "FT"]: 
                continue
                
            top_preds = match.get("top_predictions", [])
            if not top_preds: continue
            
            main_bet = next((p for p in top_preds if p.get("is_main")), top_preds[0])
            
            if "NO BET" in main_bet.get("value_level", "") or "Senza Quota" in main_bet.get("value_level", ""):
                continue
                
            try:
                odd = float(main_bet.get("odd", 0))
                if odd < 1.20: continue
            except:
                continue
                
            valid_bets.append({
                "match_id": match["match_id"],
                "date": match.get("date", ""),
                "time": match.get("time", ""),
                "market": main_bet["market"],
                "odd": odd,
                "confidence": main_bet.get("confidence", 1),
                "ev": main_bet.get("ev", 0),
                "prob": main_bet.get("prob", 0),
                "league": match.get("league", "")
            })
            
        valid_bets.sort(key=lambda x: (x["confidence"], x["ev"]), reverse=True)
        
        tickets = []
        if not valid_bets:
            return tickets
            
        singola_bet = next((b for b in valid_bets if 1.50 <= b["odd"] <= 2.50), valid_bets[0])
        tickets.append({
            "type": "Singola",
            "matches": [singola_bet],
            "total_odd": round(singola_bet["odd"], 2),
            "stake": self._calc_kelly_stake([singola_bet])
        })
        
        remaining_bets = [b for b in valid_bets if b["match_id"] != singola_bet["match_id"]]
        
        # RADDOPPIO
        if len(remaining_bets) >= 2:
            radd_matches = []
            leagues = set()
            for b in remaining_bets:
                if b["league"] not in leagues:
                    radd_matches.append(b)
                    leagues.add(b["league"])
                if len(radd_matches) == 2: break
                    
            if len(radd_matches) == 2:
                tot_odd = radd_matches[0]["odd"] * radd_matches[1]["odd"]
                if 2.0 <= tot_odd <= 6.0:
                    tickets.append({
                        "type": "Raddoppio",
                        "matches": radd_matches,
                        "total_odd": round(tot_odd, 2),
                        "stake": self._calc_kelly_stake(radd_matches)
                    })
                    for r in radd_matches: remaining_bets.remove(r)
            
            # TRIS
            if len(remaining_bets) >= 3:
                tris_matches = []
                leagues = set()
                for b in remaining_bets:
                    if b["league"] not in leagues:
                        tris_matches.append(b)
                        leagues.add(b["league"])
                    if len(tris_matches) == 3: break
                        
                if len(tris_matches) == 3:
                    tot_odd = tris_matches[0]["odd"] * tris_matches[1]["odd"] * tris_matches[2]["odd"]
                    if 3.0 <= tot_odd <= 12.0:
                        tickets.append({
                            "type": "Tris",
                            "matches": tris_matches,
                            "total_odd": round(tot_odd, 2),
                            "stake": self._calc_kelly_stake(tris_matches)
                        })
                
        return tickets