import json
from pathlib import Path
from db_manager import DatabaseManager
from settlement import clean_market

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def generate_stats():
    db = DatabaseManager()
    matches = db.get_all_matches()
    db.close()

    stats = {
        # chiavi legacy (pagina Archivio)
        "total_matches": 0,
        "completed_matches": 0,
        "markets": {},
        "confidence": {str(i): {"total": 0, "correct": 0} for i in range(1, 6)},
        # chiavi nuove (dashboard principale)
        "total_main_bets_settled": 0,
        "main_bets_won": 0,
        "main_bets_lost": 0,
        "main_win_rate": 0.0,
        "main_avg_odd": 0.0,
        "main_yield_pct": 0.0,
        "main_roi_flat_1u": 0.0,
        "main_clv_mean": None,
        "leagues_breakdown": {},
        "calibration_buckets": [],
    }

    main_odds, main_clv = [], []
    calib = {}

    for m in matches:
        if m.get("status", "") not in ["post", "FT (Conclusa)"]:
            continue
        stats["completed_matches"] += 1
        top_preds = m.get("top_predictions", [])
        if top_preds:
            stats["total_matches"] += 1
        league = m.get("league", "Unknown")

        # legacy: tutte le gambe
        for p in top_preds:
            market = p.get("market", "")
            if "NO BET" in market:
                continue
            conf = str(p.get("confidence", 1))
            is_correct = p.get("is_correct")
            if is_correct is None:
                continue
            stats["markets"].setdefault(market, {"total": 0, "correct": 0})
            stats["markets"][market]["total"] += 1
            if conf in stats["confidence"]:
                stats["confidence"][conf]["total"] += 1
            if is_correct:
                stats["markets"][market]["correct"] += 1
                if conf in stats["confidence"]:
                    stats["confidence"][conf]["correct"] += 1

        # nuovo: SOLO main bet
        main_bet = next((p for p in top_preds if p.get("is_main")), None)
        if not main_bet:
            continue
        mkt = clean_market(main_bet.get("market", ""))
        if "NO BET" in mkt:
            continue
        odd = main_bet.get("odd")
        if not isinstance(odd, (int, float)) or odd <= 1.01:
            continue
        is_correct = main_bet.get("is_correct")
        if is_correct is None:
            continue

        stats["total_main_bets_settled"] += 1
        main_odds.append(odd)
        if is_correct:
            stats["main_bets_won"] += 1
        else:
            stats["main_bets_lost"] += 1

        lb = stats["leagues_breakdown"].setdefault(league, {"won": 0, "lost": 0})
        lb["won" if is_correct else "lost"] += 1

        clv = main_bet.get("clv")
        if isinstance(clv, (int, float)):
            main_clv.append(clv)

        prob = main_bet.get("prob")
        if isinstance(prob, (int, float)):
            bucket = int(prob // 10) * 10
            cb = calib.setdefault(bucket, {"total": 0, "won": 0})
            cb["total"] += 1
            if is_correct:
                cb["won"] += 1

    total_main = stats["main_bets_won"] + stats["main_bets_lost"]
    if total_main > 0:
        avg_odd = sum(main_odds) / len(main_odds)
        profit = stats["main_bets_won"] * (avg_odd - 1) - stats["main_bets_lost"]
        stats["main_win_rate"] = round(stats["main_bets_won"] / total_main * 100, 2)
        stats["main_avg_odd"] = round(avg_odd, 2)
        stats["main_yield_pct"] = round(profit / total_main * 100, 2)
        stats["main_roi_flat_1u"] = stats["main_yield_pct"]
    if main_clv:
        stats["main_clv_mean"] = round(sum(main_clv) / len(main_clv) * 100, 2)
    for bucket, d in sorted(calib.items()):
        if d["total"] >= 5:
            stats["calibration_buckets"].append({
                "bucket": f"{bucket}-{bucket + 9}%",
                "predicted_prob": bucket + 5,
                "hit_rate": round(d["won"] / d["total"] * 100, 2),
                "n": d["total"],
            })
    for v in stats["leagues_breakdown"].values():
        v["total"] = v["won"] + v["lost"]
        v["win_rate"] = round(v["won"] / v["total"] * 100, 2) if v["total"] else 0.0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)
    print(f"[STATS] {stats['total_main_bets_settled']} main bet | WR {stats['main_win_rate']}% | "
          f"yield {stats['main_yield_pct']}% | CLV {stats['main_clv_mean']}")


if __name__ == "__main__":
    generate_stats()