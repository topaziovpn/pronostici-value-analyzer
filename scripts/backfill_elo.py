import sys
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend", "src"))

from elo_manager import EloManager

def backfill_elo():
    print("[ELO BACKFILL] Avvio ricalcolo storico Elo...")
    db_path = os.path.join(BASE_DIR, "backend", "data", "predictions.db")
    if not os.path.exists(db_path):
        print(f"[ELO BACKFILL] DB non trovato a {db_path}")
        return

    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.isolation_level = None
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query tutte le partite concluse in ordine cronologico
    cursor.execute("""
        SELECT match_id, date, time, home_team, away_team, home_score, away_score, league, status
        FROM matches
        WHERE (status IN ('post', 'FT (Conclusa)', 'FT') OR (home_score IS NOT NULL AND away_score IS NOT NULL AND status != 'pre'))
        ORDER BY date ASC, time ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]

    print(f"[ELO BACKFILL] Trovate {len(rows)} partite concluse da processare.", flush=True)

    elo = EloManager(db_path=db_path, conn=conn)
    processed = 0
    skipped = 0

    for r in rows:
        mid = r["match_id"]
        hs = r["home_score"]
        ast = r["away_score"]
        if hs is None or ast is None:
            skipped += 1
            continue

        try:
            res = elo.update_after_match(
                home_team=r["home_team"],
                away_team=r["away_team"],
                home_score=int(hs),
                away_score=int(ast),
                league=r["league"],
                match_id=mid,
                match_date=r["date"]
            )
            if res is not None:
                processed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"[ELO BACKFILL ERROR] {mid}: {e}", flush=True)
            skipped += 1

    print(f"[ELO BACKFILL] Completato! Processati {processed} match nuovi, saltati {skipped} già calcolati.", flush=True)

    # Stampa campioni per la verifica
    teams_to_check = ["internazionale", "monza", "austin fc", "real madrid", "barcelona"]
    print("\n--- SAMPLE ELO RATINGS DOPO BACKFILL ---", flush=True)
    for t in teams_to_check:
        info = elo.get_rating(t)
        print(f"Squadra: {t.title():<15} | Elo Rating: {info['rating']:.1f} | Partite Giocate: {info['matches_played']}", flush=True)

    conn.close()

if __name__ == "__main__":
    backfill_elo()
