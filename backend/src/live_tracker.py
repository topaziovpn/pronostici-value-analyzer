import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from db_manager import DatabaseManager
from moneyway_scraper import MoneyWayScraper
from data_collectors import DataCollector
from stats_generator import generate_stats

TZ = ZoneInfo("Europe/Rome")


class LiveTracker:
    def __init__(self):
        self.db = DatabaseManager()
        self.mw = MoneyWayScraper()
        self.scraper = DataCollector()

    def update_live_scores(self):
        print("[LIVE TRACKER] Avvio aggiornamento MoneyWay...")
        try:
            smart_money_data = self.mw.fetch_smart_money()
        except Exception as e:
            print(f"[LIVE TRACKER] Errore MoneyWay: {e}")
            smart_money_data = {}

        print(f"[LIVE TRACKER] Aggiornamento risultati reali (ESPN)... {datetime.now()}")
        now = datetime.now(TZ)
        dates_to_check = [(now - timedelta(days=days)).strftime("%Y-%m-%d") for days in range(7)]
        real_matches = []
        for date_str in dates_to_check:
            real_matches += self.scraper.fetch_todays_matches(date_str)
        if not real_matches:
            print("[LIVE TRACKER] Nessuna partita trovata su ESPN.")
            return

        real_dict = {m['match_id']: m for m in real_matches}
        db_matches = []
        for date_str in dates_to_check:
            db_matches += self.db.get_matches_by_date(date_str)

        updated_count = 0
        for m in db_matches:
            match_id = m['match_id']
            home_team = m['home_team']

            if smart_money_data:
                sm = None
                for k, v in smart_money_data.items():
                    if k in home_team.lower() or home_team.lower() in k:
                        sm = v
                        break
                if sm:
                    self.db.update_moneyway(match_id, sm)

            if match_id in real_dict:
                real_m = real_dict[match_id]
                status_raw = real_m['status']
                status = "NOT_STARTED"
                if status_raw == "in":
                    status = "LIVE"
                elif status_raw == "post" and real_m.get("completed", False):
                    status = "FT (Conclusa)"
                elif status_raw == "post":
                    status = "POSTPONED"
                self.db.update_live_score(match_id, real_m['home_score'],
                                          real_m['away_score'], status,
                                          real_m.get('time_detail'))
                updated_count += 1

        print(f"[LIVE TRACKER] Aggiornati {updated_count} match con risultati REALI.")
        for date_str in dates_to_check:
            self.db.publish_json_for_date(date_str)
        generate_stats()

    def run_daemon(self):
        print("Avvio Live Tracker Daemon REALE (aggiornamento ogni 2 minuti)...")
        while True:
            self.update_live_scores()
            time.sleep(120)


if __name__ == "__main__":
    tracker = LiveTracker()
    tracker.run_daemon()