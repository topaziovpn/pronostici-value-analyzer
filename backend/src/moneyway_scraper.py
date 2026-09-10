import urllib.request
import urllib.parse
import re
import json

def calc_movement(opening, current):
    if opening is None or current is None:
        return None
    if opening <= 1.01 or current <= 1.01:
        return None
    delta_pct = (current - opening) / opening * 100
    if abs(delta_pct) > 60:      # sanity check: nessun mercato serio si muove cosi'
        return None
    return round(delta_pct, 2)

class MoneyWayScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'X-Requested-With': 'XMLHttpRequest'}
        pageData = {"id":"1","sport":"soccer","pg":"soccer/football-odds-trends/money-way","date":"next-2days","country":"all","bookie":"12X","type":"date","sort":"OV","oddType":"eu","tz":"","upd":5}
        j_str = json.dumps(pageData)
        enc = urllib.parse.quote(j_str)
        self.btfodds_url = 'https://www.btfodds.com/classes/soccer/football-odds-trends/money-way.php?alldata=' + enc

    def fetch_smart_money(self):
        print('[MONEY WAY] Inizio ricerca flussi anomali e variazioni quote su BTFOdds...')
        try:
            req = urllib.request.Request(self.btfodds_url, headers=self.headers)
            html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
            
            results = {}
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
            for row in rows:
                if '&#0128;' in row or 'data-volume' in row:
                    teams_match = re.search(r'<td class="event">.*?<a[^>]*>(.*?)VS(.*?)</a>', row, re.IGNORECASE)
                    if teams_match:
                        home = re.sub(r'<[^>]+>', '', teams_match.group(1)).strip()
                        away = re.sub(r'<[^>]+>', '', teams_match.group(2)).strip()
                        
                        volumes = re.findall(r'data-volume="([0-9\.]+)"', row)
                        odds_data = re.findall(r'<td[^>]*title="[^"]*?([0-9\\.]+)[^"]*?".*?>\\s*<a[^>]*>([0-9\\.]+)</a>', row)
                        
                        if len(volumes) >= 4:
                            try:
                                vol_1 = float(volumes[0])
                                vol_x = float(volumes[1])
                                vol_2 = float(volumes[2])
                                total_vol = float(volumes[3])
                                
                                trends = {}
                                if len(odds_data) >= 3:
                                    for idx, key in enumerate(['1', 'X', '2']):
                                        try:
                                            o = float(odds_data[idx][0])
                                            c = float(odds_data[idx][1])
                                            if calc_movement(o, c) is not None:
                                                trends[key] = {'open': o, 'current': c}
                                        except: pass
                                
                                p_1 = (vol_1 / total_vol) * 100 if total_vol else 0
                                p_x = (vol_x / total_vol) * 100 if total_vol else 0
                                p_2 = (vol_2 / total_vol) * 100 if total_vol else 0
                                
                                results[home.lower()] = {
                                    'home': home,
                                    'away': away,
                                    'volumes': {'1': vol_1, 'X': vol_x, '2': vol_2, 'total': total_vol},
                                    'percentages': {'1': round(p_1, 2), 'X': round(p_x, 2), '2': round(p_2, 2)},
                                    'smart_money': '1' if p_1 > 70 else '2' if p_2 > 70 else 'X' if p_x > 70 else None,
                                    'trends': trends
                                }
                            except ValueError:
                                pass
                            
            print(f'[MONEY WAY] Estratti dati per {len(results)} partite valide (volumi e trend).')
            return results
        except Exception as e:
            print(f'[MONEY WAY] Errore durante il fetch: {e}')
            return {}

if __name__ == '__main__':
    mw = MoneyWayScraper()
    data = mw.fetch_smart_money()
    print(json.dumps(data, indent=2)[:500])
