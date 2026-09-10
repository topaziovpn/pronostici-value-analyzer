import json
from pathlib import Path
from db_manager import DatabaseManager
from settlement import settle_market, clean_market

class AITrainer:
    def __init__(self):
        self.db = DatabaseManager()
        self.weights_file = Path("backend/data/ai_weights.json")
        self.load_weights()

    def load_weights(self):
        if self.weights_file.exists():
            with open(self.weights_file, 'r', encoding='utf-8') as f:
                self.weights = json.load(f)
        else:
            self.weights = {
                "buckets": {
                    "0-20": {"n": 0, "won": 0, "sum_p": 0.0},
                    "20-40": {"n": 0, "won": 0, "sum_p": 0.0},
                    "40-60": {"n": 0, "won": 0, "sum_p": 0.0},
                    "60-80": {"n": 0, "won": 0, "sum_p": 0.0},
                    "80-100": {"n": 0, "won": 0, "sum_p": 0.0},
                },
                "calibration_factors": {
                    "0-20": 1.0,
                    "20-40": 1.0,
                    "40-60": 1.0,
                    "60-80": 1.0,
                    "80-100": 1.0,
                }
            }
            self.save_weights()

    def save_weights(self):
        self.weights_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.weights_file, 'w', encoding='utf-8') as f:
            json.dump(self.weights, f, indent=4)

    def evaluate_match(self, match):
        """Valuta se le previsioni erano corrette."""
        home_score = match.get("home_score")
        away_score = match.get("away_score")
        status = match.get("status", "")

        if "FT" not in status.upper() and "CONCLUSA" not in status.upper() and "POST" not in status.upper():
            return None
            
        if home_score is None or away_score is None:
            return None

        results = {}
        try:
            top_preds = match.get("top_predictions", [])
            if not top_preds and "predictions_json" in match:
                try:
                    data = json.loads(match["predictions_json"])
                    top_preds = data.get("top_predictions", [])
                except: pass
            
            for p in top_preds:
                if "prob" not in p: continue
                m = clean_market(p.get("market", ""))
                is_won = settle_market(m, int(home_score), int(away_score))
                results[m] = {"won": is_won, "prob": p["prob"], "odd": p.get("odd", 0)}
        except Exception as e:
            print(f"[AI TRAINER] Errore eval: {e}")
            return None
            
        return results

    def _get_bucket(self, prob):
        if prob < 20: return "0-20"
        elif prob < 40: return "20-40"
        elif prob < 60: return "40-60"
        elif prob < 80: return "60-80"
        else: return "80-100"

    def run_training_loop(self):
        """Scorre il DB, valuta i risultati e accumula bucket per calibrazione Platt-style."""
        print("[AI TRAINER] Inizio ciclo di valutazione per Calibrazione (Fase 2)...")
        all_matches = self.db.get_all_matches()
        
        # Reset buckets to recalculate from scratch based on all historical data
        for k in self.weights["buckets"]:
            self.weights["buckets"][k] = {"n": 0, "won": 0, "sum_p": 0.0}
            
        total_eval = 0
        won_eval = 0
        
        for match in all_matches:
            eval_results = self.evaluate_match(match)
            if not eval_results:
                continue
                
            for market, data in eval_results.items():
                prob = data["prob"]
                if prob == 0: continue
                
                total_eval += 1
                if data["won"]: won_eval += 1
                
                bucket = self._get_bucket(prob)
                self.weights["buckets"][bucket]["n"] += 1
                self.weights["buckets"][bucket]["sum_p"] += prob
                if data["won"]:
                    self.weights["buckets"][bucket]["won"] += 1

        # Calculate Calibration Factors
        print("\n[AI TRAINER] --- REPORT CALIBRAZIONE ---")
        for b_name, b_data in self.weights["buckets"].items():
            n = b_data["n"]
            if n > 200:
                avg_prob = b_data["sum_p"] / n
                real_hit_rate = (b_data["won"] / n) * 100
                ratio = real_hit_rate / avg_prob if avg_prob > 0 else 1.0
                
                # Smooth the calibration update (alpha = 0.5)
                # Prevent extreme changes
                ratio = max(0.5, min(1.5, ratio)) 
                self.weights["calibration_factors"][b_name] = round(ratio, 3)
                
                print(f"Bucket {b_name}% (n={n}): Stimata={avg_prob:.1f}%, Reale={real_hit_rate:.1f}% -> Calib={ratio:.2f}")
            else:
                print(f"Bucket {b_name}% (n={n}): Campione insufficiente (<200) per calibrare.")
                self.weights["calibration_factors"][b_name] = 1.0

        self.save_weights()
        accuracy = (won_eval / total_eval * 100) if total_eval > 0 else 0
        print(f"\n[AI TRAINER] Addestramento completato. Accuratezza Storica Reale: {accuracy:.1f}% su {total_eval} bet valutati.")

if __name__ == "__main__":
    trainer = AITrainer()
    trainer.run_training_loop()
