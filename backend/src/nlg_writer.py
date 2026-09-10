import pandas as pd
import random
from pathlib import Path
import io

BASE_DIR = Path(__file__).resolve().parent.parent.parent
NLG_DB_PATH = BASE_DIR / "backend" / "output" / "google_sheet_export.csv"


class _SafeDict(dict):
    """format_map con questa classe sostituisce le chiavi presenti
    e lascia VISIBILI quelle mancanti (debug immediato, nessun crash)."""
    def __missing__(self, key):
        return "{" + key + "}"


class NLGWriter:
    def __init__(self):
        self.rules = pd.DataFrame()
        self._load_db()

    def _load_db(self):
        if NLG_DB_PATH.exists():
            with open(NLG_DB_PATH, 'r', encoding='utf-8') as f:
                content = f.read().strip().split('\n')
            cleaned_lines = []
            for line in content:
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1].replace('""', '"')
                cleaned_lines.append(line)
            self.rules = pd.read_csv(io.StringIO('\n'.join(cleaned_lines)))
            print(f"[NLG] Caricate {len(self.rules)} regole dal dizionario semantico.")
        else:
            print(f"[NLG] Attenzione: file {NLG_DB_PATH} non trovato. Fallback ai testi base.")

    def get_text_for_metric(self, dimensione, value, context_pack):
        if self.rules.empty:
            return ""
        subset = self.rules[self.rules['dimensione'] == dimensione]
        if subset.empty:
            return ""
        match = subset[(subset['bucket_min'] <= value) & (subset['bucket_max'] >= value)]
        if match.empty:
            return ""
        chosen = match.sample(n=1).iloc[0]
        text_template = chosen['testo']

        # Normalizzazione e fallback per tutte le variabili dei template CSV
        raw_stats = context_pack.get('raw_stats', {}) or {}
        xg_a = context_pack.get('xg_a', context_pack.get('xg_home', raw_stats.get('xg_a', 1.3)))
        xg_b = context_pack.get('xg_b', context_pack.get('xg_away', raw_stats.get('xg_b', 1.3)))
        xg_tot = context_pack.get('xg_tot', context_pack.get('gol_attesi', xg_a + xg_b))
        forma_a = context_pack.get('forma_a', raw_stats.get('forma_a', 0))
        forma_b = context_pack.get('forma_b', raw_stats.get('forma_b', 0))
        angoli_tot = context_pack.get('angoli_tot', context_pack.get('angoli', raw_stats.get('angoli', 9.5)))
        cartelli_tot = context_pack.get('cartelli_tot', context_pack.get('cartellini', raw_stats.get('cartellini', 4.5)))
        rigore_pct = context_pack.get('rigore_pct', context_pack.get('rigori', raw_stats.get('rigore_pct', 15)))

        defaults = {
            "xg_a": xg_a,
            "xg_b": xg_b,
            "xg_tot": xg_tot,
            "forma_a": forma_a,
            "forma_b": forma_b,
            "angoli_tot": angoli_tot,
            "cartelli_tot": cartelli_tot,
            "rigore_pct": rigore_pct,
            "teamA": context_pack.get("teamA", "Squadra Casa"),
            "teamB": context_pack.get("teamB", "Squadra Trasferta"),
            "btts": context_pack.get("btts", 50.0)
        }

        formatted_pack = {}
        for k, v in context_pack.items():
            if isinstance(v, bool):
                formatted_pack[k] = v
            else:
                try:
                    formatted_pack[k] = round(float(v), 2)
                except Exception:
                    formatted_pack[k] = v

        for k, v in defaults.items():
            if k not in formatted_pack or formatted_pack[k] is None:
                try:
                    formatted_pack[k] = round(float(v), 2)
                except Exception:
                    formatted_pack[k] = v

        try:
            return text_template.format_map(_SafeDict(formatted_pack))
        except Exception as e:
            print(f"[NLG] Errore template '{dimensione}': {e}")
            return text_template

    def generate_analysis(self, context_pack):
        if context_pack.get("no_bet"):
            return "Nessuna statistica avanzata disponibile per questa partita. Mercato escluso."

        analysis_blocks = []

        # Trasparenza fonte dati
        src = context_pack.get("stats_source") or context_pack.get("raw_stats", {}).get("stats_source")
        if src == "market_implied":
            analysis_blocks.append(
                "⚠️ **Stima basata esclusivamente sulle quote di mercato.** "
                "I dati storici indipendenti non sono disponibili per questa partita: "
                "le statistiche seguenti sono proiezioni sintetiche, non osservazioni reali."
            )

        if 'xg_diff' in context_pack:
            text = self.get_text_for_metric('xg_diff', context_pack['xg_diff'], context_pack)
            if text: analysis_blocks.append(text)
        if 'forma_diff' in context_pack:
            text = self.get_text_for_metric('forma_diff', context_pack['forma_diff'], context_pack)
            if text: analysis_blocks.append(text)
        if 'casa_trasf' in context_pack:
            text = self.get_text_for_metric('casa_trasf', context_pack['casa_trasf'], context_pack)
            if text: analysis_blocks.append(text)
        if 'gol_attesi' in context_pack:
            text = self.get_text_for_metric('gol_attesi', context_pack['gol_attesi'], context_pack)
            if text: analysis_blocks.append(text)
        if 'btts' in context_pack:
            text = self.get_text_for_metric('btts', context_pack['btts'], context_pack)
            if text: analysis_blocks.append(text)

        accessories = []
        if 'angoli' in context_pack:
            txt = self.get_text_for_metric('angoli', context_pack['angoli'], context_pack)
            if txt: accessories.append(txt)
        if 'cartellini' in context_pack:
            txt = self.get_text_for_metric('cartellini', context_pack['cartellini'], context_pack)
            if txt: accessories.append(txt)
        if 'rigori' in context_pack:
            txt = self.get_text_for_metric('rigori', context_pack['rigori'], context_pack)
            if txt: accessories.append(txt)
        if accessories:
            analysis_blocks.append(" ".join(accessories))

        qualitative = []
        h2h_h = context_pack.get('h2h_home_wins', 0)
        h2h_a = context_pack.get('h2h_away_wins', 0)
        if h2h_h > h2h_a * 2 and h2h_h > 0:
            qualitative.append(f"Storicamente, il {context_pack['teamA']} è la vera 'bestia nera' in questo scontro diretto, avendo dominato nettamente le ultime sfide.")
        elif h2h_a > h2h_h * 2 and h2h_a > 0:
            qualitative.append(f"Nonostante il fattore campo, il {context_pack['teamB']} vanta una solida tradizione positiva nei testa a testa recenti contro questo avversario.")
        if context_pack.get('missing_key_home'):
            qualitative.append(f"L'assenza di giocatori chiave nel {context_pack['teamA']} potrebbe penalizzare pesantemente il potenziale offensivo dei padroni di casa oggi.")
        if context_pack.get('missing_key_away'):
            qualitative.append(f"Pesanti defezioni previste per il {context_pack['teamB']}, che si presenta a questa sfida con alcune assenze fondamentali nell'undici titolare.")
        if qualitative:
            analysis_blocks.append(" ".join(qualitative))

        # Blocco Elo: mostrato SOLO se i rating sono costruiti su partite vere
        elo = context_pack.get("elo") or {}
        if elo.get("home_matches", 0) > 0 and elo.get("away_matches", 0) > 0:
            rh, ra = elo.get("home_rating", 0), elo.get("away_rating", 0)
            diff = abs(rh - ra)
            if diff > 200:
                stronger = context_pack['teamA'] if rh > ra else context_pack['teamB']
                analysis_blocks.append(
                    f"⚡ **Analisi Elo**: il divario tecnico è significativo ({stronger} nettamente "
                    f"superiore, {rh:.0f} vs {ra:.0f}). Differenze di questa entità si traducono "
                    f"storicamente in un dominio chiaro del più forte."
                )
            elif diff > 80:
                side = "i padroni di casa" if rh > ra else "gli ospiti"
                analysis_blocks.append(
                    f"⚡ **Analisi Elo**: gap qualitativo moderato ({rh:.0f} vs {ra:.0f}), "
                    f"con leggero vantaggio tecnico per {side}."
                )
            else:
                analysis_blocks.append(
                    f"⚡ **Analisi Elo**: rating molto simile ({rh:.0f} vs {ra:.0f}): "
                    f"ci si aspetta una partita equilibrata."
                )

        if not analysis_blocks:
            return "Analisi in corso. Dati non sufficienti per generare il report statistico completo."
        return "\n\n".join(analysis_blocks)