import json
import os
from datetime import datetime
import requests

# Optional Yelp API (set in GitHub Secrets for real data)
YELP_API_KEY = os.getenv("YELP_API_KEY")

SEARCH_TERMS = ["hvac", "roofing", "plumbing", "it services", "marketing agency"]
LOCATION = "Dallas, TX"


def score_business(b):
    score = 50

    if b.get("rating", 5) < 4:
        score += 20

    if b.get("review_count", 0) < 20:
        score += 20

    if not b.get("url"):
        score += 10

    return score


def determine_need(b):
    if b.get("rating", 5) < 4:
        return "Reputation / review generation"
    if b.get("review_count", 0) < 20:
        return "Lead generation / visibility"
    return "Sales support"


def fetch_yelp():
    if not YELP_API_KEY:
        return []

    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    results = []

    for term in SEARCH_TERMS:
        url = "https://api.yelp.com/v3/businesses/search"
        params = {"term": term, "location": LOCATION, "limit": 10}

        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            continue

        data = res.json().get("businesses", [])

        for b in data:
            results.append({
                "company": b.get("name"),
                "rating": b.get("rating"),
                "review_count": b.get("review_count"),
                "phone": b.get("display_phone"),
                "url": b.get("url")
            })

    return results


def fallback_data():
    return [
        {"company": "Dallas HVAC Pros", "rating": 3.2, "review_count": 12, "phone": "(214) 555-1234", "url": ""},
        {"company": "Elite Roofing TX", "rating": 4.1, "review_count": 8, "phone": "(214) 555-5678", "url": ""}
    ]


businesses = fetch_yelp()
if not businesses:
    businesses = fallback_data()

leads = []

for b in businesses:
    score = score_business(b)

    leads.append({
        "score": score,
        "company": b["company"],
        "title": f"{b['company']} — {LOCATION}",
        "signal_summary": f"Rating: {b.get('rating')} | Reviews: {b.get('review_count')}",
        "likely_need": determine_need(b),
        "recommended_action": f"Call {b.get('phone', 'N/A')} and offer help",
        "source": "Yelp API" if YELP_API_KEY else "Fallback Data",
        "url": b.get("url", "#"),
        "matched_terms": [],
        "published": str(datetime.now().date())
    })

leads = sorted(leads, key=lambda x: x["score"], reverse=True)

with open("docs/leads.json", "w") as f:
    json.dump(leads, f, indent=2)

print(f"Generated {len(leads)} business leads")