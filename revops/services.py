from revops.sources.search import get_candidates
from revops.enrich.scraper import enrich_company
from revops.utils.dedupe import dedupe_companies


def collect_msps(city: str, state: str):
    candidates = get_candidates(city, state)
    enriched = []

    for candidate in candidates:
        try:
            enriched.append(enrich_company(candidate))
        except Exception:
            fallback = dict(candidate)
            fallback["status"] = "enrich_failed"
            fallback.setdefault("email", "")
            fallback.setdefault("phone", "")
            fallback.setdefault("score", 0)
            fallback.setdefault("classification", "Unclear")
            enriched.append(fallback)

    return dedupe_companies(enriched)
