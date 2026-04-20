import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_candidates(city, state):
    query = f"managed IT services in {city} {state}"
    url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"

    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "lxml")

    results = []

    for item in soup.select("li.b_algo"):
        title = item.select_one("h2")
        link = item.select_one("a")

        if not title or not link:
            continue

        results.append({
            "name": title.text.strip(),
            "website": link["href"],
            "city": city,
            "state": state,
            "source": "bing"
        })

    return results
