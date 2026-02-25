"""
scraper.py — Fetch and cache Pro Football Reference pages.
"""
from __future__ import annotations

import time
import pathlib
import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
BASE_URL = "https://www.pro-football-reference.com"


def _get(url: str, retries: int = 1) -> requests.Response:
    """GET with a single 429-retry at 30 s."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code == 429 and retries > 0:
        print(f"  429 — waiting 30 s before retry: {url}")
        time.sleep(30)
        return _get(url, retries - 1)
    resp.raise_for_status()
    return resp


def scrape_draft_year(year: int) -> pd.DataFrame:
    """
    Fetch the PFR draft page for *year* and return a tidy DataFrame.

    Columns: year, round, pick, team, player_name, position, age, college
    """
    url = f"{BASE_URL}/draft/{year}-nfl-draft.htm"
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "lxml")

    table = soup.find("table", {"id": "drafts"})
    if table is None:
        raise ValueError(f"Could not find #drafts table for year {year}")

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        if "thead" in tr.get("class", []):
            continue
        tds = tr.find_all(["th", "td"])
        if not tds:
            continue
        try:
            row = {
                "year": year,
                "round": tds[0].get_text(strip=True),
                "pick": tds[1].get_text(strip=True),
                "team": tds[2].get_text(strip=True),
                "player_name": tds[3].get_text(strip=True),
                "position": tds[4].get_text(strip=True),
                "age": tds[5].get_text(strip=True),
                "college": tds[7].get_text(strip=True) if len(tds) > 7 else "",
            }
            rows.append(row)
        except IndexError:
            continue

    return pd.DataFrame(rows)


def scrape_allpro_year(year: int) -> pd.DataFrame:
    """
    Fetch the PFR All-Pro page for *year* and return a tidy DataFrame.

    Columns: year, player_name, position, team
    """
    url = f"{BASE_URL}/years/{year}/allpro.htm"
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "lxml")

    # The first table on the page is the First-Team All-Pro selections
    table = soup.find("table")
    if table is None:
        raise ValueError(f"Could not find All-Pro table for year {year}")

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        if "thead" in tr.get("class", []):
            continue
        tds = tr.find_all(["th", "td"])
        if not tds:
            continue
        try:
            row = {
                "year": year,
                "player_name": tds[1].get_text(strip=True),
                "position": tds[0].get_text(strip=True),
                "team": tds[2].get_text(strip=True) if len(tds) > 2 else "",
            }
            rows.append(row)
        except IndexError:
            continue

    return pd.DataFrame(rows)


def scrape_all_years(
    years: list[int],
    data_dir: str | pathlib.Path,
    delay: float = 3.0,
) -> None:
    """
    Iterate *years*, scrape draft + All-Pro data, and cache as CSVs.

    Skips a year if the CSV already exists.  Sleeps *delay* seconds between
    requests to be a polite scraper.
    """
    data_dir = pathlib.Path(data_dir)
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for year in years:
        draft_path = raw_dir / f"draft_{year}.csv"
        allpro_path = raw_dir / f"allpro_{year}.csv"

        if not draft_path.exists():
            print(f"Scraping draft {year}…")
            df = scrape_draft_year(year)
            df.to_csv(draft_path, index=False)
            time.sleep(delay)
        else:
            print(f"  draft_{year}.csv already cached — skipping")

        if not allpro_path.exists():
            print(f"Scraping allpro {year}…")
            df = scrape_allpro_year(year)
            df.to_csv(allpro_path, index=False)
            time.sleep(delay)
        else:
            print(f"  allpro_{year}.csv already cached — skipping")

    print("Scraping complete.")
