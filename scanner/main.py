#!/usr/bin/env python3
"""RevOps Hidden Job Radar

Scans public business/news/search pages for pre-hiring signals and writes a ranked
lead list to data/leads.json. Designed to run from GitHub Actions or locally.

This is intentionally lightweight: no paid APIs required, no database required.
"""
from __future__ import annotations

import json
import re
import time
import hashlib
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SOURCES_PATH = DATA_DIR / "sources.json"
KEYWORDS_PATH = DATA_DIR / "keywords.json"
LEADS_PATH = DATA_DIR / "leads.json"

USER_AGENT = "RevOps-Hidden-Job-Radar/1.0 (+https://github.com/ClutchFourSix/RevOps)"


@dataclass
class Lead:
    id: str
    company: str
    signal: str
    source: str
    url: str
    score: int
    detected_at: str
    evidence: str
    suggested_pitch: str


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def fetch_url(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(500_000)
    return raw.decode("utf-8", errors="ignore")


def strip_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def duckduckgo_html_search(query: str, max_results: int = 8) -> list[dict]:
    encoded = urllib.parse.urlencode({"q": query})
    url = f"https://duckduckgo.com/html/?{encoded}"
    html = fetch_url(url)
    results: list[dict] = []

    # DuckDuckGo's lightweight HTML page uses result__a links. This parser is
    # deliberately forgiving so the scanner still works if markup changes a bit.
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>[\s\S]*?)</a>',
        re.I,
    )
    for match in pattern.finditer(html):
        href = match.group("href")
        title = strip_html(match.group("title"))
        if "uddg=" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            href = qs.get("uddg", [href])[0]
        if title and href.startswith("http"):
            results.append({"title": title, "url": href})
        if len(results) >= max_results:
            break
    return results


def score_text(text: str, keyword_config: dict) -> tuple[int, list[str]]:
    haystack = text.lower()
    score = 0
    hits: list[str] = []
    for category in keyword_config.get("categories", []):
        weight = int(category.get("weight", 1))
        for phrase in category.get("phrases", []):
            if phrase.lower() in haystack:
                score += weight
                hits.append(phrase)
    return score, hits


def guess_company(title: str, url: str) -> str:
    # Simple first pass: use title before separators, else domain.
    clean = re.split(r"[|:–—-]", title)[0].strip()
    if 2 <= len(clean) <= 80:
        return clean
    domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
    return domain.split(".")[0].title() if domain else "Unknown Company"


def make_pitch(company: str, signal: str) -> str:
    return (
        f"Call {company} with a useful, non-pushy angle: 'I noticed signs that you're {signal.lower()}. "
        "When companies hit that stage, they often need cleaner lead flow, recruiting support, or sales ops help before they post roles publicly. "
        "Would it be useful if I sent a short list of prospects or process gaps I found?'"
    )


def build_leads() -> list[Lead]:
    sources = load_json(SOURCES_PATH, {"queries": []})
    keywords = load_json(KEYWORDS_PATH, {"categories": []})
    now = datetime.now(timezone.utc).isoformat()
    found: dict[str, Lead] = {}

    for source in sources.get("queries", []):
        query = source.get("query", "").strip()
        signal_name = source.get("signal", "Growth signal")
        if not query:
            continue
        try:
            results = duckduckgo_html_search(query, max_results=int(source.get("max_results", 8)))
        except Exception as exc:
            print(f"WARN: query failed: {query}: {exc}")
            continue

        for result in results:
            title = result["title"]
            url = result["url"]
            evidence_text = title
            try:
                page = fetch_url(url, timeout=10)
                evidence_text = strip_html(page)[:4000] or title
                time.sleep(1)
            except Exception:
                pass

            score, hits = score_text(f"{title} {evidence_text}", keywords)
            if score < int(source.get("min_score", 4)):
                continue

            company = guess_company(title, url)
            evidence = "; ".join(hits[:6]) if hits else title
            lead_id = hashlib.sha1(f"{company}|{url}".encode("utf-8")).hexdigest()[:12]
            lead = Lead(
                id=lead_id,
                company=company,
                signal=signal_name,
                source=query,
                url=url,
                score=score,
                detected_at=now,
                evidence=evidence,
                suggested_pitch=make_pitch(company, signal_name),
            )
            found[lead_id] = lead

    existing = load_json(LEADS_PATH, [])
    for item in existing:
        if isinstance(item, dict) and item.get("id") and item["id"] not in found:
            found[item["id"]] = Lead(**item)

    return sorted(found.values(), key=lambda lead: lead.score, reverse=True)[:100]


def main() -> None:
    leads = build_leads()
    save_json(LEADS_PATH, [asdict(lead) for lead in leads])
    print(f"Saved {len(leads)} leads to {LEADS_PATH}")


if __name__ == "__main__":
    main()
