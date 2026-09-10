import urllib.request
import json
import csv
from pathlib import Path
from datetime import datetime

# Calcola i percorsi in modo robusto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "input"
OUTPUT_FILE = OUTPUT_DIR / "palinsesto_scraped.csv"

def scrape_site():
    """
    Effettua l'estrazione del palinsesto odierno collegandosi a un feed aperto e gratuito (TheSportsDB).
    Nessuna API key richiesta. E' un vero scraping di dati live JSON.
    """
    print("[DOWNLOADER] Avvio estrazione partite di oggi...")
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={today}&s=Soccer"
    
    matches = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        
        events = data.get('events', [])
        if not events:
            print("[DOWNLOADER] Nessuna partita trovata per oggi su questo network.")
            return matches
            
        print(f"[DOWNLOADER] Trovate {len(events)} partite grezze. Filtraggio in corso...")
        
        # Filtriamo e formattiamo i dati
        for e in events:
            home = e.get('strHomeTeam', 'Unknown')
            away = e.get('strAwayTeam', 'Unknown')
            league = e.get('strLeague', 'Unknown')
            time_str = e.get('strTime', '00:00:00')
            
            # Pulisce l'orario (es. da 20:45:00 a 20:45)
            if len(time_str) >= 5:
                time_str = time_str[:5]
                
            matches.append({
                "match_id": f"{home} - {away} | {league}",
                "date": today,
                "time": time_str,
                "league": league,
                "home_team": home,
                "away_team": away
            })
            
    except Exception as e:
        print(f"[DOWNLOADER] Errore critico durante l'estrazione: {e}")
            
    return matches

def save_matches(matches):
    """Salva le partite estratte in un CSV che il modulo LLM leggerà."""
    if not matches:
        print("[DOWNLOADER] Nessuna partita da salvare.")
        return
        
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w", newline='', encoding="utf-8") as f:
        # Aggiunto il campo 'time' al CSV
        writer = csv.DictWriter(f, fieldnames=["match_id", "date", "time", "league", "home_team", "away_team"])
        writer.writeheader()
        writer.writerows(matches)
        
    print(f"[DOWNLOADER] Salvataggio completato: {len(matches)} partite in '{OUTPUT_FILE.name}'")

def run():
    matches = scrape_site()
    save_matches(matches)
    return matches

if __name__ == "__main__":
    run()
