import hashlib
import json
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import streamlit as st

# ==========================================
# PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Direct Casting Intelligence & CRM",
    layout="wide",
    page_icon="🎙️"
)

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
    .stButton>button {
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# Standard browser headers required to bypass standard cloud host blocks
SCRAPER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "user" not in st.session_state:
    st.session_state["user"] = {"logged_in": False, "username": "", "role": "Voice Artist"}
if "crm_leads" not in st.session_state:
    st.session_state["crm_leads"] = []
if "results" not in st.session_state:
    st.session_state["results"] = []
if "logs" not in st.session_state:
    st.session_state["logs"] = []
if "has_run" not in st.session_state:
    st.session_state["has_run"] = False
if "gdpr_consent" not in st.session_state:
    st.session_state["gdpr_consent"] = True

# ==========================================
# SCRAPER BACKEND LOGIC
# ==========================================
def scrape_voice_acting_club(logs):
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

            # Using html.parser prevents strict XML 'invalid token' crashes on line 19
            soup = BeautifulSoup(res.content, "html.parser")
            items = soup.find_all("item")

            for item in items:
                title = item.find("title").get_text() if item.find("title") else "Untitled Call"
                link = item.find("link").get_text() if item.find("link") else url
                pub_date = item.find("pubdate").get_text() if item.find("pubdate") else "Recent"
                item_id = hashlib.md5(link.encode()).hexdigest()[:8]

                opportunities.append({
                    "id": f"vac_{item_id}",
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
    subreddits = ["recordthis", "VoiceActing", "VoiceOver", "INAT", "AudioDrama"]
    opportunities = []

    for sub in subreddits:
        source_label = f"Reddit /r/{sub}"
        url = f"https://www.reddit.com/r/{sub}/new/.rss"
        try:
            res = requests.get(url, headers=SCRAPER_HEADERS, timeout=10)
            if res.status_code != 200:
                logs.append(f"{source_label}: HTTP Error {res.status_code}")
                continue

            soup = BeautifulSoup(res.content, "html.parser")
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
                        item_id = hashlib.md5(link.encode()).hexdigest()[:8]

                        opportunities.append({
                            "id": f"red_{item_id}",
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
    opportunities = []
    queries = [
        ("LinkedIn Open Call", 'site:linkedin.com/posts ("voice artist" OR "voice actor" OR "voice casting")'),
        ("Bluesky Network Call", 'site:bsky.app/profile ("voice artist" OR "voice actor" OR "voice casting")'),
        ("Reddit Fallback Search", 'site:reddit.com/r/VoiceActing OR site:reddit.com/r/recordthis ("casting" OR "paid" OR "hiring")'),
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

                    if "uddg=" in raw_link:
                        raw_link = urllib.parse.unquote(raw_link.split("uddg=")[1].split("&")[0])

                    item_id = hashlib.md5(raw_link.encode()).hexdigest()[:8]

                    opportunities.append({
                        "id": f"web_{item_id}",
                        "source": label,
                        "title": snippet[:130] + "...",
                        "link": raw_link,
                        "date": "Recent",
                        "type": "Open Web Call",
                    })
        except Exception as e:
            logs.append(f"{label}: {str(e)}")

    return opportunities


def run_all_scrapers():
    logs = []
    results = []
    results.extend(scrape_voice_acting_club(logs))
    results.extend(scrape_reddit_rss(logs))
    results.extend(scrape_open_web_search(logs))
    
    # Deduplicate results based on URL
    seen_links = set()
    deduped_results = []
    for r in results:
        if r["link"] not in seen_links:
            seen_links.add(r["link"])
            deduped_results.append(r)

    return deduped_results, logs


# ==========================================
# APP TABS & UI NAVIGATION
# ==========================================
st.title("🎙️ Direct Casting Intelligence Platform")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Casting Intelligence", 
    "👤 User & Profile", 
    "📊 CRM Lead Pipeline", 
    "📈 Performance Analytics", 
    "🔒 GDPR & Privacy"
])

# ------------------------------------------
# TAB 1: CASTING INTELLIGENCE & SCRAPER
# ------------------------------------------
with tab1:
    col1, col2, _ = st.columns([2.5, 1.5, 6])

    with col1:
        if st.button("🔍 Scrub Open Casting Directories Now", type="primary", use_container_width=True):
            with st.spinner("Scrubbing Live Casting Directories & Open Networks..."):
                results, logs = run_all_scrapers()
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

    if st.session_state["has_run"]:
        st.info(f"Scraper completed. Parsed {len(st.session_state['results'])} items from live sources.")

    log_count = len(st.session_state["logs"])
    with st.expander(f"⚠️ View Network Connection Logs ({log_count})", expanded=False):
        if log_count > 0:
            for log_entry in st.session_state["logs"]:
                st.error(f"• {log_entry}")
        else:
            st.success("All connections successful. No network errors reported.")

    st.markdown("### 🔍 Opportunity Search & Specs")
    f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
    with f1:
        st.selectbox("Discipline", ["All Disciplines", "Voice Acting", "Audio Drama", "Commercial", "Gaming"])
    with f2:
        st.selectbox("Target Sex / Gender", ["All / Any", "Male", "Female", "Non-Binary"])
    with f3:
        st.selectbox("Application Method", ["All Methods", "Direct Email", "External Form", "Platform DM"])
    with f4:
        st.checkbox("Strict Voice Quality Filter", value=False)

    st.divider()

    if not st.session_state["has_run"] and not st.session_state["results"]:
        st.info("No active opportunities loaded. Click '🔍 Scrub Open Casting Directories Now' above.")
    elif st.session_state["has_run"] and not st.session_state["results"]:
        st.warning("No active items found matching criteria across live sources.")
    else:
        for item in st.session_state["results"]:
            c1, c2, c3 = st.columns([5, 1.5, 1.5])
            with c1:
                st.markdown(
                    f"<span class='source-badge'>{item['source']}</span> "
                    f"<span class='type-badge'>{item['type']}</span>",
                    unsafe_allow_html=True
                )
                st.markdown(f"**{item['title']}**")
                st.caption(f"Date Posted: {item['date']}")
            with c2:
                st.link_button("View Post ↗", item["link"], use_container_width=True)
            with c3:
                if st.button("➕ Save to CRM", key=f"btn_{item['id']}", use_container_width=True):
                    if item not in st.session_state["crm_leads"]:
                        st.session_state["crm_leads"].append({**item, "status": "New Lead", "notes": ""})
                        st.toast(f"Saved to CRM Pipeline!")
            st.divider()

# ------------------------------------------
# TAB 2: USER PROFILE & AUTHENTICATION
# ------------------------------------------
with tab2:
    st.header("👤 User Account & Asset Management")
    
    if not st.session_state["user"]["logged_in"]:
        st.subheader("Login / Register")
        u_col1, u_col2 = st.columns(2)
        with u_col1:
            username = st.text_input("Username / Email", value="homer@todiwala.com")
            password = st.text_input("Password", type="password", value="••••••••••••")
            if st.button("Log In", type="primary"):
                st.session_state["user"]["logged_in"] = True
                st.session_state["user"]["username"] = username
                st.success("Successfully logged in!")
                st.rerun()
    else:
        st.success(f"Logged in as **{st.session_state['user']['username']}**")
        if st.button("Log Out"):
            st.session_state["user"]["logged_in"] = False
            st.rerun()

    st.divider()
    st.subheader("📦 Digital Voice Asset Inventory")
    st.info("Your AI Voice Models and custom recorded assets managed under your digital structure.")
    st.json({
        "Registered Entity": "Todiwala Ventures LTD - Digital Media Division",
        "AI Voice Assets": ["Homer_v1_Neural_Model", "Narrator_Tone_Commercial_v2"],
        "Storage & Card Hardware Sales": "Active - Independent Asset Pool"
    })

# ------------------------------------------
# TAB 3: CRM LEAD PIPELINE
# ------------------------------------------
with tab3:
    st.header("📊 CRM Opportunity Tracker")
    st.caption("Manage saved casting leads, track audition submissions, and record notes.")

    if not st.session_state["crm_leads"]:
        st.info("No saved leads in your pipeline yet. Go to 'Casting Intelligence' and click '➕ Save to CRM' on an opportunity.")
    else:
        for idx, lead in enumerate(st.session_state["crm_leads"]):
            with st.expander(f"📌 [{lead['status']}] {lead['title']}", expanded=True):
                l_col1, l_col2, l_col3 = st.columns([3, 2, 2])
                with l_col1:
                    st.write(f"**Source:** {lead['source']}")
                    st.write(f"**Link:** [Open Listing]({lead['link']})")
                with l_col2:
                    new_status = st.selectbox(
                        "Status", 
                        ["New Lead", "Audition Submitted", "Shortlisted", "Booked", "Pass"], 
                        index=["New Lead", "Audition Submitted", "Shortlisted", "Booked", "Pass"].index(lead["status"]),
                        key=f"status_{idx}"
                    )
                    st.session_state["crm_leads"][idx]["status"] = new_status
                with l_col3:
                    notes = st.text_area("Notes", value=lead["notes"], key=f"notes_{idx}", height=68)
                    st.session_state["crm_leads"][idx]["notes"] = notes

# ------------------------------------------
# TAB 4: PERFORMANCE ANALYTICS
# ------------------------------------------
with tab4:
    st.header("📈 Audition & Conversion Analytics")
    
    m1, m2, m3, m4 = st.columns(4)
    total_scraped = len(st.session_state["results"])
    total_saved = len(st.session_state["crm_leads"])
    total_submitted = sum(1 for lead in st.session_state["crm_leads"] if lead["status"] == "Audition Submitted")
    total_booked = sum(1 for lead in st.session_state["crm_leads"] if lead["status"] == "Booked")

    m1.metric("Live Opportunities Scraped", total_scraped)
    m2.metric("Saved CRM Leads", total_saved)
    m3.metric("Auditions Submitted", total_submitted)
    m4.metric("Jobs Booked", total_booked)

    st.divider()
    st.subheader("Scraper Source Breakdown")
    if st.session_state["results"]:
        source_counts = {}
        for item in st.session_state["results"]:
            source_counts[item["source"]] = source_counts.get(item["source"], 0) + 1
        st.bar_chart(source_counts)
    else:
        st.caption("Run the scraper in Tab 1 to populate analytics graphs.")

# ------------------------------------------
# TAB 5: GDPR & DATA COMPLIANCE
# ------------------------------------------
with tab5:
    st.header("🔒 GDPR & Privacy Settings")
    st.write("Manage user data collection policies, telemetry settings, and GDPR compliance logs.")

    st.session_state["gdpr_consent"] = st.toggle("Enable Data Processing Consent (GDPR Article 6)", value=st.session_state["gdpr_consent"])
    st.checkbox("Store Scraped Data Locally in Browser Session", value=True)
    st.checkbox("Allow Anonymous Scraper Performance Telemetry", value=False)

    st.divider()
    st.subheader("Data Deletion (Right to be Forgotten)")
    if st.button("🗑️ Wipe Session Data & Clear Cache", type="secondary"):
        st.session_state["results"] = []
        st.session_state["logs"] = []
        st.session_state["crm_leads"] = []
        st.session_state["has_run"] = False
        st.success("All personal session data and cached leads wiped successfully.")
        st.rerun()
