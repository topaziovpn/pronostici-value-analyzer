import ssl
import socket
import argparse
import time
import schedule
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# FIX: ignora errori SSL per undetected_chromedriver
ssl._create_default_https_context = ssl._create_unverified_context
# FIX 2: timeout globale anti-blocco
socket.setdefaulttimeout(15.0)

from moneyway_scraper import MoneyWayScraper
from stats_engine import StatsEngine
from nlg_writer import NLGWriter
from db_manager import DatabaseManager
from data_collectors import DataCollector
from settlement import clean_market, settle_market
from stats_generator import generate_stats

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TZ = ZoneInfo("Europe/Rome")


def process_today_matches(target_date=None):
    print("Inizializzazione Sistema PRO (con Scraper Reale)...")
    scraper = DataCollector()
    target_str = target_date or datetime.now(TZ).strftime("%Y-%m-%d")
    matches = scraper.fetch_todays_matches(target_str)
    if not matches:
        print("Nessuna partita trovata o errore di rete. Fine elaborazione.")
        return
    print(f"Trovate {len(matches)} partite. Analisi in corso...")
    engine = StatsEngine()
    mw = MoneyWayScraper()
    smart_money_data = mw.fetch_smart_money()
    writer = NLGWriter()
    db = DatabaseManager()

    processed_dates = set()
    for match in matches:
        metrics = engine.calculate_metrics(match)
        top_predictions = engine.generate_value_predictions(metrics, smart_money_data, match["home_team"])
        analisi_testo = writer.generate_analysis(metrics)

        # Fuso orario corretto (UTC -> Europe/Rome, anche ora solare)
        date_str, time_str = "Oggi", "N/D"
        if "T" in match.get("start_time", ""):
            try:
                utc_dt = datetime.fromisoformat(match["start_time"].replace("Z", "+00:00"))
                ita_dt = utc_dt.astimezone(TZ)
                date_str = ita_dt.strftime("%Y-%m-%d")
                time_str = ita_dt.strftime("%H:%M")
            except Exception as e:
                print(f"[MAIN] Errore parsing start_time: {e}")
                date_str = match["start_time"][:10]
                time_str = match["start_time"][11:16]

        # Referto immediato per partite già concluse al momento della creazione
        if match.get("status") == "post" and match.get("completed", False):
            hs = match.get("home_score", 0)
            ast = match.get("away_score", 0)
            for pred in top_predictions:
                pred["is_correct"] = settle_market(clean_market(pred.get("market", "")), hs, ast)

        prediction = {
            "match_id": match["match_id"],
            "date": date_str,
            "time": time_str,
            "start_time": match.get("start_time", ""),
            "league": match["league"],
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "status": match.get("status", "NOT_STARTED"),
            "time_detail": match.get("time_detail", ""),
            "home_score": match.get("home_score", 0),
            "away_score": match.get("away_score", 0),
            "odds": match["odds"],
            "best_exact_score": metrics["best_exact_score"],
            "data_quality": metrics.get("data_quality", 50),
            "top_predictions": top_predictions,
            "analysis_360": analisi_testo,
            "raw_stats": metrics.get("raw_stats", {}),
            "disclaimer": "Nessuna scommessa sicura."
        }
        processed_dates.add(date_str)
        db.save_match_prediction(prediction)
        db.publish_json_for_date(date_str)

    for date_str in processed_dates:
        db.publish_json_for_date(date_str)
    if processed_dates:
        print("[MAIN] Elaborazione terminata. Storico aggiornato e JSON pronto.")
    generate_stats()
    db.close()
    print("---------------------------------------------------\n")


def process_today_and_tomorrow():
    process_today_matches()
    tomorrow = (datetime.now(TZ) + timedelta(days=1)).strftime("%Y-%m-%d")
    process_today_matches(tomorrow)


def main():
    print("Avvio Pronostici Value Analyzer (Architettura Ibrida NLG - PRO)")
    process_today_and_tomorrow()
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", action="store_true")
    args = parser.parse_args()
    if args.schedule:
        schedule.every().day.at("07:00").do(process_today_and_tomorrow)
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    main()