import json
from datetime import datetime
import requests
import os

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

MODE = os.getenv("SCAN_MODE", "local")
CITY = os.getenv("SCAN_LOCATION", "Dallas, Texas")

TARGETS = [
    ("craft", "plumber"),
    ("craft", "roofer"),
    ("craft", "electrician"),
    ("shop", "computer"),
    ("office", "company")
]


def build_query(city):
    parts = []
    for k, v in TARGETS:
        parts.append(f'node["{k}"="{v}"](area.searchArea);')
    return f"""
    [out:json];
    area["name"="{city}"]->.searchArea;
    (
      {' '.join(parts)}
    );
    out tags 50;
    """


def fetch_local():
    query = build_query(CITY)
    res = requests.post(OVERPASS_URL, data={"data": query})
    data = res.json()

    businesses = []
    for item in data.get("elements", []):
        tags = item.get("tags", {})
        if "name" in tags:
            businesses.append({
                "company": tags.get("name"),
                "phone": tags.get("phone", ""),
                "website": tags.get("website", ""),
                "category": tags.get("craft") or tags.get("shop") or tags.get("office"),
                "location": CITY
            })

    return businesses


def fetch_remote():
    return [
        {"company": "Remote SaaS Startup", "phone": "", "website": "", "category": "remote", "location": "remote"}
    ]


def score(b):
    s = 50
    if b.get("phone"):
        s += 20
    if not b.get("website"):
        s += 20
    return min(s, 100)


if MODE == "remote":
    businesses = fetch_remote()
else:
    businesses = fetch_local()

leads = []

for b in businesses:
    leads.append({
        "score": score(b),
        "company": b["company"],
        "title": f"{b['company']} — {b['location']}",
        "signal_summary": f"Mode: {MODE}",
        "likely_need": "Lead generation",
        "recommended_action": "Call or research",
        "source": "Overpass" if MODE == "local" else "Remote",
        "url": "#",
        "matched_terms": [MODE],
        "published": str(datetime.now().date())
    })

with open("docs/leads.json", "w") as f:
    json.dump(leads, f, indent=2)

print(f"Mode: {MODE} | Location: {CITY} | Leads: {len(leads)}")
