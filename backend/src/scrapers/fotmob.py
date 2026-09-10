from .web_search import ddg_search, best_match
from .browser import fetch_page
from .generic import extract_team_numbers

def scrape(home, away):
    q = f"site:fotmob.com {home} {away} football match stats"
    results = ddg_search(q, 10)
    candidate, score = best_match(results, home, away)
    if not candidate:
        return {"source": "FotMob", "found": False}

    page = fetch_page(candidate["url"])
    if not page:
        return {"source": "FotMob", "found": False}

    return {
        "source": "FotMob",
        "found": True,
        "match_confidence": score,
        "url": candidate["url"],
        "title": candidate["title"],
        "stats": extract_team_numbers(page["text"]),
    }
