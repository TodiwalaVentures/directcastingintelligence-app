import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Unique User-Agent format to avoid generic Python cloud scraper blocks
SCRAPER_HEADERS = {
    "User-Agent": "DirectCastingIntelligence/1.0 (Casting Search Aggregator)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def scrape_voice_acting_club(logs):
    """Scrapes Voice Acting Club RSS feeds using lenient HTML parsing."""
    opportunities = []
    urls = [
        ("Paid", "https://voiceactingclub.com/category/paid/feed/"),
        ("Unpaid", "https://voiceactingclub.com/category/unpaid/feed/"),
    ]

    for category, url in urls:
        source_label = f"Voice Acting Club ({category})"
        try:
            res = requests.get(url, headers=SCRAPER_HEADERS, timeout=10)
            res.raise_for_status()

            soup = BeautifulSoup(res.content, "html.parser")
            items = soup.find_all("item")

            for item in items:
                title = item.find("title").get_text() if item.find("title") else "Untitled Call"
                link = item.find("link").get_text() if item.find("link") else url
                pub_date = item.find("pubdate").get_text() if item.find("pubdate") else "Recent"

                opportunities.append({
                    "source": source_label,
                    "title": title.strip(),
                    "link": link.strip(),
                    "date": pub_date[:16] if len(pub_date) > 16 else pub_date,
                    "type": f"VAC {category}",
                })
        except Exception as e:
            logs.append(f"{source_label}: {str(e)}")

    return opportunities


def scrape_reddit_rss(logs):
    """Bypasses Reddit 403 datacenter blocks by utilizing RSS endpoints."""
    subreddits = ["recordthis", "VoiceActing", "VoiceOver", "INAT", "AudioDrama"]
    opportunities = []

    for sub in subreddits:
        source_label = f"Reddit /r/{sub}"
        # .rss endpoints are significantly less restrictive than .json endpoints on cloud IPs
        url = f"https://www.reddit.com/r/{sub}/new/.rss"
        try:
            res = requests.get(url, headers=SCRAPER_HEADERS, timeout=10)
            if res.status_code != 200:
                logs.append(f"{source_label}: HTTP Error {res.status_code}")
                continue

            soup = BeautifulSoup(res.content, "xml")
            entries = soup.find_all("entry")

            keywords = ["casting", "hiring", "paid", "va needed", "voice artist", "voice actor", "looking for voice"]
            for entry in entries:
                title_elem = entry.find("title")
                link_elem = entry.find("link")
                updated_elem = entry.find("updated")

                if title_elem:
                    title = title_elem.get_text()
                    if any(kw in title.lower() for kw in keywords):
                        link = link_elem["href"] if link_elem and "href" in link_elem.attrs else f"https://reddit.com/r/{sub}"
                        date_str = updated_elem.get_text()[:10] if updated_elem else "Recent"

                        opportunities.append({
                            "source": source_label,
                            "title": title.strip(),
                            "link": link,
                            "date": date_str,
                            "type": "Community Call",
                        })
        except Exception as e:
            logs.append(f"{source_label}: {str(e)}")

    return opportunities


def scrape_open_web_search(logs):
    """
    Scrapes public LinkedIn posts, Bluesky, and open web directories
    mentioning 'Voice Artist Needed' via search indexing to prevent direct IP blocks.
    """
    opportunities = []
    queries = [
        ("LinkedIn Open Posts", 'site:linkedin.com/posts ("voice artist needed" OR "voice actor needed")'),
        ("Bluesky Open Posts", 'site:bsky.app/profile ("voice artist needed" OR "voice actor needed")'),
    ]

    for label, search_query in queries:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(search_query)}"
        try:
            res = requests.get(url, headers=SCRAPER_HEADERS, timeout=10)
            if res.status_code != 200:
                logs.append(f"{label}: HTTP Error {res.status_code}")
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            results = soup.find_all("div", class_="result__body")

            for result in results:
                title_elem = result.find("a", class_="result__url")
                snippet_elem = result.find("a", class_="result__snippet")

                if title_elem and snippet_elem:
                    snippet = snippet_elem.get_text().strip()
                    raw_link = title_elem["href"]

                    # Decode DDG redirect URL to get direct link
                    if "uddg=" in raw_link:
                        raw_link = urllib.parse.unquote(raw_link.split("uddg=")[1].split("&")[0])

                    opportunities.append({
                        "source": label,
                        "title": snippet[:140] + "...",
                        "link": raw_link,
                        "date": "Recent",
                        "type": "Web Search Call",
                    })
        except Exception as e:
            logs.append(f"{label}: {str(e)}")

    return opportunities


def run_all_scrapers():
    """Aggregates all results and network logs."""
    logs = []
    results = []

    results.extend(scrape_voice_acting_club(logs))
    results.extend(scrape_reddit_rss(logs))
    results.extend(scrape_open_web_search(logs))

    return results, logs
