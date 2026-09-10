"""Modulo unico di pulizia mercati e referto scommesse."""


def clean_market(mkt):
    """Rimuove i tag emoji di MoneyWay e normalizza il nome mercato."""
    if not mkt:
        return ""
    return str(mkt).replace(" 🔥", "").replace(" ⬇️", "").strip()


def settle_market(mkt, hs, ast):
    """True se il mercato (pulito) è vincente dato il risultato finale."""
    mkt = clean_market(mkt)
    tot = hs + ast

    if mkt == "1": return hs > ast
    if mkt == "X": return hs == ast
    if mkt == "2": return hs < ast
    if mkt == "1X": return hs >= ast
    if mkt == "X2": return ast >= hs
    if mkt == "12": return hs != ast
    if mkt == "GG": return hs > 0 and ast > 0
    if mkt == "NG": return (hs == 0 or ast == 0)

    if mkt.startswith("O "):
        try: return tot > float(mkt.split(" ")[1])
        except Exception: return False
    if mkt.startswith("U "):
        try: return tot < float(mkt.split(" ")[1])
        except Exception: return False
    if mkt.startswith("Casa O "):
        try: return hs > float(mkt.split(" ")[2])
        except Exception: return False
    if mkt.startswith("Trasf O "):
        try: return ast > float(mkt.split(" ")[2])
        except Exception: return False
    if mkt.startswith("MG "):
        try:
            lo, hi = mkt.replace("MG ", "").split("-")
            return int(lo) <= tot <= int(hi)
        except Exception: return False

    combos = {
        "1X + U 3.5": hs >= ast and tot <= 3,
        "1X + U 2.5": hs >= ast and tot <= 2,
        "1X + GG":    hs >= ast and hs > 0 and ast > 0,
        "12 + O 1.5": hs != ast and tot >= 2,
        "1X + O 1.5": hs >= ast and tot >= 2,
        "1X + O 0.5": hs >= ast and tot >= 1,
        "X2 + O 0.5": ast >= hs and tot >= 1,
        "X2 + O 1.5": ast >= hs and tot >= 2,
        "X2 + U 3.5": ast >= hs and tot <= 3,
        "X2 + U 2.5": ast >= hs and tot <= 2,
        "X2 + GG":    ast >= hs and hs > 0 and ast > 0,
        "1 + O 1.5":  hs > ast and tot >= 2,
        "2 + O 1.5":  ast > hs and tot >= 2,
        "1 + GG":     hs > ast and hs > 0 and ast > 0,
        "2 + GG":     ast > hs and hs > 0 and ast > 0,
    }
    return bool(combos.get(mkt, False))