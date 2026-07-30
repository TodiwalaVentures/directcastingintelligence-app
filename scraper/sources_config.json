import os
import json
import logging
import urllib.request
import xml.etree.ElementTree as ET
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

class VoiceOverJobScraper:
    def __init__(self, config_file: str):
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        
        # Initialize Supabase client using environment variables
        url: str = os.environ.get("SUPABASE_URL", "")
        key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables.")
        self.supabase: Client = create_client(url, key)

    def fetch_url(self, url: str) -> str | None:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return response.read().decode("utf-8")
        except Exception as e:
            logging.error(f"Failed to fetch {url}: {e}")
        return None

    def scrape_rss(self, target: dict) -> list:
        logging.info(f"Parsing RSS Feed: {target['name']}")
        jobs = []
        xml_data = self.fetch_url(target["url"])
        if xml_data:
            try:
                root = ET.fromstring(xml_data)
                for item in root.findall(".//item"):
                    title = item.find("title").text if item.find("title") is not None else "No Title"
                    link = item.find("link").text if item.find("link") is not None else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    if link:
                        jobs.append({"source": target["name"], "title": title, "url": link, "published_date": pub_date})
            except Exception as e:
                logging.error(f"XML Parsing error on {target['name']}: {e}")
        return jobs

    def scrape_reddit_json(self, target: dict) -> list:
        logging.info(f"Parsing Reddit Feed: r/{target['subreddit']}")
        jobs = []
        raw_json = self.fetch_url(target["url"])
        if raw_json:
            try:
                data = json.loads(raw_json)
                posts = data.get("data", {}).get("children", [])
                for post in posts:
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    if any(kw in title.lower() for kw in ["casting", "voice actor", "vo", "paid", "audition"]):
                        jobs.append({
                            "source": f"r/{target['subreddit']}",
                            "title": title,
                            "url": f"https://reddit.com{post_data.get('permalink', '')}",
                            "published_date": str(post_data.get("created_utc", ""))
                        })
            except Exception as e:
                logging.error(f"JSON Parsing error on Reddit r/{target['subreddit']}: {e}")
        return jobs

    def save_to_supabase(self, jobs: list):
        """Batch upserts job records into Supabase DB (ignores existing URLs)."""
        if not jobs:
            logging.info("No jobs to save.")
            return

        logging.info(f"Sending {len(jobs)} jobs to Supabase...")
        try:
            # ignore_duplicates=True ensures existing URLs don't trigger errors
            response = self.supabase.table("job_postings").upsert(jobs, on_conflict="url", ignore_duplicates=True).execute()
            logging.info("Successfully updated Supabase DB.")
        except Exception as e:
            logging.error(f"Failed to save to Supabase: {e}")

    def run_pipeline(self):
        all_jobs = []

        for target in self.config.get("tier_1_direct_http", []):
            if target["type"] == "rss":
                all_jobs.extend(self.scrape_rss(target))

        for target in self.config.get("tier_1_reddit_json", []):
            all_jobs.extend(self.scrape_reddit_json(target))

        self.save_to_supabase(all_jobs)

if __name__ == "__main__":
    scraper = VoiceOverJobScraper("sources_config.json")
    scraper.run_pipeline()
