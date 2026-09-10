import sqlite3
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((BASE_DIR / "backend" / "src").resolve()))

from nlg_writer import NLGWriter
from db_manager import DatabaseManager

def reprocess_all():
    print("Avvio rigenerazione rapida testi NLG per tutti i match nel DB...")
    db_path = BASE_DIR / "backend" / "data" / "predictions.db"
    if not db_path.exists():
        print("Database non trovato.")
        return

    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT match_id, date, predictions_json FROM matches")
    rows = cursor.fetchall()
    print(f"Trovate {len(rows)} partite da processare.")

    writer = NLGWriter()
    updated_count = 0
    dates_to_publish = set()

    for r in rows:
        mid = r["match_id"]
        date_str = r["date"]
        raw_json = r["predictions_json"]
        if not raw_json:
            continue

        try:
            mdata = json.loads(raw_json)
        except Exception:
            continue

        # Garantisci chiavi fondamentali in mdata
        if "teamA" not in mdata:
            mdata["teamA"] = mdata.get("home_team", "")
        if "teamB" not in mdata:
            mdata["teamB"] = mdata.get("away_team", "")

        # Genera il nuovo testo NLG usando mdata arricchito
        new_analysis = writer.generate_analysis(mdata)
        mdata["analysis_360"] = new_analysis

        new_json = json.dumps(mdata, ensure_ascii=False)

        cursor.execute(
            "UPDATE matches SET predictions_json = ? WHERE match_id = ?",
            (new_json, mid)
        )
        updated_count += 1
        if date_str:
            dates_to_publish.add(date_str)

    conn.commit()
    conn.close()
    print(f"Aggiornate {updated_count} partite nel DB.")

    # Rigenera i file JSON pubblicati in backend/output/
    print("Rigenerazione file JSON pubblicati per tutte le date...")
    db_mgr = DatabaseManager()
    for d in sorted(list(dates_to_publish)):
        db_mgr.publish_json_for_date(d)
    db_mgr.close()
    print("Operazione completata con successo! Tutti i file JSON sono stati aggiornati.")

if __name__ == "__main__":
    reprocess_all()
