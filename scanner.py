import json
import feedparser
from datetime import datetime

KEYWORDS = {
    "pain": ["overwhelmed", "too busy", "backlog", "missed calls"],
    "growth": ["growing fast", "expanding", "new clients"],
    "hiring": ["need help", "looking for someone", "recommend someone"],
    "sales": ["more leads", "appointments", "follow up"]
}

SOURCES = [
    "https://news.google.com/rss/search?q=small+business+growth",
    "https://www.reddit.com/search.rss?q=business+need+help"
]

def score_text(text):
    score = 0
    matched = []

    for category, words in KEYWORDS.items():
        for w in words:
            if w in text.lower():
                score += 15
                matched.append(w)

    return score, matched

results = []

for url in SOURCES:
    feed = feedparser.parse(url)

    for entry in feed.entries[:15]:
        text = entry.title + " " + entry.get("summary", "")
        score, matches = score_text(text)

        if score > 0:
            results.append({
                "score": score,
                "company": "Unknown",
                "title": entry.title,
                "signal_summary": text[:140],
                "likely_need": "Sales / Ops Help",
                "recommended_action": "Research and reach out",
                "source": url,
                "url": entry.link,
                "matched_terms": matches,
                "published": str(datetime.now().date())
            })

results = sorted(results, key=lambda x: x["score"], reverse=True)

with open("docs/leads.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"Saved {len(results)} leads")
