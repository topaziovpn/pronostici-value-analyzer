import re
from bs4 import BeautifulSoup

def clean(text):
    return re.sub(r"\s+", " ", text).strip()

def extract_title(html):
    soup = BeautifulSoup(html, "lxml")
    return soup.title.get_text(" ", strip=True) if soup.title else ""

def find_stat(text, labels):
    """
    Cerca un numero vicino a una label.
    """
    low = text.lower()
    for label in labels:
        pos = low.find(label.lower())
        if pos >= 0:
            chunk = text[pos:pos+180]
            m = re.search(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*%?", chunk)
            if m:
                try:
                    return float(m.group(1).replace(",", "."))
                except ValueError:
                    pass
    return None

def extract_team_numbers(text):
    labels = {
        "xg": ["xg", "expected goals"],
        "goals_for_avg": ["goals scored per match", "goals for per match"],
        "goals_against_avg": ["goals conceded per match", "goals against per match"],
        "btts": ["btts"],
        "over25": ["over 2.5"],
        "corners": ["corners per match", "corners", "angoli"],
        "shots": ["shots per match", "total shots", "tiri"],
        "shots_on_target": ["shots on target", "tiri in porta"],
        "big_chances": ["big chances", "grandi occasioni"],
        "possession": ["possession", "ball possession", "possesso palla"],
        "yellow_cards": ["yellow cards", "cartellini gialli"]
    }
    return {k: find_stat(text, v) for k, v in labels.items()}
