from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0 Safari/537.36"
)

def ddg_search(query: str, max_results: int = 8):
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        out = []
        for a in soup.select("a.result__a"):
            href = a.get("href")
            title = a.get_text(" ", strip=True)
            if href and title:
                out.append({"title": title, "url": href})
            if len(out) >= max_results:
                break
        return out
    except Exception as e:
        print(f"[DDG] Errore di ricerca: {e}")
        return []

def best_match(results, home, away):
    if not results:
        return None, 0
    target = f"{home} {away}".lower()
    best = None
    score = -1
    for x in results:
        s = fuzz.token_set_ratio(target, x["title"].lower())
        if s > score:
            best, score = x, s
    return best, score
