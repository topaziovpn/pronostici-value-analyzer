import json
from pathlib import Path
from datetime import datetime, timedelta
from data_collectors import DataCollector
from db_manager import DatabaseManager
from stats_generator import generate_stats

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "backend" / "output"


def update_past_results():
    """Backfill risultati: aggiorna il DB (fonte di verità) e ripubblica i JSON."""
    print("[UPDATER] Avvio aggiornamento risultati passati...")
    dates_file = OUTPUT_DIR / "available_dates.json"
    if not dates_file.exists():
        print("[UPDATER] Nessun file date disponibile.")
        return
    with open(dates_file, 'r', encoding='utf-8') as f:
        available_dates = json.load(f).get("dates", [])

    scraper = DataCollector()
    db = DatabaseManager()

    for date_str in available_dates:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        espn_dates = [target.strftime("%Y%m%d"),
                      (target - timedelta(days=1)).strftime("%Y%m%d")]
        live_matches = []
        for d in espn_dates:
            live_matches += scraper.fetch_todays_matches(d)
        if not live_matches:
            continue

        live_dict = {m['match_id']: m for m in live_matches}
        db_matches = db.get_matches_by_date(date_str)
        updated = 0
        for m in db_matches:
            live_m = live_dict.get(m['match_id'])
            if not live_m:
                continue
            status_raw = live_m.get('status', 'pre')
            status = "NOT_STARTED"
            if status_raw == "in":
                status = "LIVE"
            elif status_raw == "post":
                status = "FT (Conclusa)"
            db.update_live_score(m['match_id'], live_m['home_score'],
                                 live_m['away_score'], status,
                                 live_m.get('time_detail'))
            updated += 1
        if updated:
            db.publish_json_for_date(date_str)
            print(f"[UPDATER] {date_str}: aggiornate {updated} partite.")

    generate_stats()
    db.close()
    print("[UPDATER] Completato.")


if __name__ == "__main__":
    update_past_results()