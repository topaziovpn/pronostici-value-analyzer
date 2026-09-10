import tkinter as tk
from tkinter import ttk, messagebox
import yaml
import csv
from pathlib import Path
import sys
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
EXAMPLE_PATH = BASE_DIR / "config.example.yaml"
CSV_PATH = BASE_DIR / "input" / "palinsesto.csv"

class ConfigManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pronostici Value Analyzer - Gestione Campionati")
        self.geometry("750x850")
        
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        self.date_filter = tk.StringVar(value="Oggi")
        self.match_counts = {}
        
        # Dizionari per memorizzare i widget da aggiornare
        self.league_checkboxes = {}
        
        self.load_config()
        self.build_ui()

    def load_config(self):
        if not CONFIG_PATH.exists():
            if EXAMPLE_PATH.exists():
                import shutil
                shutil.copy(EXAMPLE_PATH, CONFIG_PATH)
            else:
                messagebox.showerror("Errore", "Impossibile trovare config.yaml o config.example.yaml")
                sys.exit(1)
                
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
            
        self.leagues = self.config.get("leagues", [])
        
        self.tree_data = {}
        for idx, l in enumerate(self.leagues):
            cont = l.get("continent", "Sconosciuto")
            ctry = l.get("country", "Sconosciuto")
            if cont not in self.tree_data:
                self.tree_data[cont] = {}
            if ctry not in self.tree_data[cont]:
                self.tree_data[cont][ctry] = []
            
            self.tree_data[cont][ctry].append((idx, l))
            
    def load_match_counts(self):
        self.match_counts.clear()
        if not CSV_PATH.exists():
            return
            
        today_str = datetime.now().strftime("%Y-%m-%d")
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        target_date = None
        if self.date_filter.get() == "Oggi":
            target_date = today_str
        elif self.date_filter.get() == "Domani":
            target_date = tomorrow_str
            
        try:
            with open(CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    match_date = row.get("date", "")
                    league = row.get("league", "")
                    
                    if target_date and match_date != target_date:
                        continue
                        
                    if league:
                        self.match_counts[league] = self.match_counts.get(league, 0) + 1
        except Exception as e:
            print(f"Errore lettura CSV: {e}")
            
    def update_labels(self):
        self.load_match_counts()
        for idx, cb in self.league_checkboxes.items():
            league_name = self.leagues[idx]["name"]
            count = self.match_counts.get(league_name, 0)
            if count > 0:
                cb.config(text=f"{league_name}  ({count} partite)")
                cb.config(fg="#006600") # Evidenzia in verde
            else:
                cb.config(text=league_name)
                cb.config(fg="#333333")

    def on_date_filter_change(self):
        self.update_labels()
            
    def add_league(self):
        # Finestra di dialogo custom per inserire Continente, Nazione e Nome Campionato
        dialog = tk.Toplevel(self)
        dialog.title("Aggiungi Campionato")
        dialog.geometry("400x250")
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Continente:", font=("Segoe UI", 10)).pack(pady=(10, 0))
        cont_entry = tk.Entry(dialog, font=("Segoe UI", 10), width=30)
        cont_entry.pack()
        
        tk.Label(dialog, text="Nazione:", font=("Segoe UI", 10)).pack(pady=(10, 0))
        ctry_entry = tk.Entry(dialog, font=("Segoe UI", 10), width=30)
        ctry_entry.pack()
        
        tk.Label(dialog, text="Nome Campionato:", font=("Segoe UI", 10)).pack(pady=(10, 0))
        name_entry = tk.Entry(dialog, font=("Segoe UI", 10), width=30)
        name_entry.pack()
        
        def save_new():
            cont = cont_entry.get().strip()
            ctry = ctry_entry.get().strip()
            name = name_entry.get().strip()
            
            if not cont or not ctry or not name:
                messagebox.showwarning("Attenzione", "Compila tutti i campi!")
                return
                
            new_league = {
                "name": name,
                "country": ctry,
                "continent": cont,
                "enabled": True,
                "priority": "medium"
            }
            self.leagues.append(new_league)
            
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
                
            messagebox.showinfo("Successo", f"{name} aggiunto con successo!\nRiavvia l'applicazione per vederlo nella lista.")
            dialog.destroy()
            
        tk.Button(dialog, text="Aggiungi", command=save_new, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold")).pack(pady=20)

    def build_ui(self):
        main_frame = tk.Frame(self, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top bar
        top_frame = tk.Frame(main_frame, bg="#333", padx=20, pady=15)
        top_frame.pack(fill=tk.X)
        
        tk.Label(top_frame, text="Seleziona i campionati da analizzare", font=("Segoe UI", 16, "bold"), fg="white", bg="#333").pack(side=tk.LEFT)
        
        save_btn = tk.Button(top_frame, text="Salva Modifiche", command=self.save_config, bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), relief=tk.FLAT, padx=15)
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        add_btn = tk.Button(top_frame, text="+ Nuovo Campionato", command=self.add_league, bg="#2196F3", fg="white", font=("Segoe UI", 12, "bold"), relief=tk.FLAT, padx=15)
        add_btn.pack(side=tk.RIGHT)
        
        # Filtri Date Bar
        filter_frame = tk.Frame(main_frame, bg="#e0e0e0", padx=20, pady=10)
        filter_frame.pack(fill=tk.X)
        
        tk.Label(filter_frame, text="Visualizza partite di:", font=("Segoe UI", 11, "bold"), bg="#e0e0e0").pack(side=tk.LEFT, padx=(0, 10))
        
        for text in ["Oggi", "Domani", "Tutte"]:
            tk.Radiobutton(filter_frame, text=text, variable=self.date_filter, value=text, 
                           command=self.on_date_filter_change, bg="#e0e0e0", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=5)
        
        # Area scorrevole
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        canvas = tk.Canvas(canvas_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        
        scrollable_frame = tk.Frame(canvas, bg="#ffffff")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=660)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.vars = {} 
        self.country_vars = {} 
        
        for cont, countries in sorted(self.tree_data.items()):
            cont_frame = tk.LabelFrame(scrollable_frame, text=cont, font=("Segoe UI", 14, "bold"), bg="#ffffff", fg="#0056b3", pady=10, padx=10, relief=tk.FLAT)
            cont_frame.pack(fill=tk.X, expand=True, pady=(0, 15))
            
            for ctry, lg_list in sorted(countries.items()):
                ctry_frame = tk.Frame(cont_frame, bg="#ffffff")
                ctry_frame.pack(fill=tk.X, pady=5)
                
                c_var = tk.BooleanVar(value=all(l["enabled"] for idx, l in lg_list))
                self.country_vars[(cont, ctry)] = c_var
                
                cb = tk.Checkbutton(ctry_frame, text=ctry, font=("Segoe UI", 12, "bold"), variable=c_var, bg="#ffffff", activebackground="#ffffff",
                                    command=lambda c=cont, ct=ctry: self.toggle_country(c, ct))
                cb.pack(anchor="w")
                
                lg_frame = tk.Frame(ctry_frame, bg="#f9f9f9", padx=30, pady=5)
                lg_frame.pack(fill=tk.X)
                
                for idx, lg in lg_list:
                    l_var = tk.BooleanVar(value=lg["enabled"])
                    self.vars[idx] = l_var
                    
                    lg_cb = tk.Checkbutton(lg_frame, text=lg["name"], variable=l_var, font=("Segoe UI", 11), bg="#f9f9f9", activebackground="#f9f9f9",
                                   command=lambda c=cont, ct=ctry: self.update_country_cb(c, ct))
                    lg_cb.pack(anchor="w", pady=2)
                    self.league_checkboxes[idx] = lg_cb
                    
        self.update_labels()
                                   
    def toggle_country(self, cont, ctry):
        is_checked = self.country_vars[(cont, ctry)].get()
        for idx, lg in self.tree_data[cont][ctry]:
            self.vars[idx].set(is_checked)
            
    def update_country_cb(self, cont, ctry):
        all_checked = all(self.vars[idx].get() for idx, lg in self.tree_data[cont][ctry])
        self.country_vars[(cont, ctry)].set(all_checked)
        
    def save_config(self):
        for idx, var in self.vars.items():
            self.leagues[idx]["enabled"] = var.get()
            
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            messagebox.showinfo("Successo", "Configurazione dei campionati salvata correttamente!")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare il file:\n{str(e)}")

if __name__ == "__main__":
    app = ConfigManager()
    app.mainloop()
