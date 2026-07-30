import os
import urllib.parse
from datetime import datetime
from flask import Flask, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Standard browser headers required to bypass 403 blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def scrape_voice_acting_club(logs):
    opportunities = []
    urls = [
        ("Paid", "https://voiceactingclub.com/category/paid/feed/"),
        ("Unpaid", "https://voiceactingclub.com/category/unpaid/feed/"),
    ]

    for category, url in urls:
        source_label = f"Voice Acting Club ({category})"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.raise_for_status()

            # Using html.parser prevents strict XML 'invalid token' crashes
            soup = BeautifulSoup(res.content, "html.parser")
            items = soup.find_all("item")

            for item in items:
                title = item.find("title").get_text() if item.find("title") else "Untitled Post"
                link = item.find("link").get_text() if item.find("link") else url
                pub_date = item.find("pubdate").get_text() if item.find("pubdate") else "Recent"

                opportunities.append({
                    "source": source_label,
                    "title": title,
                    "link": link,
                    "date": pub_date,
                    "type": category,
                })
        except Exception as e:
            logs.append(f"{source_label}: {str(e)}")

    return opportunities


def scrape_reddit(logs):
    subreddits = ["recordthis", "VoiceActing", "VoiceOver", "INAT", "AudioDrama"]
    opportunities = []

    for sub in subreddits:
        source_label = f"Reddit /r/{sub}"
        url = f"https://www.reddit.com/r/{sub}/new.json?limit=15"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                logs.append(f"{source_label}: HTTP Error {res.status_code}")
                continue

            data = res.json()
            posts = data.get("data", {}).get("children", [])

            keywords = ["casting", "hiring", "paid", "va needed", "voice artist", "voice actor"]
            for post in posts:
                pdata = post.get("data", {})
                title = pdata.get("title", "")

                if any(kw in title.lower() for kw in keywords):
                    created_dt = datetime.fromtimestamp(pdata.get("created_utc", 0)).strftime("%Y-%m-%d")
                    opportunities.append({
                        "source": source_label,
                        "title": title,
                        "link": f"https://reddit.com{pdata.get('permalink')}",
                        "date": created_dt,
                        "type": "Community Post",
                    })
        except Exception as e:
            logs.append(f"{source_label}: {str(e)}")

    return opportunities


def scrape_bluesky(logs):
    opportunities = []
    source_label = "Bluesky Public API"
    query = urllib.parse.quote('"voice artist needed" OR "voice actor needed" OR "casting call"')
    url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={query}&limit=20"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            logs.append(f"{source_label}: HTTP Error {res.status_code}")
            return opportunities

        data = res.json()
        for post in data.get("posts", []):
            text = post.get("record", {}).get("text", "")
            author = post.get("author", {}).get("handle", "unknown")
            rkey = post.get("uri", "").split("/")[-1]

            opportunities.append({
                "source": "Bluesky Network",
                "title": f"@{author}: {text[:120]}...",
                "link": f"https://bsky.app/profile/{author}/post/{rkey}",
                "date": post.get("indexedAt", "")[:10],
                "type": "Open Network Call",
            })
    except Exception as e:
        logs.append(f"{source_label}: {str(e)}")

    return opportunities


def scrape_linkedin(logs):
    opportunities = []
    source_label = "LinkedIn Open Networks"
    search_query = 'site:linkedin.com/posts ("voice artist needed" OR "voice actor needed" OR "voice casting")'
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(search_query)}"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            logs.append(f"{source_label}: HTTP Error {res.status_code}")
            return opportunities

        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all("div", class_="result__body")

        for result in results:
            title_elem = result.find("a", class_="result__url")
            snippet_elem = result.find("a", class_="result__snippet")

            if title_elem and snippet_elem:
                snippet = snippet_elem.get_text().strip()
                raw_link = title_elem["href"]

                # Extract real destination link from DuckDuckGo redirect
                if "uddg=" in raw_link:
                    raw_link = urllib.parse.unquote(raw_link.split("uddg=")[1].split("&")[0])

                opportunities.append({
                    "source": "LinkedIn Post",
                    "title": snippet[:140] + "...",
                    "link": raw_link,
                    "date": "Recent",
                    "type": "Professional Call",
                })
    except Exception as e:
        logs.append(f"{source_label}: {str(e)}")

    return opportunities


@app.route("/api/scrape", methods=["GET"])
def run_scrubber():
    logs = []
    results = []

    results.extend(scrape_voice_acting_club(logs))
    results.extend(scrape_reddit(logs))
    results.extend(scrape_bluesky(logs))
    results.extend(scrape_linkedin(logs))

    return jsonify({
        "status": "success",
        "count": len(results),
        "data": results,
        "logs": logs
    })


@app.route("/")
def index():
    # Embedded HTML UI matching your application layout
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Casting Scraper Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-50 p-8 font-sans text-slate-800">
        <div class="max-w-7xl mx-auto space-y-6">
            
            <div class="flex items-center space-x-4">
                <button id="scrubBtn" onclick="runScrape()" class="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-md shadow-sm transition">
                    🔍 Scrub Open Casting Directories Now
                </button>
                <button onclick="clearFeed()" class="bg-blue-500 hover:bg-blue-600 text-white font-medium px-4 py-2 rounded-md shadow-sm transition">
                    🧹 Clear Feed
                </button>
            </div>

            <div id="statusBanner" class="hidden p-4 rounded-md text-sm font-medium"></div>

            <details class="bg-white border border-slate-200 rounded-md p-4 shadow-sm">
                <summary class="cursor-pointer font-semibold text-amber-600 flex items-center gap-2">
                    ⚠️ View Network Connection Logs (<span id="logCount">0</span>)
                </summary>
                <ul id="logList" class="mt-3 space-y-1 font-mono text-xs text-red-600 list-disc list-inside">
                    <li class="text-slate-400 italic">No network errors reported yet.</li>
                </ul>
            </details>

            <div class="bg-white border border-slate-200 rounded-md p-6 shadow-sm space-y-4">
                <h2 class="text-xl font-bold flex items-center gap-2 text-slate-900">
                    🔍 Opportunity Search & Specs
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-500 mb-1">Discipline</label>
                        <select class="w-full border border-slate-200 bg-slate-50 rounded px-3 py-2 text-sm">
                            <option>All Disciplines</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-500 mb-1">Target Sex / Gender</label>
                        <select class="w-full border border-slate-200 bg-slate-50 rounded px-3 py-2 text-sm">
                            <option>All / Any</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-500 mb-1">Application Method</label>
                        <select class="w-full border border-slate-200 bg-slate-50 rounded px-3 py-2 text-sm">
                            <option>All Methods</option>
                        </select>
                    </div>
                </div>
            </div>

            <div id="resultsContainer" class="space-y-3">
                <div id="emptyState" class="bg-blue-50 text-blue-800 p-4 rounded-md text-sm">
                    No active opportunities loaded. Click '🔍 Scrub Open Casting Directories Now' above.
                </div>
            </div>
        </div>

        <script>
            async function runScrape() {
                const btn = document.getElementById('scrubBtn');
                const banner = document.getElementById('statusBanner');
                const container = document.getElementById('resultsContainer');
                const logList = document.getElementById('logList');
                const logCount = document.getElementById('logCount');

                btn.innerText = "⏳ Scrubbing Live Feeds...";
                btn.disabled = true;

                try {
                    const res = await fetch('/api/scrape');
                    const data = await res.json();

                    banner.className = "p-4 rounded-md text-sm font-medium bg-amber-50 text-amber-900 border border-amber-200 block";
                    banner.innerText = `Scraper completed. Parsed ${data.count} items from live sources.`;

                    // Render Logs
                    logCount.innerText = data.logs.length;
                    if (data.logs.length > 0) {
                        logList.innerHTML = data.logs.map(l => `<li>${l}</li>`).join('');
                    } else {
                        logList.innerHTML = `<li class="text-emerald-600">All connections successful. No errors.</li>`;
                    }

                    // Render Cards
                    if (data.data.length > 0) {
                        container.innerHTML = data.data.map(item => `
                            <div class="bg-white border border-slate-200 p-4 rounded-md shadow-sm flex justify-between items-start">
                                <div>
                                    <span class="text-xs font-semibold px-2 py-0.5 rounded bg-blue-100 text-blue-800">${item.source}</span>
                                    <span class="text-xs font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600 ml-2">${item.type}</span>
                                    <h3 class="text-base font-bold text-slate-900 mt-2">${item.title}</h3>
                                    <p class="text-xs text-slate-400 mt-1">Date Posted: ${item.date}</p>
                                </div>
                                <a href="${item.link}" target="_blank" class="bg-slate-900 hover:bg-slate-800 text-white text-xs px-3 py-2 rounded-md transition font-medium">
                                    View Post ↗
                                </a>
                            </div>
                        `).join('');
                    } else {
                        container.innerHTML = `<div class="bg-amber-50 text-amber-800 p-4 rounded-md text-sm">No items found matching criteria across live sources.</div>`;
                    }
                } catch (err) {
                    banner.className = "p-4 rounded-md text-sm font-medium bg-red-50 text-red-800 block";
                    banner.innerText = "Error executing scraper requests.";
                } finally {
                    btn.innerText = "🔍 Scrub Open Casting Directories Now";
                    btn.disabled = false;
                }
            }

            function clearFeed() {
                document.getElementById('resultsContainer').innerHTML = `
                    <div id="emptyState" class="bg-blue-50 text-blue-800 p-4 rounded-md text-sm">
                        No active opportunities loaded. Click '🔍 Scrub Open Casting Directories Now' above.
                    </div>
                `;
                document.getElementById('statusBanner').classList.add('hidden');
                document.getElementById('logList').innerHTML = `<li class="text-slate-400 italic">No network errors reported yet.</li>`;
                document.getElementById('logCount').innerText = "0";
            }
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
