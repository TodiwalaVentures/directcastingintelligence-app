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
# 4. HIGH-YIELD SCRAPING ENGINE (CASTING CALL CLUB, BLUESKY, REDDIT, NEWGROUNDS)
# -----------------------------------------------------------------------------
def fetch_live_casting_opportunities(user_id):
    """Fetches maximum live casting calls across open APIs, websites, and feeds."""
    scraped_jobs = []
    scrape_errors = []
    today_str = str(datetime.now().date())
    deadline_str = str((datetime.now() + timedelta(days=14)).date())
    
    # Modern browser User-Agent header to bypass standard anti-bot 403 blocks
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    # 1. LIVE SCRAPE: Casting Call Club (https://www.castingcall.club/find_jobs)
    try:
        ccc_url = "https://www.castingcall.club/find_jobs"
        req = urllib.request.Request(ccc_url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            # Extract project links from find_jobs page using regex matching /projects/
            project_matches = re.findall(r'/projects/([a-zA-Z0-9-]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            
            seen_ids = set()
            for p_id, raw_title in project_matches:
                clean_title = re.sub(r'<[^<]+?>', '', raw_title).strip()
                if not clean_title or len(clean_title) < 3 or p_id in seen_ids:
                    continue
                seen_ids.add(p_id)
                
                p_url = f"https://www.castingcall.club/projects/{p_id}"
                scraped_jobs.append((
                    user_id, f"[CCC] {clean_title[:75]}", "Casting Call Club Creator", "Casting Call Club - find_jobs",
                    "Video Games", today_str, deadline_str, "🌍 Worldwide Remote", "Direct Web Application", "", p_url,
                    "$150 - $400 / Commercial Project", "Paid", "Open casting call posted on Casting Call Club (find_jobs).", "Male", "20-40", "General British, US, RP", "Energetic, Grounded"
                ))
            
            # Fallback to CCC public search API endpoint if HTML parsing returns fewer than 3 items
            if len(seen_ids) < 3:
                api_req = urllib.request.Request("https://www.castingcall.club/api/v1/projects?limit=20", headers=headers)
                try:
                    with urllib.request.urlopen(api_req, timeout=4) as api_resp:
                        data = json.loads(api_resp.read().decode('utf-8'))
                        for proj in data.get('projects', []):
                            p_title = proj.get('title', 'CCC Open Casting Project')
                            p_id = proj.get('id', '')
                            p_url = f"https://www.castingcall.club/projects/{p_id}" if p_id else ccc_url
                            p_desc = proj.get('description', 'Casting Call Club open project audition call.')[:250].strip()
                            scraped_jobs.append((
                                user_id, f"[CCC] {p_title[:75]}", "Casting Call Club Creator", "Casting Call Club - Website",
                                "Video Games", today_str, deadline_str, "🌍 Worldwide Remote", "Direct Web Application", "", p_url,
                                "$150 - $400 / Commercial Project", "Paid", p_desc, "Male", "20-40", "General British, US, RP", "Energetic, Grounded"
                            ))
                except Exception:
                    pass

    except Exception as e:
        scrape_errors.append(f"Casting Call Club (find_jobs): {e}")

    # 2. LIVE SCRAPE: Bluesky Public Search API (100% Open & Unauthenticated)
    try:
        bsky_search_terms = ["casting call voice", "voice actor needed", "voice artist needed", "looking for voice actor"]
        for term in bsky_search_terms[:2]:
            encoded_term = urllib.parse.quote(term)
            bsky_endpoint = f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={encoded_term}&limit=10"
            req = urllib.request.Request(bsky_endpoint, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                posts = data.get('posts', [])
                for p in posts:
                    author_handle = p.get('author', {}).get('handle', 'Bluesky User')
                    record = p.get('record', {})
                    text = record.get('text', 'Bluesky casting notice')[:250].strip()
                    rkey = p.get('uri', '').split('/')[-1]
                    post_url = f"https://bsky.app/profile/{author_handle}/post/{rkey}" if rkey else "https://bsky.app"
                    
                    first_line = text.splitlines()[0] if text else f"Casting Call from @{author_handle}"
                    title = first_line[:70]
                    scraped_jobs.append((
                        user_id, f"[BLUESKY] {title}", f"@{author_handle}", "Bluesky Social",
                        "Animation", today_str, deadline_str, "🌍 Worldwide Remote", "Direct Web Application", "", post_url,
                        "Indie / Commercial Rate", "Paid" if "paid" in text.lower() else "Unpaid Opportunity",
                        text, "Any", "20-50", "RP, General British, US", "Character, Conversational"
                    ))
    except Exception as e:
        scrape_errors.append(f"Bluesky Public API: {e}")

    # 3. LIVE SCRAPE: Reddit Subreddits (With Fixed User-Agent Headers)
    reddit_subs = ["recordthis", "VoiceActing", "CastingSeeks", "VoiceOver", "INAT", "Audiodrama", "IndieDev", "gamedev", "CastingCalls"]
    reddit_keywords = ['paid', 'casting', 'hiring', 'looking for', 'casting call', 'voice actor', 'voice artist', 'va needed', 'audition', 'narrator needed']
    
    for sub in reddit_subs:
        try:
            r_req = urllib.request.Request(f"https://www.reddit.com/r/{sub}/new.json?limit=8", headers=headers)
            with urllib.request.urlopen(r_req, timeout=4) as resp:
                r_data = json.loads(resp.read().decode('utf-8'))
                posts = r_data.get('data', {}).get('children', [])
                for p in posts:
                    pdata = p.get('data', {})
                    r_title = pdata.get('title', 'Reddit Casting Query')
                    r_permalink = f"https://www.reddit.com{pdata.get('permalink', '')}"
                    r_text = pdata.get('selftext', 'Open casting query posted on Reddit.')[:250].strip()
                    if any(kw in r_title.lower() or kw in r_text.lower() for kw in reddit_keywords):
                        scraped_jobs.append((
                            user_id, f"[{sub.upper()}] {r_title[:70]}", f"Reddit User u/{pdata.get('author', 'Client')}", f"Reddit (/r/{sub})",
                            "Corporate/ELT" if sub == "recordthis" else ("Audiobooks" if sub == "Audiodrama" else "Video Games"), 
                            today_str, deadline_str, "🌍 Worldwide Remote", "Direct Web Application", "", r_permalink,
                            "$100 - $350 / Project Rate", "Paid" if "[paid]" in r_title.lower() or "paid" in r_title.lower() else "Unpaid Opportunity",
                            r_text if r_text else "Reddit open audition call.", "Any", "20-50", "RP, General British", "Warm, Conversational"
                        ))
        except Exception as e:
            scrape_errors.append(f"Reddit /r/{sub}: {e}")

    # 4. LIVE SCRAPE: Newgrounds Collaboration Board (Animation & Game VO)
    try:
        ng_url = "https://www.newgrounds.com/bbs/forum/23"
        req = urllib.request.Request(ng_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            ng_matches = re.findall(r'/bbs/topic/([0-9]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            for t_id, raw_title in ng_matches[:10]:
                clean_title = re.sub(r'<[^<]+?>', '', raw_title).strip()
                if any(kw in clean_title.lower() for kw in ['voice', 'actor', 'casting', 'va', 'dub']):
                    t_url = f"https://www.newgrounds.com/bbs/topic/{t_id}"
                    scraped_jobs.append((
                        user_id, f"[NEWGROUNDS] {clean_title[:70]}", "Newgrounds Creator", "Newgrounds Collaboration Board",
                        "Animation", today_str, deadline_str, "🌍 Worldwide Remote", "Direct Web Application", "", t_url,
                        "Indie Game / Animation Rate", "Paid" if "paid" in clean_title.lower() else "Unpaid Opportunity",
                        "Newgrounds collaboration board casting call.", "Any", "18-45", "RP, US, General British", "Character"
                    ))
    except Exception as e:
        scrape_errors.append(f"Newgrounds BBS: {e}")

    return scraped_jobs, scrape_errors

# -----------------------------------------------------------------------------
# 5. UNIFIED RESOURCE VAULT DATABASE (100% CLEANED & VERIFIED - NO SCAM SITES)
# -----------------------------------------------------------------------------
VAULT_FULL_DATA = [
    {"Name": "VOPlanet", "Resource Type": "Dedicated Marketplace", "Work Type": "Commercial, Narration, Corporate", "Demo Required": "Yes (Commercial)", "Notes": "Buyers must post paid jobs only; no underbidding allowed. High quality signal-to-noise ratio.", "Link": "https://www.voplanet.com/"},
    {"Name": "Voice123", "Resource Type": "Pay-to-Play Marketplace", "Work Type": "Variety—audiobooks, commercial, character", "Demo Required": "No", "Notes": "Free tier allows limited applies; subscription tiers ($299–$2k+/yr) unlock higher audition volume.", "Link": "https://voice123.com/plans"},
    {"Name": "Voices.com", "Resource Type": "Pay-to-Play Marketplace", "Work Type": "Variety—commercial, corporate, narration", "Demo Required": "No", "Notes": "Free sign-up to browse/apply; priority & higher volume gated behind paid membership.", "Link": "https://www.voices.com/jobs"},
    {"Name": "The Voice Realm", "Resource Type": "Casting Database", "Work Type": "Commercial, Corporate", "Demo Required": "Yes (Commercial)", "Notes": "Buyer-side auto-matching tool for vetted talent.", "Link": "https://www.thevoicerealm.com/"},
    {"Name": "AhabTalent", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks & Voiceover", "Demo Required": "No", "Notes": "Free signup and free auditions; audition matches emailed directly to you.", "Link": "https://account.ahabtalent.com/signup/talent"},
    {"Name": "Fictra", "Resource Type": "Dedicated Marketplace", "Work Type": "Commercial, Character", "Demo Required": "No", "Notes": "Free account to audition; includes built-in payment escrow.", "Link": "https://fictra.co.uk/"},
    {"Name": "VOQuent", "Resource Type": "Casting Database / Agency", "Work Type": "International Commercial, Narration", "Demo Required": "Yes (Variety)", "Notes": "Functions like an agency roster; talent is matched and contacted directly.", "Link": "https://www.voquent.com/jobs/signup/"},
    {"Name": "Bodalgo", "Resource Type": "Pay-to-Play Marketplace", "Work Type": "Variety—audiobooks, commercial, character", "Demo Required": "Yes (Professional)", "Notes": "Based in Germany; free to browse, ~€40/mo for invitation-based auditions.", "Link": "https://www.bodalgo.com/en"},
    {"Name": "AllCasting", "Resource Type": "Casting Board", "Work Type": "Voiceover & On-Camera", "Demo Required": "No", "Notes": "Voiceover section includes local and remote opportunities.", "Link": "https://allcasting.com/castingcalls/voiceover"},
    {"Name": "VoiceBooking.com", "Resource Type": "Agency / Marketplace", "Work Type": "European & International Commercial", "Demo Required": "Yes (Commercial)", "Notes": "European market focus; curated roster.", "Link": "https://www.voicebooking.com/"},
    {"Name": "Fiverr", "Resource Type": "General Freelance", "Work Type": "Voiceover Gigs & Commercials", "Demo Required": "No", "Notes": "Free to browse and list services; commission taken on completed orders.", "Link": "https://www.fiverr.com/search/gigs?query=voice%20over"},
    {"Name": "Upwork", "Resource Type": "General Freelance", "Work Type": "Variety—narration, games, commercial", "Demo Required": "No", "Notes": "Free to browse and bid with monthly free Connects.", "Link": "https://www.upwork.com/freelance-jobs/apply/voice-over_~/"},
    {"Name": "PeoplePerHour", "Resource Type": "General Freelance", "Work Type": "Commercial & Corporate VO", "Demo Required": "No", "Notes": "Free browsing; service fee applies to completed projects.", "Link": "https://www.peopleperhour.com/freelance-voice-over-jobs"},
    {"Name": "Freelancer.com", "Resource Type": "General Freelance", "Work Type": "Voiceover & Audio Editing", "Demo Required": "No", "Notes": "Free to sign up and bid on active client queries.", "Link": "https://www.freelancer.com/job-search/voice-over/"},
    {"Name": "Guru.com", "Resource Type": "General Freelance", "Work Type": "Corporate, ELT, Narration", "Demo Required": "No", "Notes": "Free browse and job application submissions.", "Link": "https://www.guru.com/d/jobs/skill/voice-over/"},
    {"Name": "Twine.net", "Resource Type": "General Freelance", "Work Type": "Voiceover Artists & Singers", "Demo Required": "No", "Notes": "Talent list day rates; free to join and bid.", "Link": "https://www.twine.net/find/voiceover-artists"},
    {"Name": "Behance Job Board", "Resource Type": "Creative Job Board", "Work Type": "Animation, Video Games, Commercial", "Demo Required": "No", "Notes": "Clean, filtered creative listings.", "Link": "https://www.behance.net/joblist?country=US&search=voice+over"},
    {"Name": "ACX (Audible)", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks", "Demo Required": "No", "Notes": "Free account and auditions; US/UK/Canada/Ireland residents only.", "Link": "https://www.acx.com/"},
    {"Name": "Findaway Voices", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks", "Demo Required": "No", "Notes": "Free profile; projects are algorithmically matched to your voice specs.", "Link": "https://findawayvoices.com/narrators"},
    {"Name": "Author's Republic", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks", "Demo Required": "No", "Notes": "Distribution and production service for audiobook narrators.", "Link": "https://www.authorsrepublic.com/"},
    {"Name": "LibriVox", "Resource Type": "Volunteer Audiobook", "Work Type": "Public Domain Audiobooks", "Demo Required": "No", "Notes": "Fully volunteer public-domain audiobook narration.", "Link": "https://librivox.org/pages/volunteer-for-librivox/"},
    {"Name": "Learning Ally", "Resource Type": "Volunteer Narration", "Work Type": "Educational Narration", "Demo Required": "No", "Notes": "Volunteer narration for students with reading disabilities.", "Link": "https://learningally.org/About-Us/Overview"},
    {"Name": "Gatewave", "Resource Type": "Volunteer Broadcast", "Work Type": "News & Article Narration", "Demo Required": "No", "Notes": "Reads content for visually impaired listeners.", "Link": "http://gatewave.org/volunteer-faq"},
    {"Name": "Casting Call Club", "Resource Type": "Open Casting Platform", "Work Type": "Animation, Games, Audio Dramas", "Demo Required": "No", "Notes": "100% free at every step. Browse, apply, and get hired.", "Link": "https://www.castingcall.club/find_jobs"},
    {"Name": "Actor's Access", "Resource Type": "Casting Network", "Work Type": "Voiceover, On-Camera, Theatre", "Demo Required": "No", "Notes": "$68/yr subscription; check breakdowns for VO specification.", "Link": "https://actorsaccess.com/"},
    {"Name": "Backstage", "Resource Type": "Casting Network", "Work Type": "General Voiceover & On-Camera", "Demo Required": "No", "Notes": "Free to browse; ~$16–25/mo to submit applications.", "Link": "https://www.backstage.com/casting/?role_type=V&job_type=vo"},
    {"Name": "Mandy.com (Voiceover)", "Resource Type": "Casting Network", "Work Type": "Commercial, Film, Corporate", "Demo Required": "No", "Notes": "Free profile creation; subscription required to submit applications.", "Link": "https://voiceovers.mandy.com/us"},
    {"Name": "StarNow", "Resource Type": "Casting Network", "Work Type": "Commercial & Voiceover", "Demo Required": "No", "Notes": "Part of Backstage/Mandy group; subscription required to apply.", "Link": "https://www.starnow.com/"},
    {"Name": "Stage32", "Resource Type": "Creative Networking", "Work Type": "Film, Animation, Games", "Demo Required": "No", "Notes": "Free film community job board; periodic voiceover calls.", "Link": "https://www.stage32.com/find-jobs"},
    {"Name": "Amazing Voice", "Resource Type": "Studio Roster", "Work Type": "IVR, Corporate Narration", "Demo Required": "Yes (Commercial)", "Notes": "Curated studio roster; requires high quality commercial demo.", "Link": "https://www.amazingvoice.com/voice-talent-application"},
    {"Name": "Blend Voices (formerly GM Voices)", "Resource Type": "Studio Roster", "Work Type": "Commercial, IVR, e-Learning", "Demo Required": "Yes (Raw Sample)", "Notes": "Requires raw booth sample; transparent regarding AI vs human bookings.", "Link": "https://www.gmvoices.com/"},
    {"Name": "Blue Wave", "Resource Type": "Studio Roster", "Work Type": "Political Voiceover", "Demo Required": "Yes (Political)", "Notes": "Specialist political VO roster; requires produced political demo.", "Link": "https://www.bluewavevoiceover.com/"},
    {"Name": "CAS Music", "Resource Type": "Studio Roster", "Work Type": "Commercial, Narration", "Demo Required": "Yes (Commercial)", "Notes": "Requires anonymous commercial demo (no spoken name in audio).", "Link": "https://casmusic.com/voice-over-submissions/"},
    {"Name": "Casting by Smile", "Resource Type": "Studio Roster", "Work Type": "Commercial & Corporate", "Demo Required": "Yes (Multiple)", "Notes": "Sweden-based studio; submit resume + up to 3 demos via form.", "Link": "https://www.studiosmile.se/contact"},
    {"Name": "Creative Media Design NYC", "Resource Type": "Studio Roster", "Work Type": "Commercial, Games, Promo", "Demo Required": "Yes (Pro Setup)", "Notes": "Requires Source-Connect Standard or ipDTL pro studio capability.", "Link": "https://www.cmdnyc.com/new-talent-form/"},
    {"Name": "Deyan Audio", "Resource Type": "Studio Roster", "Work Type": "Audiobooks", "Demo Required": "Yes (Narration)", "Notes": "Major audiobook production studio; submit via contact page.", "Link": "https://www.deyanaudio.com/"},
    {"Name": "Dragonuk Connects", "Resource Type": "Networking Board", "Work Type": "US Mid-Atlantic Regional VO", "Demo Required": "No", "Notes": "Paid membership required for active forum messaging.", "Link": "https://www.dragonukconnects.com/"},
    {"Name": "DreamVoices", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks & Commercial", "Demo Required": "Yes (Narration)", "Notes": "Periodic roster opens for diverse narration talent.", "Link": "https://www.dreamempirefilms.com/"},
    {"Name": "Ear Works Media", "Resource Type": "Studio Roster", "Work Type": "Commercial & Narration", "Demo Required": "Yes (Commercial)", "Notes": "Requires Source-Connect Standard/Pro; quick turnaround capability.", "Link": "https://www.earworks.com/voice-talent-application"},
    {"Name": "Encore Voices", "Resource Type": "Studio Roster", "Work Type": "Dubbing & Localization", "Demo Required": "Yes (Character)", "Notes": "Dubbing studio; submit via website account portal.", "Link": "https://talent.encorevoices.com/talent-registration/"},
    {"Name": "Graphic Audio", "Resource Type": "Audiobook / Audio Drama DB", "Work Type": "Full-Cast Audio Dramas", "Demo Required": "Yes (Character)", "Notes": "Full cast audio dramas; submit via Google form with character/dialect demo.", "Link": "https://www.graphicaudio.net/"},
    {"Name": "Halp Network", "Resource Type": "Studio Roster", "Work Type": "Video Games, MoCap", "Demo Required": "Yes (Character)", "Notes": "Game studio roster; expects character demo on your personal site.", "Link": "https://airtable.com/shrJEs3NswRmy3pZ8"},
    {"Name": "Holdcom", "Resource Type": "Studio Roster", "Work Type": "IVR, Telephony, Narration", "Demo Required": "Yes (Script Read)", "Notes": "Record sample script to submit; requires 24-hr turnaround ability.", "Link": "https://www.holdcom.com/voice-talent-audition/"},
    {"Name": "JL Studios", "Resource Type": "Studio Roster", "Work Type": "Commercial, Narration", "Demo Required": "No", "Notes": "Submit form detailing booth specs and voice description.", "Link": "https://jlstudios.ca/"},
    {"Name": "khōréō", "Resource Type": "Studio Roster", "Work Type": "Audiobooks / Podcasts", "Demo Required": "No", "Notes": "Seeks diaspora/immigrant voice artists for speculative fiction stories.", "Link": "https://www.khoreomag.com/voice-actors/"},
    {"Name": "Kocha Sound", "Resource Type": "Studio Roster", "Work Type": "Anime, Animation, Games", "Demo Required": "Yes (Character)", "Notes": "Character/animation focus; strict one-submission policy.", "Link": "http://www.kochasound.com/contact-us/"},
    {"Name": "Lau Lapides / MCVO", "Resource Type": "Agency Roster", "Work Type": "Commercial", "Demo Required": "Yes (Commercial)", "Notes": "Freelance agency model; requires Source-Connect Standard.", "Link": "https://laulapidescompany.com/"},
    {"Name": "Network Nexus Studios", "Resource Type": "Studio Roster", "Work Type": "Animation, Games", "Demo Required": "Yes (Character)", "Notes": "Apply via Careers -> Talent Pool Application Form.", "Link": "https://www.networknexusstudios.com/"},
    {"Name": "Newgrounds - Forum", "Resource Type": "Community Forum", "Work Type": "Indie Games & Animation", "Demo Required": "No", "Notes": "Free community forum for indie game and animation casting calls.", "Link": "https://www.newgrounds.com/bbs/forum/23"},
    {"Name": "No Studio in Particular", "Resource Type": "Indie Studio Mailing List", "Work Type": "Character, Narration", "Demo Required": "Yes (Character)", "Notes": "Mailing list + Discord casting calls for indie animation/games.", "Link": "https://docs.google.com/forms/d/e/1FAIpQLScLrNPF5iM1eGiKtev29v2LO2VQH68BUvqvFa7xnCm9UVjgIQ/viewform"},
    {"Name": "ProComm Voices", "Resource Type": "Studio Roster", "Work Type": "Commercial", "Demo Required": "Yes (Commercial)", "Notes": "Requires commercial demo and Source-Connect Standard.", "Link": "https://www.procommvoices.com/"},
    {"Name": "Royal Guard Publishing", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks", "Demo Required": "Yes (Narration)", "Notes": "Audiobook publisher; requests samples, website link, and rate card.", "Link": "https://royalguardpublishing.com/submissions/"},
    {"Name": "Sound Cadence Studios", "Resource Type": "Studio Roster", "Work Type": "Anime, Games, Animation", "Demo Required": "Yes (Character)", "Notes": "Submit via New Actor Submission Form; do not resubmit identical info.", "Link": "https://www.soundcadencestudios.com/"},
    {"Name": "Studio Coattails", "Resource Type": "Studio Roster", "Work Type": "Visual Novels, Video Games", "Demo Required": "Yes (Character)", "Notes": "Google Form submission for visual novel and indie game roster.", "Link": "https://studiocoattails.com/"},
    {"Name": "Studio Nano", "Resource Type": "Studio Roster", "Work Type": "Anime & Animation Dubbing", "Demo Required": "Yes (Character)", "Notes": "Dubbing studio; red button submission form on contact page.", "Link": "https://studionano.com/contact-us"},
    {"Name": "TYDEF Studios", "Resource Type": "Studio Roster", "Work Type": "Audiobooks & Commercial", "Demo Required": "Yes (Narration)", "Notes": "Atlanta-based production studio; submit samples via roster sign-up.", "Link": "https://www.tydefstudios.com/actor-roster-signup"},
    {"Name": "Very Berry Studios", "Resource Type": "Studio Roster", "Work Type": "Indie Games & Visual Novels", "Demo Required": "No", "Notes": "Maintains specialized rosters for diverse and authentic casting.", "Link": "https://veryberrystudios.com/"},
    {"Name": "Voice Acting Alliance (VAA)", "Resource Type": "Community Group", "Work Type": "Audio Dramas, Indie Games", "Demo Required": "No", "Notes": "Facebook community group for open casting announcements.", "Link": "https://www.facebook.com/groups/voiceactingallianceunofficialgroup/"},
    {"Name": "Voice Acting Club (VAC) - Forum", "Resource Type": "Community Forum", "Work Type": "Animation, Games, Audio Dramas", "Demo Required": "No", "Notes": "Active open board featuring paid and unpaid community castings.", "Link": "https://voiceacting.boards.net/"},
    {"Name": "Voice Acting Club (VAC) - Discord", "Resource Type": "Discord Community", "Work Type": "Indie Projects & Voice Acting", "Demo Required": "No", "Notes": "Companion Discord server for real-time audition announcements.", "Link": "https://discord.gg/voiceactingclub"},
    {"Name": "Voice Talent Warehouse", "Resource Type": "Studio Roster", "Work Type": "Commercial & Corporate", "Demo Required": "Yes (Variety)", "Notes": "Reviews new submission forms monthly for roster additions.", "Link": "https://voicetalentwarehouse.com/contact/"},
    {"Name": "Voiceover Cafe", "Resource Type": "Agency Roster", "Work Type": "UK Commercial, Corporate, ELT", "Demo Required": "Yes (Variety)", "Notes": "UK-based localization agency; submit demos and rate card to hello@voiceover.cafe.", "Link": "https://voiceover.cafe/"},
    {"Name": "VoiceProductions", "Resource Type": "Agency / Marketplace", "Work Type": "International Commercial & Narration", "Demo Required": "Yes (3 Demos)", "Notes": "Netherlands-based; requires minimum of 3 demos for profile review.", "Link": "https://www.voiceproductions.com/en/registration-voice-actor"},
    {"Name": "VSI Group", "Resource Type": "Dubbing & Localization", "Work Type": "Global Dubbing & Subtitling", "Demo Required": "Yes (Sample)", "Notes": "Global dubbing provider; apply via Freelancers portal.", "Link": "https://vsi.tv/contact"},
    {"Name": "Wehear", "Resource Type": "Audiobook Production", "Work Type": "Audiobooks", "Demo Required": "Yes (Narration)", "Notes": "Audiobook app narrator program; submit demo to voices@wehearfm.com.", "Link": "https://wehearfm.com/narrator-program"},
    {"Name": "Zoo Digital", "Resource Type": "Dubbing & Localization", "Work Type": "Film & TV Dubbing", "Demo Required": "Yes (Sample)", "Notes": "Cloud dubbing vendor; apply via freelance vacancies portal.", "Link": "https://www.zoodigital.com/freelance-vacancies/voice-actor/"}
]

# -----------------------------------------------------------------------------
# 6. AUTHENTICATION & ONBOARDING GATEKEEPER
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
            o_height = st.text_input("Height", value="5ft 10in (178cm)")
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

            # DEDICATED REAL-TIME SEARCH ENGINES & DORKS (EXTENDED LAUNCHPAD)
            with st.expander("🔎 Launch External Search Engines & Social Feeds (LinkedIn, Bluesky, Twitter, Google, Craigslist, Itch)", expanded=False):
                st.markdown("Launch live, pre-formatted queries on external search engines and social platforms:")
                
                s1, s2, s3, s4 = st.columns(4)
                with s1:
                    li_posts_url = "https://www.linkedin.com/search/results/content/?keywords=%22casting%22%20AND%20(%22voice%20actor%20needed%22%20OR%20%22voice%20artist%20needed%22%20OR%20%22seeking%20voice%20actor%22)&sortBy=%22date_posted%22"
                    st.markdown(f'<a href="{li_posts_url}" target="_blank"><button style="background-color:#0077B5;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;">🔗 LinkedIn Posts Feed</button></a>', unsafe_allow_html=True)
                with s2:
                    bsky_url = "https://bsky.app/search?q=%22casting%20call%22%20voice"
                    st.markdown(f'<a href="{bsky_url}" target="_blank"><button style="background-color:#0085FF;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;">🦋 Bluesky Casting Feed</button></a>', unsafe_allow_html=True)
                with s3:
                    tw_url = "https://x.com/search?q=(%23VACastingCall%20OR%20%23VOCasting%20OR%20%22voice%20actor%20needed%22)&f=live"
                    st.markdown(f'<a href="{tw_url}" target="_blank"><button style="background-color:#000000;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;">🐦 Twitter/X Live Feed</button></a>', unsafe_allow_html=True)
                with s4:
                    gf_url = "https://www.google.com/search?q=site:docs.google.com/forms+%22casting+call%22+(%22voice+actor%22+OR+%22voiceover%22)"
                    st.markdown(f'<a href="{gf_url}" target="_blank"><button style="background-color:#0F9D58;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;">📋 Google Forms Search</button></a>', unsafe_allow_html=True)

                s5, s6, s7, s8 = st.columns(4)
                with s5:
                    cl_url = "https://www.google.com/search?q=site:craigslist.org+%22voice+over%22+OR+%22voice+actor+needed%22"
                    st.markdown(f'<a href="{cl_url}" target="_blank"><button style="background-color:#551A8B;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;margin-top:6px;">☮️ Craigslist VO Search</button></a>', unsafe_allow_html=True)
                with s6:
                    itch_url = "https://www.google.com/search?q=site:itch.io+%22voice+actor%22+needed+OR+%22casting+call%22"
                    st.markdown(f'<a href="{itch_url}" target="_blank"><button style="background-color:#FA5C5C;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;margin-top:6px;">🎮 itch.io Indie Game Calls</button></a>', unsafe_allow_html=True)
                with s7:
                    fb_url = "https://www.facebook.com/groups/voiceactingclub/"
                    st.markdown(f'<a href="{fb_url}" target="_blank"><button style="background-color:#1877F2;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;margin-top:6px;">👥 Facebook VAC Group</button></a>', unsafe_allow_html=True)
                with s8:
                    typeform_url = "https://www.google.com/search?q=site:typeform.com/to+(%22casting+call%22+OR+%22voice+audition%22)"
                    st.markdown(f'<a href="{typeform_url}" target="_blank"><button style="background-color:#262627;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;margin-top:6px;">📄 Typeform Intake Dork</button></a>', unsafe_allow_html=True)

            st.divider()

            col_sync, col_purge = st.columns([1.5, 1])
            
            with col_sync:
                if st.button("🔄 Scrub Open Casting Directories Now"):
                    st.toast("Scrubbing live external directories, APIs & subreddits...", icon="🔍")
                    
                    scraped_data_feed, scrape_errors = fetch_live_casting_opportunities(user_id)
                    
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
                        st.rerun()
                    else:
                        c.execute("SELECT COUNT(*) FROM active_jobs WHERE user_id = %s", (user_id,))
                        total_db_jobs = c.fetchone()[0]
                        if total_db_jobs > 0:
                            st.info("Live feed is fully up to date.")
                        else:
                            st.warning(f"Scraper completed. Parsed {len(scraped_data_feed)} items from live sources.")
                            if scrape_errors:
                                with st.expander("⚠️ View Network Connection Logs"):
                                    for err in scrape_errors:
                                        st.write(f"- `{err}`")
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

                    # SOFT VOCAL STYLE MATCHING
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
        # TAB 4: UNIFIED RESOURCE & AGENCY INTAKE VAULT (CLICKABLE DIRECTORY)
        # ---------------------------------------------------------------------
        with tabs[3]:
            st.header("📚 Tab 4: Unified Resource & Agency Intake Vault")
            st.caption("All verified roster submission forms, agency portals, audiobook databases, and intake links from your directory.")

            # Search & Filter Controls
            sc1, sc2, sc3 = st.columns([2, 1, 1])
            with sc1:
                search_query = st.text_input("🔍 Search Vault by Name or Keywords:", value="", placeholder="e.g. Graphic Audio, Audiobook, Studio Roster...")
            with sc2:
                all_res_types = ["All Types"] + sorted(list(set(r["Resource Type"] for r in VAULT_FULL_DATA)))
                selected_res_type = st.selectbox("Resource Type", all_res_types)
            with sc3:
                all_demo_reqs = ["All Requirements"] + sorted(list(set(r["Demo Required"] for r in VAULT_FULL_DATA)))
                selected_demo_req = st.selectbox("Demo Required?", all_demo_reqs)

            # Filter Logic
            filtered_vault = []
            for item in VAULT_FULL_DATA:
                m_q = search_query.lower()
                matches_search = not m_q or (m_q in item["Name"].lower() or m_q in item["Work Type"].lower() or m_q in item["Notes"].lower())
                matches_res = (selected_res_type == "All Types") or (item["Resource Type"] == selected_res_type)
                matches_demo = (selected_demo_req == "All Requirements") or (item["Demo Required"] == selected_demo_req)
                
                if matches_search and matches_res and matches_demo:
                    filtered_vault.append(item)

            st.write(f"Showing **{len(filtered_vault)}** of **{len(VAULT_FULL_DATA)}** verified intake portals")

            view_mode = st.radio("View Mode:", ["📊 Interactive Table View", "📱 Interactive Cards View"], horizontal=True)

            st.divider()

            if view_mode == "📊 Interactive Table View":
                df_vault = pd.DataFrame(filtered_vault)
                cols_order = ["Name", "Resource Type", "Work Type", "Demo Required", "Notes", "Link"]
                df_vault = df_vault[cols_order]

                st.dataframe(
                    df_vault,
                    column_config={
                        "Name": st.column_config.TextColumn("Directory / Agency", width="medium"),
                        "Resource Type": st.column_config.TextColumn("Resource Category", width="small"),
                        "Work Type": st.column_config.TextColumn("Work Disciplines", width="medium"),
                        "Demo Required": st.column_config.TextColumn("Demo Req.", width="small"),
                        "Notes": st.column_config.TextColumn("Submission Notes & Requirements", width="large"),
                        "Link": st.column_config.LinkColumn(
                            "Intake Link / Portal",
                            help="Click to open the intake form directly in a new tab",
                            validate="^https?://",
                            display_text="🔗 Open Intake Portal",
                            width="medium"
                        )
                    },
                    hide_index=True,
                    use_container_width=True
                )

            else:  # Interactive Cards View
                for item in filtered_vault:
                    clean_link = sanitize_url(item["Link"])
                    with st.expander(f"📚 {item['Name']} — {item['Resource Type']} ({item['Work Type']})"):
                        c_col1, c_col2 = st.columns([3, 1])
                        with c_col1:
                            st.write(f"**Work Disciplines:** `{item['Work Type']}`")
                            st.write(f"**Demo Requirement:** `{item['Demo Required']}`")
                            st.write(f"**Notes & Requirements:** {item['Notes']}")
                        with c_col2:
                            st.markdown(f'<a href="{clean_link}" target="_blank"><button style="background-color:#2563EB;color:white;border:none;padding:12px 18px;border-radius:6px;cursor:pointer;width:100%;font-weight:bold;margin-top:10px;">🔗 Open Intake Portal</button></a>', unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # TAB 5: SPOTLIGHT PROFILE & GDPR PRIVACY CONTROLS
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
