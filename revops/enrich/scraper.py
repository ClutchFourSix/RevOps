import requests
from bs4 import BeautifulSoup
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_REGEX = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"

MSP_KEYWORDS = [
    "managed it",
    "it support",
    "cybersecurity",
    "network monitoring",
    "microsoft 365",
    "cloud services"
]


def enrich_company(company):
    url = company.get("website")

    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(res.text, "lxml")
        text = soup.get_text().lower()
    except Exception:
        company["status"] = "dead_site"
        return company

    emails = list(set(re.findall(EMAIL_REGEX, res.text)))
    phones = list(set(re.findall(PHONE_REGEX, res.text)))

    score = sum(1 for kw in MSP_KEYWORDS if kw in text)

    company["email"] = emails[0] if emails else ""
    company["phone"] = phones[0] if phones else ""
    company["score"] = score
    company["classification"] = "Likely MSP" if score >= 2 else "Unclear"

    return company
