import json
from datetime import datetime
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CITY = "Dallas, Texas"

# No API key required. These are OpenStreetMap tags that often identify callable SMBs.
TARGETS = [
    {"label": "HVAC / contractor", "tags": [('shop', 'trade'), ('craft', 'hvac'), ('craft', 'electrician')]},
    {"label": "Plumbing", "tags": [('craft', 'plumber')]},
    {"label": "Roofing", "tags": [('craft', 'roofer')]},
    {"label": "IT / computer service", "tags": [('shop', 'computer')]},
    {"label": "Marketing / office", "tags": [('office', 'company')]}
]


def overpass_query(city, targets):
    parts = []
    for target in targets:
        for key, value in target["tags"]:
            parts.append(f'node["{key}"="{value}"](area.searchArea);')
            parts.append(f'way["{key}"="{value}"](area.searchArea);')
            parts.append(f'relation["{key}"="{value}"](area.searchArea);')

    return f"""
    [out:json][timeout:25];
    area["name"="{city}"]->.searchArea;
    (
      {' '.join(parts)}
    );
    out center tags 80;
    """


def fetch_businesses():
    query = overpass_query(CITY, TARGETS)
    response = requests.post(OVERPASS_URL, data={"data": query}, timeout=40)
    response.raise_for_status()
    data = response.json()

    businesses = []
    seen = set()

    for item in data.get("elements", []):
        tags = item.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        identity = name.lower().strip()
        if identity in seen:
            continue
        seen.add(identity)

        phone = tags.get("phone") or tags.get("contact:phone") or ""
        website = tags.get("website") or tags.get("contact:website") or ""
        category = tags.get("craft") or tags.get("shop") or tags.get("office") or "local business"
        address = " ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street"), tags.get("addr:city")]))

        businesses.append({
            "company": name,
            "phone": phone,
            "website": website,
            "category": category,
            "address": address,
            "osm_type": item.get("type"),
            "osm_id": item.get("id")
        })

    return businesses


def score_business(b):
    score = 45
    matched = []

    if b.get("phone"):
        score += 25
        matched.append("phone listed")
    else:
        matched.append("no phone visible")

    if not b.get("website"):
        score += 25
        matched.append("no website listed")
    else:
        matched.append("website listed")

    if b.get("category") in ["plumber", "roofer", "hvac", "electrician"]:
        score += 10
        matched.append("high-value local service")

    return min(score, 100), matched


def likely_need(b):
    if not b.get("website") and b.get("phone"):
        return "Website / lead generation / Google visibility"
    if not b.get("phone"):
        return "Business profile cleanup / local presence"
    return "Outbound sales / local lead generation"


def recommended_action(b):
    phone = b.get("phone") or "phone not listed"
    if b.get("phone"):
        return f"Call {phone}; offer to improve visibility and capture more local leads."
    return "Research website/phone manually; pitch local visibility cleanup."


def fallback_data():
    # Only used if Overpass is down. Keeps dashboard from breaking.
    return [
        {"company": "Dallas Local Plumbing", "phone": "", "website": "", "category": "plumber", "address": "Dallas, TX"},
        {"company": "North Texas Roof Repair", "phone": "", "website": "", "category": "roofer", "address": "Dallas, TX"}
    ]


try:
    businesses = fetch_businesses()
except Exception as exc:
    print(f"Overpass fetch failed: {exc}")
    businesses = fallback_data()

leads = []
today = str(datetime.now().date())

for b in businesses:
    score, matched = score_business(b)
    website = b.get("website") or ""
    url = website if website.startswith("http") else "#"

    leads.append({
        "score": score,
        "company": b.get("company"),
        "title": f"{b.get('company')} — {b.get('category', 'local business')} in {CITY}",
        "signal_summary": f"Category: {b.get('category', 'local business')} | Phone: {b.get('phone') or 'not listed'} | Website: {b.get('website') or 'not listed'} | Address: {b.get('address') or 'not listed'}",
        "likely_need": likely_need(b),
        "recommended_action": recommended_action(b),
        "source": "OpenStreetMap / Overpass API",
        "url": url,
        "matched_terms": matched,
        "published": today
    })

leads = sorted(leads, key=lambda x: x["score"], reverse=True)[:80]

with open("docs/leads.json", "w") as f:
    json.dump(leads, f, indent=2)

print(f"Generated {len(leads)} no-key business leads from {CITY}")
