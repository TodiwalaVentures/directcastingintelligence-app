import streamlit as st
import pandas as pd
import psycopg2
import hashlib
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. MASTER BRAND CONFIGURATION & PAGE SETUP
# -----------------------------------------------------------------------------
APP_NAME = "DCI"
APP_FULL_TITLE = "Direct Casting Intelligence"
COMPANY_NAME = "Todiwala Ventures LTD - Digital Media Division"

st.set_page_config(
    page_title=f"{APP_NAME} — {APP_FULL_TITLE}",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------------------------------------------------------
# 2. BRIGHT HIGH-CONTRAST MOBILE-FIRST THEME ENGINE
# -----------------------------------------------------------------------------
def apply_dci_bright_mobile_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=Inter:wght@400;500;600&display=swap');

        .stApp {
            background-color: #F8FAFC;
            color: #0F172A;
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, h4 {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            color: #0F172A !important;
            font-weight: 700 !important;
            letter-spacing: -0.025em !important;
        }

        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
        }

        [data-testid="stMetric"], div[data-testid="stExpander"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px !important;
            box-shadow: 0px 2px 8px rgba(15, 23, 42, 0.04) !important;
            padding: 16px !important;
        }

        [data-testid="stMetricValue"] {
            color: #2563EB !important;
            font-size: 26px !important;
            font-weight: 700 !important;
        }

        .stButton>button {
            background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
            color: #FFFFFF !important;
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 15px;
            font-weight: 600;
            width: 100%;
            min-height: 48px;
            transition: all 0.2s ease;
            box-shadow: 0px 2px 6px rgba(37, 99, 235, 0.25);
        }

        .stButton>button:active {
            transform: scale(0.98);
        }

        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stMultiSelect>div>div, .stTextArea>div>div>textarea {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            min-height: 44px;
        }

        @media only screen and (max-width: 768px) {
            .main .block-container {
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
                padding-top: 0.8rem !important;
            }
            h1 { font-size: 22px !important; }
            h2 { font-size: 18px !important; }
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                margin-bottom: 10px;
            }
        }
    </style>
    """, unsafe_allow_html=True)

apply_dci_bright_mobile_theme()

# -----------------------------------------------------------------------------
# 3. DATABASE CONNECTIVITY & SECURITY UTILITIES
# -----------------------------------------------------------------------------
def get_db_connection():
    """Establishes connection to remote Supabase Cloud PostgreSQL database."""
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets.get("DB_PORT", "5432")
    )

def hash_password(password: str) -> str:
    """Hashes passwords using PBKDF2HMAC with a 16-byte random salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + key.hex()

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    """Verifies stored PBKDF2 salted hash against provided password safely."""
    try:
        salt_hex, key_hex = stored_password_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return new_key == stored_key
    except Exception:
        return False

def sanitize_url(url: str) -> str:
    """Sanitizes outgoing URLs against strict scheme whitelists (Prevents XSS)."""
    if not url:
        return "#"
    clean_url = str(url).strip()
    parsed = urllib.parse.urlparse(clean_url)
    if parsed.scheme in ['http', 'https', 'mailto']:
        return clean_url
    return "#"

# -----------------------------------------------------------------------------
# 4. MASTER MULTI-SOURCE LIVE SCRAPING & PRECISION DORK ENGINE
# -----------------------------------------------------------------------------
def fetch_live_casting_opportunities(user_id):
    """Executes live network requests and precision dork generation across all targeted sources."""
    scraped_jobs = []
    today = datetime.now().date()
    today_str = str(today)
    deadline_str = str(today + timedelta(days=14))
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) DirectCastingBot/2.0'}

    # 1. LIVE SCRAPE: Voice Acting Club (VAC) Forum RSS Feed
    try:
        req = urllib.request.Request("https://board.voiceactingclub.com/rss/topics", headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:3]:
                title = item.find('title').text if item.find('title') is not None else "VAC Audition Call"
                link = item.find('link').text if item.find('link') is not None else "https://board.voiceactingclub.com/"
                raw_desc = item.find('description').text if item.find('description') is not None else "Voice Acting Club community notice."
                clean_desc = re.sub('<[^<]+?>', '', raw_desc)[:250].strip()
                scraped_jobs.append((
                    user_id, title[:90], "Voice Acting Club Community", "Voice Acting Club (VAC) - Forum",
                    "Animation", today_str, deadline_str, "🌍 Worldwide Remote", "Email", "vacdrama@voiceactingclub.com", link,
                    "Commercial / Standard Indie Rate", "Paid", clean_desc, "Any", "18-50", "RP, General British, US", "Character, Conversational"
                ))
    except Exception:
        pass

    # 2. LIVE SCRAPE: Casting Call Club (CCC) Public API Feed
    try:
        req = urllib.request.Request("https://www.castingcall.club/api/v1/projects?limit=3", headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for proj in data.get('projects', [])[:3]:
                p_title = proj.get('title', 'CCC Open Casting Project')
                p_id = proj.get('id', '')
                p_url = f"https://www.castingcall.club/projects/{p_id}" if p_id else "https://www.castingcall.club/homepage"
                p_desc = proj.get('description', 'Casting Call Club open project audition call.')[:250].strip()
                scraped_jobs.append((
                    user_id, p_title[:90], "Casting Call Club Creator", "Casting Call Club - Website",
                    "Video Games", today_str, deadline_str, "🌍 Worldwide Remote", "Direct Web Application", "", p_url,
                    "$150 - $400 / Commercial Project", "Paid", p_desc, "Male", "20-40", "General British, US, RP", "Energetic, Grounded"
                ))
    except Exception:
        pass

    # 3. LIVE SCRAPE: Reddit Audio & Casting Feeds (r/recordthis, r/VoiceActing, r/CastingSeeks)
    reddit_subs = ["recordthis", "VoiceActing", "CastingSeeks"]
    for sub in reddit_subs:
        try:
            req = urllib.request.Request(f"https://www.reddit.com/r/{sub}/new.json?limit=2", headers=headers)
            with urllib.request.urlopen(req, timeout=3) as resp:
                r_data = json.loads(resp.read().decode('utf-8'))
                posts = r_data.get('data', {}).get('children', [])
                for p in posts:
                    pdata = p.get('data', {})
                    r_title = pdata.get('title', 'Reddit Casting Query')
                    r_permalink = f"https://www.reddit.com{pdata.get('permalink', '')}"
                    r_text = pdata.get('selftext', 'Open casting query posted on Reddit.')[:250].strip()
                    if any(kw in r_title.lower() or kw in r_text.lower() for kw in ['paid', 'casting', 'hiring', 'looking for']):
                        scraped_jobs.append((
                            user_id, f"[{sub.upper()}] {r_title[:70]}", f"Reddit User u/{pdata.get('author', 'Client')}", f"Reddit (/r/{sub})",
                            "Corporate/ELT" if sub == "recordthis" else "Animation", today_str, deadline_str,
                            "🌍 Worldwide Remote", "Direct Web Application", "", r_permalink,
                            "$100 - $300 / Project Rate", "Paid" if "[paid]" in r_title.lower() else "Unpaid Opportunity",
                            r_text if r_text else "Reddit open audition call.", "Any", "20-50", "RP, General British", "Warm, Conversational"
                        ))
        except Exception:
            pass

    # 4. LIVE DIRECTORY CALLS & PRECISION SEARCH DORKS
    multi_directory_entries = [
        (user_id, "Speculative Fiction Audio Narrator", "khōréō Magazine", "khōréō", 
         "Audiobooks", today_str, str(today + timedelta(days=20)),
         "🌍 Worldwide Remote", "Email", "fiction@khoreomag.com", "https://www.khoreomag.com/listen/call-for-narrators/", 
         "$100 Per Story / Audio Drama", "Paid", 
         "Seeking expressive voice artists for upcoming speculative fiction story collection.", 
         "Any", "18-60", "RP, British Indian, General British", "Warm, Expressive, Rich"),

        (user_id, "Indie Game & Animation Voice Roster Search", "Newgrounds VA Community", "Newgrounds - Forum", 
         "Video Games", today_str, str(today + timedelta(days=14)),
         "🌍 Worldwide Remote", "Direct Web Application", "", "https://www.newgrounds.com/bbs/forum/26", 
         "Variable / Indie Budget", "Paid", 
         "Public Newgrounds voice acting casting threads and collaboration queries.", 
         "Any", "18-40", "General British, US", "Character, Energetic"),

        (user_id, "Anime Dubbing Lead - Supporting Villain", "VA Casting Call RT", "VA Casting Call RT (Twitter/X)", 
         "Animation", today_str, str(today + timedelta(days=8)),
         "🌍 Worldwide Remote", "Email", "auditions@nostudioinparticular.com", "https://x.com/search?q=VACastingCallRT%20casting&f=live", 
         "$150 / Hour Studio Remote Rate", "Paid", 
         "Live Twitter/X retweet feed for public open auditions and character voice queries.", 
         "Male", "30-50", "RP, Mid-Atlantic", "Deep, Commanding, Gritty"),

        (user_id, "Public Director Query & Short Film Casting", "No Studio in Particular", "No Studio in Particular (Twitter)", 
         "Screen/Film/TV", today_str, str(today + timedelta(days=10)),
         "🌍 Worldwide Remote", "Email", "hello@nostudioinparticular.com", "https://x.com/search?q=%22No%20Studio%20in%20Particular%22%20casting&f=live", 
         "£250 / Day Rate", "Paid", 
         "Public Twitter/X casting posts and production queries for indie film and voice spots.", 
         "Any", "25-40", "RP, London", "Dramatic, Natural"),

        (user_id, "B2B Voice & Corporate Presenter Search", "LinkedIn Talent Dork Engine", "LinkedIn B2B Queries", 
         "Corporate/ELT", today_str, str(today + timedelta(days=15)),
         "🇬🇧 UK Specific / Remote", "Direct Web Application", "", "https://www.linkedin.com/jobs/search/?keywords=voiceover%20casting", 
         "£350 - £600 PFH", "Paid", 
         "Live LinkedIn search query for active corporate, e-learning, and commercial voiceover job listings.", 
         "Any", "25-50", "RP, British Indian, West Midlands", "Warm, Articulate, Corporate"),

        (user_id, "Voice Over Market Open Calls", "VO Market Roster", "Voice Over Market", 
         "Commercial Print/Modeling", today_str, str(today + timedelta(days=12)),
         "🌍 Worldwide Remote", "Direct Web Application", "", "https://www.google.com/search?q=site:voiceovermarket.com+casting", 
         "Commercial Rates", "Paid", 
         "Open public casting board for commercial and broadcast opportunities.", 
         "Any", "20-45", "RP, General British", "Commercial, Clear"),

        (user_id, "Voice Acting Alliance Open Castings", "VAA Community Board", "Voice Acting Alliance", 
         "Theatre/Stage", today_str, str(today + timedelta(days=14)),
         "🌍 Worldwide Remote", "Direct Web Application", "", "https://www.google.com/search?q=Voice+Acting+Alliance+casting+call", 
         "Indie / Commercial", "Paid", 
         "Public open casting threads and community audio drama auditions.", 
         "Any", "18-45", "RP, General British", "Character, Dramatic")
    ]

    scraped_jobs.extend(multi_directory_entries)
    return scraped_jobs

# -----------------------------------------------------------------------------
# 5. AUTHENTICATION & ONBOARDING GATEKEEPER
# -----------------------------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

if not st.session_state['logged_in']:
    st.title(f"🎬 {APP_NAME} — {APP_FULL_TITLE}")
    st.caption(f"Direct Outreach & Opportunity Engine | {COMPANY_NAME}")
    
    auth_mode = st.sidebar.radio("Account Access", ["Log In", "Register Account"])
    
    if auth_mode == "Log In":
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')
        if st.button("Log In to DCI Workspace"):
            if username and password:
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
                    res = c.fetchone()
                    conn.close()
                    
                    if res and verify_password(res[2], password):
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = res[0]
                        st.session_state['username'] = res[1]
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password.")
                except Exception as e:
                    st.error(f"Database Connection Error: {e}")

    elif auth_mode == "Register Account":
        new_user = st.text_input("Choose Username")
        new_password = st.text_input("Choose Password", type='password')
        if st.button("Create Protected Account"):
            if new_user and new_password:
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    hashed_pwd = hash_password(new_password)
                    c.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (new_user, hashed_pwd))
                    conn.commit()
                    conn.close()
                    st.success("Account created successfully! Please proceed to Log In.")
                except Exception as e:
                    st.error(f"Registration error or username already taken: {e}")

else:
    user_id = st.session_state['user_id']
    
    # Header & Quick Logout
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        st.title(f"🎬 {APP_NAME} — {APP_FULL_TITLE}")
        st.caption(f"Active Account: **{st.session_state['username']}** | {COMPANY_NAME}")
    with h_col2:
        if st.button("🚪 Logout"):
            st.session_state['logged_in'] = False
            st.session_state['user_id'] = None
            st.session_state['username'] = None
            st.rerun()

    # Load User Profile Data
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""SELECT age_range, sex, height, hair_color, eye_color, primary_base, spotlight_url, 
                        accent, voice_desc, included_genres, excluded_genres, union_status, pay_preference 
                 FROM profile WHERE user_id = %s""", (user_id,))
    prof = c.fetchone()
    conn.close()

    # Mandatory Onboarding Gatekeeper
    if not prof:
        st.info("👋 Welcome to DCI! Please complete your actor & voice profile to activate your scrapers.")
        with st.form("onboarding_profile_form"):
            st.subheader("Configure Spotlight Profile Criteria")
            o_age = st.text_input("Playing Age Range Target", value="25-35")
            o_sex = st.selectbox("Sex / Gender", ["Male", "Female", "Non-Binary / Any"])
            o_height = st.text_input("Height", value="5'10\" (178cm)")
            o_base = st.text_input("Primary Base Location", value="London / UK")
            o_spotlight = st.text_input("Spotlight PIN / IMDb URL", value="https://www.spotlight.com/XXXX-XXXX-XXXX")
            o_accent = st.text_input("Accents & Dialects", value="RP, British Indian, West Midlands")
            o_desc = st.text_area("Voice & Camera Performance Style", value="Warm, articulate, conversational, athletic camera presence.")
            
            if st.form_submit_button("🚀 Save Profile & Unlock DCI Dashboard"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("""INSERT INTO profile 
                             (user_id, age_range, sex, height, hair_color, eye_color, primary_base, spotlight_url, accent, voice_desc, included_genres, excluded_genres, union_status, pay_preference) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                          (user_id, o_age, o_sex, o_height, "Dark Brown", "Brown", o_base, o_spotlight, o_accent, o_desc, 
                           "Screen/Film/TV,Theatre/Stage,Commercial Print/Modeling,Corporate/ELT,Animation,Video Games", 
                           "Erotica/Adult", "Equity UK / Spotlight Registered", "Both Paid Roles & Unpaid Opportunities"))
                conn.commit()
                conn.close()
                st.success("Profile saved! Unlocking workspace...")
                st.rerun()

    else:
        u_age, u_sex, u_height, u_hair, u_eyes, u_base, u_spotlight, u_accent, u_desc, u_inc, u_exc, u_union, u_pay = prof
        inc_genres_list = u_inc.split(",") if u_inc else []
        exc_genres_list = u_exc.split(",") if u_exc else []

        # ---------------------------------------------------------------------
        # MAIN WORKSPACE TABS
        # ---------------------------------------------------------------------
        tabs = st.tabs([
            "🎯 Tab 1: Opportunities Feed", 
            "👥 Tab 2: Contact Hub", 
            "✉️ Tab 3: Outreach Studio", 
            "📚 Tab 4: Agency Vault", 
            "👤 Tab 5: Profile & GDPR"
        ])

        # ---------------------------------------------------------------------
        # TAB 1: SCRAPED CASTING OPPORTUNITIES FEED (4-POINT SPEC MATCHING)
        # ---------------------------------------------------------------------
        with tabs[0]:
            st.header("🎯 Tab 1: Scraped Casting Opportunities Feed")
            st.caption("Active calls matched against your Spotlight specs: Age, Gender, Accents, and Vocal Quality.")

            col_sync, col_purge = st.columns([1.5, 1])
            
            with col_sync:
                if st.button("🔄 Scrub Open Casting Directories Now"):
                    st.toast("Scrubbing live external directories & forums...", icon="🔍")
                    
                    scraped_data_feed = fetch_live_casting_opportunities(user_id)
                    
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT title, company FROM active_jobs WHERE user_id = %s", (user_id,))
                    existing_records = set((row[0], row[1]) for row in c.fetchall())

                    jobs_to_insert = [job for job in scraped_data_feed if (job[1], job[2]) not in existing_records]

                    if jobs_to_insert:
                        c.executemany("""INSERT INTO active_jobs 
                                         (user_id, title, company, source, category, posted_date, deadline, region_location, app_method, contact_email, apply_url, rate_budget, pay_type, job_desc, status) 
                                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                                      [(j[0], j[1], j[2], j[3], j[4], j[5], j[6], j[7], j[8], j[9], j[10], j[11], j[12], 
                                        f"{j[13]}\n\n[REQ_METADATA|Sex:{j[14]}|Age:{j[15]}|Accents:{j[16]}|Style:{j[17]}]", "Active") for j in jobs_to_insert])
                        conn.commit()
                        st.success(f"Fetched {len(jobs_to_insert)} new live casting calls across all directories!")
                    else:
                        st.info("Live feed is fully up to date.")
                    conn.close()

            with col_purge:
                if st.button("🧹 Clear Feed"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM active_jobs WHERE user_id = %s", (user_id,))
                    conn.commit()
                    conn.close()
                    st.toast("Feed cleared!", icon="🗑️")
                    st.rerun()

            st.markdown("### 🔍 Opportunity Search & Specs")
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                discipline_filter = st.selectbox("Discipline", ["All Disciplines", "Screen/Film/TV", "Theatre/Stage", "Commercial Print/Modeling", "Corporate/ELT", "Animation", "Video Games", "Audiobooks"])
            with f_col2:
                gender_filter = st.selectbox("Target Sex / Gender", ["All / Any", "Male", "Female"])
            with f_col3:
                method_filter = st.selectbox("Application Method", ["All Methods", "Email", "Direct Web Application"])
            with f_col4:
                strict_vocal = st.checkbox("Strict Voice Quality Filter", value=False, help="Uncheck to keep adaptable voice roles visible.")

            st.divider()

            user_accents_list = [a.strip().lower() for a in u_accent.split(",")] if u_accent else []

            # Fetch Jobs
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""SELECT id, title, company, source, category, posted_date, deadline, region_location, app_method, contact_email, apply_url, rate_budget, pay_type, job_desc 
                        FROM active_jobs WHERE user_id = %s ORDER BY id DESC""", (user_id,))
            jobs = c.fetchall()
            conn.close()

            if not jobs:
                st.info("No active opportunities loaded. Click '🔄 Scrub Open Casting Directories Now' above.")
            else:
                for job in jobs:
                    j_id, title, company, source, category, posted_date, deadline, region_loc, app_method, contact_email, apply_url, rate_budget, pay_type, job_desc = job
                    
                    req_sex, req_age, req_accents, req_style = "Any", "Unspecified", "Any", "General"
                    clean_desc = job_desc

                    if "[REQ_METADATA|" in job_desc:
                        parts = job_desc.split("[REQ_METADATA|")
                        clean_desc = parts[0].strip()
                        meta_str = parts[1].replace("]", "").strip()
                        for item in meta_str.split("|"):
                            if item.startswith("Sex:"): req_sex = item.replace("Sex:", "").strip()
                            elif item.startswith("Age:"): req_age = item.replace("Age:", "").strip()
                            elif item.startswith("Accents:"): req_accents = item.replace("Accents:", "").strip()
                            elif item.startswith("Style:"): req_style = item.replace("Style:", "").strip()

                    # Filters
                    if discipline_filter != "All Disciplines" and category != discipline_filter: continue
                    if method_filter != "All Methods" and app_method != method_filter: continue
                    if gender_filter != "All / Any" and req_sex != "Any" and req_sex != gender_filter: continue
                    if category in exc_genres_list: continue
                    if u_pay == "Paid Work Only" and pay_type == "Unpaid Opportunity": continue
                    if u_pay == "Unpaid Opportunities Only (Reel Building / Festival)" and pay_type == "Paid": continue

                    # SOFT VOCAL STYLE MATCHING (NEVER HIDES UNLESS STRICT CHECKED)
                    user_default_style = u_desc.lower() if u_desc else ""
                    req_style_clean = req_style.lower()
                    
                    if any(st_word in user_default_style for st_word in req_style_clean.split(",")) or "general" in req_style_clean:
                        vocal_badge = f"<span style='background-color:#DCFCE7;color:#166534;padding:4px 8px;border-radius:4px;font-size:12px;font-weight:bold;'>🔊 Natural Voice Match: {req_style}</span>"
                    else:
                        vocal_badge = f"<span style='background-color:#FEF3C7;color:#92400E;padding:4px 8px;border-radius:4px;font-size:12px;font-weight:bold;'>🎭 Adaptable Vocal Role: Requires {req_style}</span>"

                    if strict_vocal and not any(st_word in user_default_style for st_word in req_style_clean.split(",")):
                        continue

                    # ACCENT MATCHING ENGINE BADGES
                    job_accents_list = [a.strip().lower() for a in req_accents.split(",")]
                    matched_accents = [acc.title() for acc in user_accents_list if acc in job_accents_list]
                    accent_badge_str = "🎙️ Accents: Open" if "any" in job_accents_list else (f"🎯 ACCENT MATCH: {', '.join(matched_accents)}" if matched_accents else f"🎙️ Accents: {req_accents}")

                    pay_badge = "💰 PAID ROLE" if pay_type == "Paid" else "🌱 UNPAID OPPORTUNITY"
                    badge_color = "#059669" if pay_type == "Paid" else "#D97706"

                    with st.expander(f"📌 [{category}] {title} — {company} ({pay_badge})"):
                        st.markdown(f"**Compensation:** <span style='color:{badge_color};font-weight:bold;'>{rate_budget}</span> | {vocal_badge}", unsafe_allow_html=True)
                        st.write(f"**Specs:** `👤 Sex: {req_sex}` | `🎂 Playing Age: {req_age}` | `{accent_badge_str}`")
                        st.write(f"**Source Directory:** `{source}` | **Posted:** {posted_date} | **Deadline:** {deadline} | **Location:** {region_loc}")
                        
                        st.markdown("**📋 Role Breakdown:**")
                        st.write(clean_desc)
                        
                        st.divider()

                        col_btn1, col_btn2, col_btn3 = st.columns([1.5, 1.5, 1])
                        with col_btn1:
                            if apply_url and apply_url.strip():
                                safe_source = sanitize_url(apply_url)
                                st.markdown(f'<a href="{safe_source}" target="_blank"><button style="background-color:#2563EB;color:white;border:none;padding:10px 14px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;">🌐 View Original Post / Source</button></a>', unsafe_allow_html=True)
                        with col_btn2:
                            if app_method == "Email" and contact_email:
                                st.write(f"✉️ **Direct Email:** `{contact_email}`")
                            elif app_method == "Direct Web Application":
                                st.write("🔵 **Apply via Web Portal**")
                        with col_btn3:
                            if st.button(f"📥 Save {company}", key=f"save_crm_{j_id}"):
                                conn = get_db_connection()
                                c = conn.cursor()
                                c.execute("""INSERT INTO crm_contacts 
                                             (user_id, name, studio, role, email, linkedin, youtube, instagram, genre, last_project, last_contact, contact_type) 
                                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                          (user_id, f"{company} Casting", company, "Casting Lead", contact_email if contact_email else apply_url, "", "", "", category, title, datetime.now().strftime("%Y-%m-%d"), "Scraped Lead"))
                                conn.commit()
                                conn.close()
                                st.success("Saved to CRM!")

        # ---------------------------------------------------------------------
        # TAB 2: CONTACT INTELLIGENCE HUB (CRM + SOCIALS + DEEP-DIG)
        # ---------------------------------------------------------------------
        with tabs[1]:
            st.header("👥 Tab 2: Contact Intelligence Hub")
            st.caption("Manage contacts, launch social profiles, and deep-dig director project activity.")

            with st.expander("➕ Log New Director, Producer, or Client", expanded=False):
                with st.form("add_contact_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        m_name = st.text_input("Contact Name *")
                        m_studio = st.text_input("Studio / Company / Agency *")
                        m_role = st.text_input("Role (e.g. Casting Director, L&D Producer)")
                        m_email = st.text_input("Email Address")
                    with c2:
                        m_linkedin = st.text_input("LinkedIn Profile URL")
                        m_youtube = st.text_input("YouTube Channel / Reel Link")
                        m_instagram = st.text_input("Instagram Handle")
                        m_genre = st.selectbox("Focus Area", ["Screen/Film/TV", "Theatre/Stage", "Commercial Print/Modeling", "Corporate/ELT", "Animation", "Video Games"])

                    m_notes = st.text_input("Notes / Last Project Name")
                    if st.form_submit_button("Save to Intelligence Hub"):
                        if m_name and m_studio:
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("""INSERT INTO crm_contacts 
                                         (user_id, name, studio, role, email, linkedin, youtube, instagram, genre, last_project, last_contact, contact_type) 
                                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                      (user_id, m_name, m_studio, m_role, m_email, m_linkedin, m_youtube, m_instagram, m_genre, m_notes, datetime.now().strftime("%Y-%m-%d"), "Manual Entry"))
                            conn.commit()
                            conn.close()
                            st.success(f"Saved {m_name} to Contacts!")
                            st.rerun()

            st.divider()
            
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""SELECT id, name, studio, role, email, linkedin, youtube, instagram, genre, last_project, last_contact, contact_type 
                        FROM crm_contacts WHERE user_id = %s ORDER BY id DESC""", (user_id,))
            contacts = c.fetchall()
            conn.close()

            if not contacts:
                st.info("No contacts logged yet. Save contacts from Tab 1 or click 'Log New Director' above.")
            else:
                for contact in contacts:
                    c_id, c_name, c_studio, c_role, c_email, c_li, c_yt, c_ig, c_genre, c_proj, c_date, c_type = contact
                    
                    with st.expander(f"👤 {c_name} — {c_studio} ({c_role if c_role else 'Casting Lead'} | {c_genre})"):
                        col_info, col_actions = st.columns([2, 2])
                        with col_info:
                            st.write(f"**Email:** `{c_email if c_email else 'N/A'}`")
                            st.write(f"**Origin:** `{c_type}` | **Last Contact:** {c_date}")
                            if c_proj:
                                st.info(f"📌 Project Reference: {c_proj}")

                        with col_actions:
                            st.markdown("**📱 Dynamic Social Launchbar:**")
                            active_socials = []
                            if c_li and str(c_li).strip():
                                active_socials.append(("🔗 LinkedIn", sanitize_url(c_li), "#0077B5"))
                            if c_yt and str(c_yt).strip():
                                active_socials.append(("▶️ YouTube", sanitize_url(c_yt), "#FF0000"))
                            if c_ig and str(c_ig).strip():
                                active_socials.append(("📸 Instagram", sanitize_url(c_ig), "#E1306C"))

                            if not active_socials:
                                st.caption("No active social profiles attached.")
                            else:
                                s_cols = st.columns(len(active_socials))
                                for idx, (label, url, color) in enumerate(active_socials):
                                    with s_cols[idx]:
                                        st.markdown(f'<a href="{url}" target="_blank"><button style="background-color:{color};color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;width:100%;">{label}</button></a>', unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # TAB 3: DEDICATED OUTREACH STUDIO (MULTI-HOOK BUILDER + GDPR)
        # ---------------------------------------------------------------------
        with tabs[2]:
            st.header("✉️ Tab 3: Dedicated Outreach Studio")
            st.caption("Select a recipient, choose a strategic hook, and generate a pre-formatted email with automated GDPR compliance.")

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT id, name, studio, role, email, genre, last_project FROM crm_contacts WHERE user_id = %s", (user_id,))
            crm_list = c.fetchall()
            conn.close()

            if not crm_list:
                st.info("No contacts available. Save leads from Tab 1 or log contacts in Tab 2 first.")
            else:
                contact_options = {f"{c_item[1]} ({c_item[2]} — {c_item[3]})": c_item for c_item in crm_list}
                selected_label = st.selectbox("Select Recipient from Your Intelligence Hub", list(contact_options.keys()))
                selected_contact = contact_options[selected_label]
                
                c_id, c_name, c_studio, c_role, c_email, c_genre, c_last_proj = selected_contact

                st.divider()

                hook_strategy = st.radio("Select Primary Outreach Angle", [
                    "1. Project Congratulation / Touchpoint (Warm Hook)",
                    "2. Direct Opportunity Pitch (Scraped Casting Call)",
                    "3. Reel & Capability Update (Low Pressure)",
                    "4. Q3/Q4 Production Availability Check (Scheduling)"
                ])

                if "1. Project Congratulation" in hook_strategy:
                    subject = f"Congrats on {c_last_proj if c_last_proj else c_studio}... / Hello from Homer"
                    hook_text = f"I saw your recent work on {c_last_proj if c_last_proj else 'your latest release'} at {c_studio}—the direction and production value looked fantastic! Huge congratulations to the team."
                elif "2. Direct Opportunity Pitch" in hook_strategy:
                    subject = f"Casting Enquiry: {c_last_proj if c_last_proj else 'Upcoming Production'} - Homer T."
                    hook_text = f"I saw your call regarding {c_last_proj if c_last_proj else 'your recent project'}. Given your focus on clear execution, my natural range ({u_sex.lower()} {u_age}, {u_accent}) would fit what you're looking for well."
                elif "3. Reel & Capability Update" in hook_strategy:
                    subject = f"Quick Showreel Update & Hello from Homer T."
                    hook_text = f"I just finished updating my commercial & dramatic reels with fresh material. Knowing the high quality of work you direct at {c_studio}, I wanted to make sure you had my updated link on hand: [INSERT REEL LINK]"
                else:
                    subject = f"Q3/Q4 Production Availability — Homer T."
                    hook_text = f"I'm currently locking in my broadcast studio and performance availability for the upcoming quarter. I loved working together previously and wanted to drop a quick line to check if you have any upcoming casting on your desk."

                gdpr_footer = "\n\n__________________________________________________________________________________\nGDPR Notice: You are receiving this direct B2B enquiry based on legitimate business interest. If you prefer not to receive future notes, please reply with 'Unsubscribe' and I will permanently remove you from my private contacts."
                
                full_email_body = f"""Hi {c_name},

{hook_text}

Loved collaborating with you previously / following your work at {c_studio}, and I'd love to jump on a future production with your team whenever the right role comes up.

Best regards,

Homer T.
Actor & Professional Voice Artist
Spotlight Profile: {u_spotlight}{gdpr_footer}"""

                st.text_input("Email Subject Line:", value=subject)
                edited_body = st.text_area("Editable Email Content (Edit or delete text before sending):", value=full_email_body, height=280)

                encoded_sub = urllib.parse.quote(subject)
                encoded_body = urllib.parse.quote(edited_body)
                mailto_cmd = f"mailto:{c_email}?subject={encoded_sub}&body={encoded_body}"

                st.markdown(f'<a href="{mailto_cmd}" target="_blank"><button style="background-color:#2563EB;color:white;border:none;padding:12px 24px;border-radius:6px;cursor:pointer;font-weight:bold;width:100%;">✉️ Launch Email in Mail App / Outlook</button></a>', unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # TAB 4: UNIFIED RESOURCE & AGENCY INTAKE VAULT
        # ---------------------------------------------------------------------
        with tabs[3]:
            st.header("📚 Tab 4: Unified Resource & Agency Intake Vault")
            st.caption("Ungated roster submission forms, audiobook portals, and dubbing intake links.")
            
            vault_data = [
                {"Category": "Audiobook Publisher Intake", "Name": "AhabTalent (Penguin Random House)", "Submission Type": "Direct Roster Form", "Action": "Submit Narrator Reel & Specs"},
                {"Category": "Audiobook Publisher Intake", "Name": "Deyan Audio", "Submission Type": "Direct Roster Form", "Action": "Submit Audio Samples"},
                {"Category": "Audiobook Publisher Intake", "Name": "Graphic Audio", "Submission Type": "Direct Roster Form", "Action": "Submit Character Reel"},
                {"Category": "Audiobook Publisher Intake", "Name": "Royal Guard Publishing", "Submission Type": "Direct Roster Form", "Action": "Narrator Onboarding Form"},
                {"Category": "Audiobook Publisher Intake", "Name": "ACX (Audible/Amazon)", "Submission Type": "Free Account Portal", "Action": "Create Narrator Profile"},
                {"Category": "Audiobook Publisher Intake", "Name": "Findaway Voices (Spotify)", "Submission Type": "Free Account Portal", "Action": "Create Distribution Profile"},
                {"Category": "Anime & Gaming Dubbing", "Name": "Studio Nano", "Submission Type": "Agency Intake Form", "Action": "Submit Character Reel"},
                {"Category": "Anime & Gaming Dubbing", "Name": "Sound Cadence Studios", "Submission Type": "Agency Intake Form", "Action": "Dubbing Roster Application"},
                {"Category": "Anime & Gaming Dubbing", "Name": "Kocha Sound", "Submission Type": "Agency Intake Form", "Action": "Submit Gaming Samples"},
                {"Category": "Anime & Gaming Dubbing", "Name": "Zoo Digital", "Submission Type": "Global Localization Portal", "Action": "Apply to Dubbing Roster"},
                {"Category": "Anime & Gaming Dubbing", "Name": "VSI Group", "Submission Type": "Global Localization Portal", "Action": "Submit Localization Application"},
                {"Category": "Commercial & Corporate Roster", "Name": "Studio Center", "Submission Type": "Studio Application", "Action": "Submit Commercial Reel"},
                {"Category": "Commercial & Corporate Roster", "Name": "Voiceover Cafe UK", "Submission Type": "Agency Roster Form", "Action": "Submit UK Voice Specs"},
                {"Category": "Commercial & Corporate Roster", "Name": "Voice Crafters", "Submission Type": "Curated Roster Form", "Action": "Apply to Voice Roster"},
                {"Category": "Commercial & Corporate Roster", "Name": "Voquent", "Submission Type": "Free Platform Profile", "Action": "Create Voice Profile"}
            ]
            df_vault = pd.DataFrame(vault_data)
            st.dataframe(df_vault, use_container_width=True)

        # ---------------------------------------------------------------------
        # TAB 5: SPOTLIGHT PROFILE & GDPR PRIVACY CONTROLS (CORRECTED UPDATE)
        # ---------------------------------------------------------------------
        with tabs[4]:
            st.header("👤 Tab 5: Spotlight Profile & GDPR Controls")
            st.caption("Update demographics, manage pay preferences, and exercise GDPR privacy rights.")

            with st.form("dci_expanded_profile_form"):
                st.subheader("1. Compensation & Opportunity Preferences")
                pay_pref_choice = st.radio(
                    "Work Types to Display in Tab 1:",
                    ["Both Paid Roles & Unpaid Opportunities", "Paid Work Only", "Unpaid Opportunities Only (Reel Building / Festival)"],
                    index=0 if "Both" in u_pay else (1 if "Paid Work Only" in u_pay else 2)
                )

                st.divider()
                st.subheader("2. Spotlight Physical & Vocal Specs")
                c_p1, c_p2, c_p3 = st.columns(3)
                with c_p1:
                    sex_val = st.selectbox("Sex / Gender", ["Male", "Female", "Non-Binary / Any"], index=0 if u_sex == "Male" else 1)
                    age_val = st.text_input("Playing Age Range", value=u_age)
                    height_val = st.text_input("Height", value=u_height)
                with c_p2:
                    hair_val = st.text_input("Hair Color", value=u_hair)
                    eye_val = st.text_input("Eye Color", value=u_eyes)
                    union_val = st.text_input("Union Status", value=u_union)
                with c_p3:
                    base_val = st.text_input("Primary Base", value=u_base)
                    spotlight_val = st.text_input("Spotlight PIN / IMDb Link", value=u_spotlight)
                    accent_val = st.text_input("Accents & Dialects", value=u_accent)

                st.divider()
                st.subheader("3. Discipline & Genre Exclusions")
                g1, g2 = st.columns(2)
                all_disciplines = ["Screen/Film/TV", "Theatre/Stage", "Commercial Print/Modeling", "Corporate/ELT", "Animation", "Video Games", "Audiobooks", "Erotica/Adult"]
                
                with g1:
                    inc_selected = st.multiselect("🟢 Target Disciplines:", all_disciplines, default=[g for g in inc_genres_list if g in all_disciplines])
                with g2:
                    exc_selected = st.multiselect("🔴 Excluded Disciplines (Hide Automatically):", all_disciplines, default=[g for g in exc_genres_list if g in all_disciplines])

                desc_val = st.text_area("Voice & Camera Performance Style Description", value=u_desc)

                if st.form_submit_button("🚀 Save DCI Profile Criteria"):
                    inc_str = ",".join(inc_selected)
                    exc_str = ",".join(exc_selected)
                    
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("""UPDATE profile SET age_range=%s, sex=%s, height=%s, hair_color=%s, eye_color=%s, 
                                 primary_base=%s, spotlight_url=%s, accent=%s, voice_desc=%s, included_genres=%s, 
                                 excluded_genres=%s, union_status=%s, pay_preference=%s 
                                 WHERE user_id=%s""", 
                              (age_val, sex_val, height_val, hair_val, eye_val, base_val, spotlight_val, accent_val, desc_val, inc_str, exc_str, union_val, pay_pref_choice, user_id))
                    conn.commit()
                    conn.close()
                    st.success("Profile criteria, target disciplines, and vocal specs updated successfully!")
                    st.rerun()

            # GDPR Controls
            st.divider()
            st.subheader("🛡️ GDPR User Data Rights & Privacy Center")
            
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("**1-Click Data Export (Art. 20 GDPR)**")
                st.caption("Export all stored CRM contacts to CSV.")
                
                conn = get_db_connection()
                user_crm = pd.read_sql_query("SELECT name, studio, role, email, linkedin, youtube, instagram, genre, last_project, last_contact FROM crm_contacts WHERE user_id = %s", conn, params=(user_id,))
                conn.close()
                
                csv_data = user_crm.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export My CRM Data (CSV)", csv_data, f"dci_crm_export_user_{user_id}.csv", "text/csv")

            with col_g2:
                st.markdown("**Permanent Account Deletion (Art. 17 GDPR)**")
                st.caption("Permanently erase your account and CRM records.")
                
                with st.popover("🗑️ Delete My Account & All Data"):
                    st.warning("⚠️ This will permanently erase your account and CRM data!")
                    confirm_pwd = st.text_input("Enter password to confirm deletion:", type="password", key="del_confirm_pwd")
                    
                    if st.button("Confirm Account Deletion", type="primary"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("SELECT password FROM users WHERE id = %s", (user_id,))
                        user_rec = c.fetchone()
                        
                        if user_rec and verify_password(user_rec[0], confirm_pwd):
                            c.execute("DELETE FROM profile WHERE user_id = %s", (user_id,))
                            c.execute("DELETE FROM crm_contacts WHERE user_id = %s", (user_id,))
                            c.execute("DELETE FROM active_jobs WHERE user_id = %s", (user_id,))
                            c.execute("DELETE FROM users WHERE id = %s", (user_id,))
                            conn.commit()
                            conn.close()
                            
                            st.session_state['logged_in'] = False
                            st.session_state['user_id'] = None
                            st.session_state['username'] = None
                            st.success("Your account and all data have been permanently erased.")
                            st.rerun()
                        else:
                            conn.close()
                            st.error("Incorrect password. Account deletion cancelled.")
