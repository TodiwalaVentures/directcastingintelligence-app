import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import streamlit as st

# Streamlit Page Configuration
st.set_page_config(
    page_title="Direct Casting Intelligence",
    layout="wide",
    page_icon="🔍"
)

# Custom Styling to match your dashboard
st.markdown("""
    <style>
    .source-badge {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    .type-badge {
        background-color: #F1F5F9;
        color: #475569;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
        margin-left: 6px;
    }
    </style>
""", unsafe_allow_html=True)

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


# --- App State Initialization ---
if "results" not in st.session_state:
    st.session_state["results"] = []
if "logs" not in st.session_state:
    st.session_state["logs"] = []
if "has_run" not in st.session_state:
    st.session_state["has_run"] = False


# --- Action Controls ---
col1, col2, _ = st.columns([2.5, 1.5, 6])

with col1:
    if st.button("🔍 Scrub Open Casting Directories Now", type="primary", use_container_width=True):
        with st.spinner("Scrubbing Live Feeds..."):
            logs = []
            results = []
            results.extend(scrape_voice_acting_club(logs))
            results.extend(scrape_reddit(logs))
            results.extend(scrape_bluesky(logs))
            results.extend(scrape_linkedin(logs))

            st.session_state["results"] = results
            st.session_state["logs"] = logs
            st.session_state["has_run"] = True
        st.rerun()

with col2:
    if st.button("🧹 Clear Feed", use_container_width=True):
        st.session_state["results"] = []
        st.session_state["logs"] = []
        st.session_state["has_run"] = False
        st.rerun()


# --- Status Banner ---
if st.session_state["has_run"]:
    st.info(f"Scraper completed. Parsed {len(st.session_state['results'])} items from live sources.")


# --- Connection Logs Expander ---
log_count = len(st.session_state["logs"])
with st.expander(f"⚠️ View Network Connection Logs ({log_count})", expanded=False):
    if log_count > 0:
        for log_entry in st.session_state["logs"]:
            st.error(f"• {log_entry}")
    else:
        st.success("All connections successful. No network errors reported.")


# --- Filters & Search Specs ---
st.markdown("### 🔍 Opportunity Search & Specs")
f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 2])

with f_col1:
    st.selectbox("Discipline", ["All Disciplines"])
with f_col2:
    st.selectbox("Target Sex / Gender", ["All / Any"])
with f_col3:
    st.selectbox("Application Method", ["All Methods"])
with f_col4:
    st.checkbox("Strict Voice Quality Filter")

st.divider()


# --- Results Display ---
if not st.session_state["has_run"] and not st.session_state["results"]:
    st.info("No active opportunities loaded. Click '🔍 Scrub Open Casting Directories Now' above.")
elif st.session_state["has_run"] and not st.session_state["results"]:
    st.warning("No active items found matching criteria across live sources.")
else:
    for item in st.session_state["results"]:
        card_col1, card_col2 = st.columns([5, 1])
        with card_col1:
            st.markdown(
                f"<span class='source-badge'>{item['source']}</span> "
                f"<span class='type-badge'>{item['type']}</span>",
                unsafe_allow_html=True
            )
            st.markdown(f"**{item['title']}**")
            st.caption(f"Date Posted: {item['date']}")
        with card_col2:
            st.link_button("View Post ↗", item["link"], use_container_width=True)
        st.divider()
