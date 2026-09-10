import sqlite3
import json
from pathlib import Path
from datetime import datetime
from settlement import clean_market, settle_market

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "backend" / "data"
DB_PATH = DB_DIR / "predictions.db"
OUTPUT_DIR = BASE_DIR / "backend" / "output"


class DatabaseManager:
    def __init__(self):
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                match_id TEXT PRIMARY KEY,
                date TEXT,
                time TEXT,
                league TEXT,
                home_team TEXT,
                away_team TEXT,
                home_score INTEGER,
                away_score INTEGER,
                status TEXT,
                predictions_json TEXT,
                updated_at TEXT
            )
        ''')
        self.conn.commit()

    def save_match_prediction(self, match_data):
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        match_id = match_data['match_id']
        pred_fields = {k: v for k, v in match_data.items()
                       if k not in ['date', 'time', 'league', 'home_team', 'away_team', 'match_id']}
        predictions_json = json.dumps(pred_fields, ensure_ascii=False)
        cursor.execute('''
            INSERT INTO matches (match_id, date, time, league, home_team, away_team,
                                 home_score, away_score, status, predictions_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, 'NOT_STARTED', ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                predictions_json = CASE
                    WHEN matches.status IN ('NOT_STARTED', 'pre') THEN excluded.predictions_json
                    ELSE matches.predictions_json
                END,
                updated_at = excluded.updated_at
        ''', (match_id, match_data.get('date'), match_data.get('time'), match_data.get('league'),
              match_data.get('home_team'), match_data.get('away_team'), predictions_json, now))
        self.conn.commit()

    def update_live_score(self, match_id, home_score, away_score, status, time_detail=None):
        """Aggiorna punteggio/stato; congela closing odds, calcola CLV, referta con settlement unico."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('SELECT predictions_json FROM matches WHERE match_id = ?', (match_id,))
        row = cursor.fetchone()
        if not row:
            return
        try:
            preds = json.loads(row['predictions_json'])
        except Exception as e:
            print(f"[DB] ERRORE JSON corrotto per {match_id}: {e}")
            return

        if time_detail is not None:
            preds['time_detail'] = time_detail

        if status in ["post", "FT (Conclusa)"]:
            # 1) Congela le closing odds UNA volta sola (preferisce i trend MoneyWay)
            if "closing_odds" not in preds:
                closing = {}
                trends = preds.get("moneyway_trends", {}) or {}
                base_odds = preds.get("odds", {}) or {}
                for k in ("1", "X", "2"):
                    cur = None
                    if isinstance(trends.get(k), dict):
                        cur = trends[k].get("current")
                    if not (isinstance(cur, (int, float)) and cur > 1.01):
                        cur = base_odds.get(k)
                    if isinstance(cur, (int, float)) and cur > 1.01:
                        closing[k] = cur
                for k, v in base_odds.items():
                    if k not in closing and isinstance(v, (int, float)) and v > 1.01:
                        closing[k] = v
                if closing:
                    preds["closing_odds"] = closing

            # 2) Referto con modulo unico (pulisce i tag 🔥/⬇️)
            hs, ast = int(home_score), int(away_score)
            closing = preds.get("closing_odds", {})
            for top_pred in preds.get("top_predictions", []):
                mkt = clean_market(top_pred.get("market", ""))
                top_pred["is_correct"] = settle_market(mkt, hs, ast)
                # 3) CLV sulla main bet
                if top_pred.get("is_main"):
                    odd_taken = top_pred.get("odd")
                    closing_odd = closing.get(mkt)
                    if (isinstance(odd_taken, (int, float)) and odd_taken > 1.01
                            and isinstance(closing_odd, (int, float)) and closing_odd > 1.01):
                        top_pred["clv"] = round(odd_taken / closing_odd - 1, 4)

        new_json = json.dumps(preds, ensure_ascii=False)
        cursor.execute('''
            UPDATE matches SET home_score = ?, away_score = ?, status = ?,
                   updated_at = ?, predictions_json = ?
            WHERE match_id = ?
        ''', (home_score, away_score, status, now, new_json, match_id))
        self.conn.commit()

    def get_matches_by_date(self, date_str):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM matches WHERE date = ? ORDER BY time ASC', (date_str,))
        rows = cursor.fetchall()
        matches = []
        for row in rows:
            m = dict(row)
            try:
                preds = json.loads(m['predictions_json'])
            except Exception as e:
                print(f"[DB] ERRORE JSON in get_matches_by_date ({m['match_id']}): {e}")
                preds = {}
            sql_vals = {'status': m['status'], 'home_score': m['home_score'],
                        'away_score': m['away_score'], 'updated_at': m['updated_at']}
            m.update(preds)
            m.update(sql_vals)
            m.pop('predictions_json', None)
            matches.append(m)
        return matches

    def get_all_matches(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM matches ORDER BY time ASC')
        rows = cursor.fetchall()
        matches = []
        for row in rows:
            m = dict(row)
            if m.get('predictions_json'):
                try:
                    preds = json.loads(m['predictions_json'])
                    sql_vals = {'status': m['status'], 'home_score': m['home_score'],
                                'away_score': m['away_score']}
                    m.update(preds)
                    m.update(sql_vals)
                    m.pop('predictions_json', None)
                except Exception as e:
                    print(f"[DB] ERRORE JSON in get_all_matches ({m['match_id']}): {e}")
            matches.append(m)
        return matches

    def update_moneyway(self, match_id, smart_money):
        """Tag MoneyWay + trend quote + storico odds_history."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT predictions_json FROM matches WHERE match_id = ?', (match_id,))
        row = cursor.fetchone()
        if not row:
            return
        try:
            preds = json.loads(row['predictions_json'])
            updated = False
            now = datetime.now().isoformat()

            # 1) Tag Fiamma/Drop
            for p in preds.get("top_predictions", []):
                market = p.get("market", "")
                base_market = clean_market(market)
                if base_market in ["1", "X", "2"]:
                    if base_market == smart_money.get("smart_money"):
                        if "🔥" not in market:
                            p["market"] = f"{base_market} 🔥"
                            updated = True
                    elif smart_money.get("percentages", {}).get(base_market, 0) > 50:
                        if "⬇️" not in market:
                            p["market"] = f"{base_market} ⬇️"
                            updated = True

            # 2) Trend quote correnti
            if "trends" in smart_money:
                if preds.get("moneyway_trends") != smart_money["trends"]:
                    preds["moneyway_trends"] = smart_money["trends"]
                    updated = True
                # 3) Storico (max 50 snapshot)
                if smart_money["trends"]:
                    hist = preds.setdefault("odds_history", [])
                    hist.append({"t": now, "trends": smart_money["trends"]})
                    if len(hist) > 50:
                        preds["odds_history"] = hist[-50:]
                    updated = True

            if updated:
                new_json = json.dumps(preds, ensure_ascii=False)
                cursor.execute('UPDATE matches SET predictions_json = ? WHERE match_id = ?',
                               (new_json, match_id))
                self.conn.commit()
        except Exception as e:
            print(f"[DB] ERRORE update_moneyway per {match_id}: {e}")

    def publish_json_for_date(self, date_str):
        matches = self.get_matches_by_date(date_str)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        file_path = OUTPUT_DIR / f"{date_str}.json"
        existing_tickets = None
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    if old_data.get("tickets"):
                        existing_tickets = old_data["tickets"]
            except Exception as e:
                print(f"[DB] Errore lettura JSON esistente {date_str}: {e}")
        if existing_tickets is not None:
            tickets = existing_tickets
        else:
            try:
                from ticket_generator import TicketGenerator
                tickets = TicketGenerator().generate_tickets(matches)
            except Exception as e:
                print(f"[DB] Errore generazione schedine: {e}")
                tickets = []
        report = {
            "date": date_str,
            "updated_at": datetime.now().isoformat(),
            "total_analyzed": len(matches),
            "tickets": tickets,
            "predictions": matches
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        latest_path = OUTPUT_DIR / "latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        self._update_available_dates_index()
        return file_path

    def _update_available_dates_index(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT date FROM matches ORDER BY date DESC')
        all_dates = [row['date'] for row in cursor.fetchall()]
        valid_dates = [d for d in all_dates if (OUTPUT_DIR / f"{d}.json").exists()]
        with open(OUTPUT_DIR / "available_dates.json", "w", encoding="utf-8") as f:
            json.dump({"dates": valid_dates}, f)

    def close(self):
        self.conn.close()