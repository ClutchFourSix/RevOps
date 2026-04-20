import argparse
from revops.sources.search import get_candidates
from revops.enrich.scraper import enrich_company
from revops.utils.dedupe import dedupe_companies
from revops.export.csv_exporter import export_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args()

    print(f"[+] Collecting MSPs in {args.city}, {args.state}")

    candidates = get_candidates(args.city, args.state)
    print(f"[+] Found {len(candidates)} raw candidates")

    enriched = []
    for c in candidates:
        try:
            enriched.append(enrich_company(c))
        except Exception:
            print(f"[!] Failed: {c.get('name')}")

    deduped = dedupe_companies(enriched)
    print(f"[+] {len(deduped)} after dedupe")

    export_csv(deduped, f"{args.city}_msps.csv")
    print("[✓] Done")


if __name__ == "__main__":
    main()
