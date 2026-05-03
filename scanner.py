import json
import os
from datetime import datetime
from urllib.parse import quote_plus

import requests

MODE = os.getenv("SCAN_MODE", "local").strip().lower()
CITY = os.getenv("SCAN_LOCATION", "Dallas, Texas").strip()
INDUSTRY_TERMS = [x.strip().lower() for x in os.getenv("INDUSTRY_TERMS", "plumbing,roofing,hvac,it services,marketing agency").split(",") if x.strip()]

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "RevOpsHiddenJobRadar/0.5 (GitHub Pages MVP)"}

TERM_TAGS = {
    "plumbing": [("craft", "plumber")],
    "plumber": [("craft", "plumber")],
    "roofing": [("craft", "roofer")],
    "roofer": [("craft", "roofer")],
    "hvac": [("craft", "hvac"), ("shop", "trade")],
    "electrician": [("craft", "electrician")],
    "it services": [("shop", "computer"), ("office", "it")],
    "computer": [("shop", "computer")],
    "marketing agency": [("office", "advertising_agency"), ("office", "company")],
    "agency": [("office", "advertising_agency"), ("office", "company")]
}

REMOTE_SEEDS = [
    {
        "company": "Remote SaaS Sales Signal",
        "category": "remote",
        "location": "remote",
        "phone": "",
        "website": "https://www.linkedin.com/search/results/content/?keywords=looking%20for%20SDR%20remote",
        "signal": "Remote SDR / sales development signal search"
    },
    {
        "company": "Remote Appointment Setter Signal",
        "category": "remote",
        "location": "remote",
        "phone": "",
        "website": "https://www.google.com/search?q=%22looking+for+appointment+setter%22+remote",
        "signal": "Remote appointment setter signal search"
    }
]


def get_bbox(city):
    params = {"q": city, "format": "json", "limit": 1}
    response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data:
        raise RuntimeError(f"Could not geocode location: {city}")
    south, north, west, east = data[0]["boundingbox"]
    return float(south), float(west), float(north), float(east)


def selected_tags():
    tags = []
    for term in INDUSTRY_TERMS:
        tags.extend(TERM_TAGS.get(term, []))
    if not tags:
        tags = [("craft", "plumber"), ("craft", "roofer"), ("shop", "computer"), ("office", "company")]
    return list(dict.fromkeys(tags))


def build_overpass_query(bbox):
    south, west, north, east = bbox
    bbox_text = f"{south},{west},{north},{east}"
    parts = []
    for key, value in selected_tags():
        parts.append(f'node["{key}"="{value}"]({bbox_text});')
        parts.append(f'way["{key}"="{value}"]({bbox_text});')
        parts.append(f'relation["{key}"="{value}"]({bbox_text});')
    return f"""
    [out:json][timeout:45];
    (
      {' '.join(parts)}
    );
    out center tags 120;
    """


def normalize_business(item):
    tags = item.get("tags", {})
    name = tags.get("name")
    if not name:
        return None

    phone = tags.get("phone") or tags.get("contact:phone") or tags.get("mobile") or ""
    website = tags.get("website") or tags.get("contact:website") or tags.get("url") or ""
    category = tags.get("craft") or tags.get("shop") or tags.get("office") or "local business"
    address = " ".join(filter(None, [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city") or CITY
    ]))

    return {
        "company": name,
        "phone": phone,
        "website": website,
        "category": category,
        "location": CITY,
        "address": address,
        "osm_id": item.get("id"),
        "osm_type": item.get("type")
    }


def fetch_local():
    bbox = get_bbox(CITY)
    query = build_overpass_query(bbox)
    response = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=60)
    response.raise_for_status()
    data = response.json()

    businesses = []
    seen = set()
    for item in data.get("elements", []):
        business = normalize_business(item)
        if not business:
            continue
        key = (business["company"].lower(), business.get("address", "").lower())
        if key in seen:
            continue
        seen.add(key)
        businesses.append(business)
    return businesses


def fetch_remote():
    return REMOTE_SEEDS


def score_business(b):
    score = 45
    matched = []
    if b.get("phone"):
        score += 25
        matched.append("phone listed")
    else:
        matched.append("phone not listed")
    if not b.get("website"):
        score += 25
        matched.append("no website listed")
    else:
        matched.append("website listed")
    if b.get("category") in ["plumber", "roofer", "hvac", "electrician", "computer"]:
        score += 10
        matched.append("high-value SMB niche")
    return min(score, 100), matched


def likely_need(b):
    if MODE == "remote":
        return "Remote sales / SDR / appointment-setting research"
    if b.get("phone") and not b.get("website"):
        return "Website + local lead generation"
    if not b.get("phone"):
        return "Business profile cleanup / local presence"
    return "Lead generation / visibility improvement"


def recommended_action(b):
    if MODE == "remote":
        return "Open source link and manually identify the poster/company; pitch remote SDR or appointment-setting help."
    if b.get("phone"):
        return f"Call {b.get('phone')}; offer to improve local visibility and capture more calls."
    return "Research phone/website manually; pitch profile cleanup and local lead generation."


def to_lead(b):
    score, matched = score_business(b)
    website = b.get("website") or ""
    url = website if website.startswith("http") else ("https://" + website if website else "#")
    signal = b.get("signal") or f"Category: {b.get('category', 'local business')} | Phone: {b.get('phone') or 'not listed'} | Website: {b.get('website') or 'not listed'} | Address: {b.get('address') or b.get('location', 'not listed')}"
    return {
        "score": score,
        "company": b.get("company"),
        "title": f"{b.get('company')} — {b.get('location', CITY)}",
        "signal_summary": f"Mode: {MODE} | {signal}",
        "likely_need": likely_need(b),
        "recommended_action": recommended_action(b),
        "source": "OpenStreetMap / Overpass API" if MODE == "local" else "Remote signal seed",
        "url": url,
        "matched_terms": [MODE] + matched,
        "published": str(datetime.now().date())
    }


def main():
    try:
        businesses = fetch_remote() if MODE == "remote" else fetch_local()
    except Exception as exc:
        print(f"Scanner failed: {exc}")
        businesses = []

    leads = [to_lead(b) for b in businesses]
    leads = sorted(leads, key=lambda x: x["score"], reverse=True)[:120]

    with open("docs/leads.json", "w") as f:
        json.dump(leads, f, indent=2)

    print(f"Mode: {MODE} | Location: {CITY} | Terms: {INDUSTRY_TERMS} | Leads: {len(leads)}")


if __name__ == "__main__":
    main()
