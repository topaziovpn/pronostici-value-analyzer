import argparse
import yaml
import sys
from pathlib import Path

def main():
    if len(sys.argv) == 1:
        # Nessun argomento passato (es. avvio con doppio clic)
        manage_leagues()
        input("\nPremi INVIO per uscire...")
        return

    parser = argparse.ArgumentParser(description="Gestione campionati Pronostici Value Analyzer")
    parser.add_argument("command", choices=["leagues"], nargs="?", default="leagues", help="Comando da eseguire")
    args = parser.parse_args()

    if args.command == "leagues":
        manage_leagues()

def manage_leagues():
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("Errore: config.yaml non trovato. Copia config.example.yaml in config.yaml prima.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    leagues = config.get("leagues", [])
    if not leagues:
        print("Nessun campionato trovato in config.yaml.")
        return
    
    while True:
        print("\n--- Gestione Campionati ---")
        for i, league in enumerate(leagues):
            status = "[X]" if league.get("enabled") else "[ ]"
            print(f"{i+1}. {status} {league.get('name')} (Priorità: {league.get('priority')})")
        print("0. Salva ed esci")
        print("---------------------------")
        
        try:
            choice = int(input("Seleziona il numero del campionato da attivare/disattivare (0 per uscire): "))
            if choice == 0:
                break
            if 1 <= choice <= len(leagues):
                idx = choice - 1
                leagues[idx]["enabled"] = not leagues[idx]["enabled"]
            else:
                print("Scelta non valida.")
        except ValueError:
            print("Inserisci un numero valido.")
    
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    
    print("Configurazione salvata con successo in config.yaml.")

if __name__ == "__main__":
    main()
