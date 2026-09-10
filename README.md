# Pronostici Value Analyzer

Sistema automatico modulare e responsabile per l'analisi di partite di calcio e la ricerca di value bets basata su statistiche (edge, EV).

## Struttura del Progetto
Il progetto si divide in 3 parti principali:
- **STEP 1**: Backend Python in locale (schedulatore, analizzatore tramite LLM).
- **STEP 2**: Validazione e test suite.
- **STEP 3**: App Android in Kotlin per visualizzare i risultati archiviati.

## Installazione (STEP 1)
1. Assicurati di avere Python 3.11+.
2. Crea un virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # su Linux/Mac
   venv\Scripts\activate     # su Windows
   ```
3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
4. Copia `config.example.yaml` in `config.yaml` e modificalo con le tue preferenze.
5. Copia `.env.example` in `.env` e inserisci le tue chiavi.

## Avvio rapido
Per avviare la modalità schedule:
```bash
python backend/src/main.py
```

Per gestire i campionati via CLI:
```bash
python manage.py leagues
```
