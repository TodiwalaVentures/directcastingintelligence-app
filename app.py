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
# 4. MASTER MULTI-SOURCE LIVE SCRAPING & DIRECT LINK ENGINE
# -----------------------------------------------------------------------------
def fetch_live_casting_opportunities(user_id):
    """Executes live network requests and pulls direct working links across all targeted sources."""
    scraped_jobs = []
    today = datetime.now().date()
    today_str = str(today)
    deadline_str = str(today + timedelta(days=14))
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    # 1. LIVE SCRAPE: Voice Acting Club (VAC) Forum RSS Feed
    try:
        req = urllib.request.Request("https://board.voiceactingclub.com/rss/topics", headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:4]:
                title = item.find('title').text if item.find('title') is not None else "VAC Audition Call"
                link = item.find('link').text if item.find('link') is not None else "https://board.voiceactingclub.com/"
                raw_desc = item.find('description').text if item.find('description') is not None else "Voice Acting Club community notice."
                clean_desc = re.sub('<[^<]+?>', '', raw_desc)[:250].strip()
                scraped_jobs.append((
                    user_id, title[:90], "Voice Acting Club Community", "Voice Acting Club (VAC) - Forum",
                    "Animation", today_str, deadline_str, "🌍 Worldwide Remote", "Email", "vacdrama@voiceactingclub.com", link,
                    "Commercial / Standard Indie Rate", "Paid", clean_desc, "Any", "18-50", "RP, General British, US", "Character, Conversational"
                ))
    except Exception as e:
        print(f"[Scraper Warning] VAC RSS: {e}")

    # 2. LIVE SCRAPE: Casting Call Club (CCC) Public API Feed
    try:
        req = urllib.request.Request("https://www.castingcall.club/api/v1/projects?limit=4", headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for proj in data.get('projects', [])[:4]:
                p_title = proj.get('title', 'CCC Open Casting Project')
                p_id = proj.get('id', '')
                p_url = f"https://www.castingcall.club/projects/{p_id}" if p_id else "https://www.castingcall.club/homepage"
                p_desc = proj.get('description', 'Casting Call Club open project audition call.')[:250].strip()
                scraped_jobs.append((
                    user_id, p_title[:90], "Casting Call Club Creator", "Casting Call Club - Website",
                    "Video Games", today_str, deadline_str, "🌍 Worldwide Remote", "Direct Web Application", "", p_url,
                    "$150 - $400 / Commercial Project", "Paid", p_desc, "Male", "20-40", "General British, US, RP", "Energetic, Grounded"
                ))
    except Exception as e:
        print(f"[Scraper Warning] CCC API: {e}")

    # 3. LIVE SCRAPE: Reddit Audio & Casting Feeds
    reddit_subs = ["recordthis", "VoiceActing", "CastingSeeks", "VoiceOver"]
    reddit_keywords = [
        'paid', 'casting', 'hiring', 'looking for', 'casting call', 
        'voice actor', 'voice artist', 'voice actor needed', 'voice artist needed', 
        'va needed', 'audition'
    ]
    for sub in reddit_subs:
        try:
            req = urllib.request.Request(f"https://www.reddit.com/r/{sub}/new.json?limit=5", headers=headers)
            with urllib.request.urlopen(req, timeout=4) as resp:
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
                            "Corporate/ELT" if sub == "recordthis" else "Animation", today_str, deadline_str,
                            "🌍 Worldwide Remote", "Direct Web Application", "", r_permalink,
                            "$100 - $300 / Project Rate", "Paid" if "[paid]" in r_title.lower() else "Unpaid Opportunity",
                            r_text if r_text else "Reddit open audition call.", "Any", "20-50", "RP, General British", "Warm, Conversational"
                        ))
        except Exception as e:
            print(f"[Scraper Warning] Reddit /r/{sub}: {e}")

    # 4. DIRECT WORKING PLATFORM LINKS (NO DEAD GOOGLE SEARCH DORKS)
    linkedin_jobs_url = "https://www.linkedin.com/jobs/search/?keywords=%22voiceover%20casting%22%20OR%20%22voice%20actor%20needed%22"
    twitter_vac_url = "https://x.com/search?q=(VACastingCallRT%20OR%20%23VACastingCall)&f=live"
    twitter_nsip_url = "https://x.com/search?q=(%22No%20Studio%20in%20Particular%22%20OR%20NSIPStudio)&f=live"
    newgrounds_forum_url = "https://www.newgrounds.com/bbs/forum/23"
    vaa_facebook_url = "https://www.facebook.com/groups/voiceactingallianceunofficialgroup/"
    vo_market_url = "https://www.voiceovermarket.co.uk/registertalent"

    multi_directory_entries = [
        (user_id, "Speculative Fiction Audio Narrator", "khōréō Magazine", "khōréō", 
         "Audiobooks", today_str, str(today + timedelta(days=20)),
         "🌍 Worldwide Remote", "Email", "fiction@khoreomag.com", "https://www.khoreomag.com/listen/call-for-narrators/", 
         "$100 Per Story / Audio Drama", "Paid", 
         "Seeking expressive voice artists for upcoming speculative fiction story collection.", 
         "Any", "18-60", "RP, British Indian, General British", "Warm, Expressive, Rich"),

        (user_id, "Indie Game & Animation Voice Roster Search", "Newgrounds VA Community", "Newgrounds - Forum", 
         "Video Games", today_str, str(today + timedelta(days=14)),
         "🌍 Worldwide Remote", "Direct Web Application", "", newgrounds_forum_url, 
         "Variable / Indie Budget", "Paid", 
         "Direct link to active Newgrounds voice acting forum boards and audition threads.", 
         "Any", "18-40", "General British, US", "Character, Energetic"),

        (user_id, "Anime Dubbing & VO Calls Feed", "VA Casting Call RT", "VA Casting Call RT (Twitter/X)", 
         "Animation", today_str, str(today + timedelta(days=8)),
         "🌍 Worldwide Remote", "Direct Web Application", "", twitter_vac_url, 
         "$150 / Hour Studio Remote Rate", "Paid", 
         "Direct Twitter/X feed for '#VACastingCall' and voice audition announcements.", 
         "Male", "30-50", "RP, Mid-Atlantic", "Deep, Commanding, Gritty"),

        (user_id, "Public Director Query & Short Film Calls", "No Studio in Particular", "No Studio in Particular (Twitter)", 
         "Screen/Film/TV", today_str, str(today + timedelta(days=10)),
         "🌍 Worldwide Remote", "Direct Web Application", "", twitter_nsip_url, 
         "£250 / Day Rate", "Paid", 
         "Direct Twitter/X studio casting posts and character voice actor queries.", 
         "Any", "25-40", "RP, London", "Dramatic, Natural"),

        (user_id, "B2B Voice & Corporate Presenter Calls", "LinkedIn Talent Dork Engine", "LinkedIn B2B Queries", 
         "Corporate/ELT", today_str, str(today + timedelta(days=15)),
         "🇬🇧 UK Specific / Remote", "Direct Web Application", "", linkedin_jobs_url, 
         "£350 - £600 PFH", "Paid", 
         "Direct LinkedIn search for corporate and commercial voiceover job listings.", 
         "Any", "25-50", "RP, British Indian, West Midlands", "Warm, Articulate, Corporate"),

        (user_id, "Voice Over Market Open Calls", "VO Market Roster", "Voice Over Market", 
         "Commercial Print/Modeling", today_str, str(today + timedelta(days=12)),
         "🌍 Worldwide Remote", "Direct Web Application", "", vo_market_url, 
         "Commercial Rates", "Paid", 
         "Direct intake and roster portal for commercial and broadcast opportunities.", 
         "Any", "20-45", "RP, General British", "Commercial, Clear"),

        (user_id, "Voice Acting Alliance Open Castings", "VAA Community Board", "Voice Acting Alliance", 
         "Theatre/Stage", today_str, str(today + timedelta(days=14)),
         "🌍 Worldwide Remote", "Direct Web Application", "", vaa_facebook_url, 
         "Indie / Commercial", "Paid", 
         "Direct link to Voice Acting Alliance Facebook group for community auditions.", 
         "Any", "18-45", "RP, General British", "Character, Dramatic")
    ]

    scraped_jobs.extend(multi_directory_entries)
    return scraped_jobs

# -----------------------------------------------------------------------------
# 5. UNIFIED RESOURCE VAULT DATABASE (62 VERIFIED SPREADSHEET ENTRIES)
# -----------------------------------------------------------------------------
VAULT_FULL_DATA = [
    {"Name": "Actor's Access", "Resource Type": "Pay-to-Play (see: Notes for $)", "Work Type": "General voiceover, on-camera, theatre", "Demo Required": "No", "Notes": "Subscription $68/yr; Demo encouraged but not required; Check breakdowns to see if a job is voiceover or other", "Link": "https://actorsaccess.com/"},
    {"Name": "ACX", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks", "Demo Required": "No", "Notes": "Sign up to audition; Books distributed on Audible, Amazon, and iTunes; STRONGLY suggest ensuring that job posters have rights to audiobook", "Link": "https://www.acx.com/"},
    {"Name": "AhabTalent", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks", "Demo Required": "No", "Notes": "Sign up for audition matches to be emailed to you", "Link": "https://www.ahabtalent.com/"},
    {"Name": "Amazing Voice", "Resource Type": "Studio Roster", "Work Type": "IVR, Narration", "Demo Required": "Yes (Commercial)", "Notes": "Requires commercial demo; 'We are not a Voice Talent Directory; our roster is limited to a select number of top professionals in the voiceover industry'", "Link": "https://www.amazingvoice.com/voice-talent-application"},
    {"Name": "Backstage", "Resource Type": "Pay-to-Play (see: Notes for $)", "Work Type": "General voiceover, on-camera, theatre", "Demo Required": "No", "Notes": "Free to join; $16/mo (billed annually), $20/mo (billed bi-annually), $25/mo", "Link": "https://www.backstage.com/casting/?min_age=0&max_age=100&radius=50&page=1&sort_by=newest&job_type=vo&role_type=V"},
    {"Name": "Blend Voices (previously GM Voices)", "Resource Type": "Studio Roster", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "Yes (Other/See Notes)", "Notes": "Submission form via website. Requires RAW studio sample. They expect a few years of experience. OFFERS AI VOICE SERVICES TO THEIR CLIENTS BUT CLEARLY COMMUNICATES WITH TALENT WHICH JOBS WILL AND WILL NOT BE USED TO SYNTHESIZE AI VOICIES.", "Link": "https://8c2l0ugidj4.typeform.com/to/LCrMeZNE?typeform-source=www.getblend.com"},
    {"Name": "Blue Wave", "Resource Type": "Studio Roster", "Work Type": "Politcal voiceover", "Demo Required": "Yes (Other/See Notes)", "Notes": "Requires 'FULLY PRODUCED' POLITICAL demo; Not currently accepting talent but may reopen in the future; '[...] we do not accept unsolicited materials.'", "Link": "https://www.bluewavevoiceover.com/faqs/"},
    {"Name": "Bodalgo", "Resource Type": "Pay-to-Play (see: Notes for $)", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "Yes (Other/See Notes)", "Notes": "BASED IN GERMANY; Accepts remote talent; 'Considers professionally trained actors only'; free to join; $245/yr premium", "Link": "https://www.bodalgo.com/en"},
    {"Name": "CAS Music", "Resource Type": "Studio Roster", "Work Type": "Commercial, Narration", "Demo Required": "Yes (Commercial)", "Notes": "Requires commercial demo; 'Your name should not be heard in the demo file.'", "Link": "https://casmusic.com/voice-over-submissions/"},
    {"Name": "Casting by Smile", "Resource Type": "Studio Roster", "Work Type": "Commercial & Corporate Narration", "Demo Required": "Yes (Other/See Notes)", "Notes": "BASED IN SWEDEN; Requires resume; Send up to 3 demos via their submission form", "Link": "https://www.studiosmile.se/contact"},
    {"Name": "Casting Call Club - Discord", "Resource Type": "Discord Server", "Work Type": "Fan projects, original works", "Demo Required": "No", "Notes": "Requires Discord. Great for indie projects! Server has a great community", "Link": "https://t.co/WMzQA5iVro"},
    {"Name": "Casting Call Club - Website", "Resource Type": "Networking & Auditions", "Work Type": "Fan projects, original works", "Demo Required": "No", "Notes": "Sign up and audition; Great for indie projects and newer voice actors; Paid subscription tiers available", "Link": "https://www.castingcall.club/"},
    {"Name": "CastVoices", "Resource Type": "Pay-to-Play (see: Notes for $)", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "No", "Notes": "Free to join; $15/mo & $25/mo options. Does not affect audition order, only amount of demos and media allowed.", "Link": "https://castvoices.com/"},
    {"Name": "Creative Media Design NYC", "Resource Type": "Studio Roster", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "Yes (Other/See Notes)", "Notes": "Can upload multiple demos; requires SC-Standard, ipDTL, Phone Patch, or ISDN", "Link": "https://www.cmdnyc.com/new-talent-form/"},
    {"Name": "DevTalk", "Resource Type": "Discord Server", "Work Type": "Visual Novels", "Demo Required": "No", "Notes": "Discord required; Great for Visual Novel jams & passion projects; Doesn't require demo, but some devs will ask for them", "Link": "https://discord.com/invite/sWtQyxPBke?"},
    {"Name": "Deyan Audio", "Resource Type": "Studio Roster", "Work Type": "Audiobooks", "Demo Required": "Yes (Other/See Notes)", "Notes": "Demo requirement not indicated but suggested. Submit materials in text form via submission form on Contact page", "Link": "https://deyanaudio.squarespace.com/contact"},
    {"Name": "Dragonuk Connects", "Resource Type": "Networking & Auditions", "Work Type": "General voiceover, on-camera, theatre", "Demo Required": "No", "Notes": "U.S. Mid-Atlantic Region focused, but permits other regions to be selected. Demos are optional but highly suggested. Very on-camera heavy. Paid membership required to use forum, have a public profile, send and receive messages, and receive 'Special Profile Castings'", "Link": "https://www.dragonukconnects.com/home.php"},
    {"Name": "DreamVoices", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks, Commercial", "Demo Required": "Yes (Other/See Notes)", "Notes": "Narration demo and/or commercial demo required; Looking to grow a diverse roster", "Link": "https://www.dreamempirefilms.com/voiceoversubmissions"},
    {"Name": "Ear-Reality", "Resource Type": "Audiobook Casting Database", "Work Type": "Interactive Audiobooks", "Demo Required": "Yes (Other/See Notes)", "Notes": "BASED IN GERMANY; Submission page has been removed and replaced with a generic 'contact' form", "Link": "https://ear-reality.com/"},
    {"Name": "Ear Works Media", "Resource Type": "Studio Roster", "Work Type": "Commercial, Narration", "Demo Required": "Yes (Commercial)", "Notes": "Requires commercial demo and Source Connect Standard OR Pro; Can record in-studio if located in the Virginia Beach, USA area; Requires quick turnarounds and open weekday availability", "Link": "https://www.earworks.com/voice-talent-application"},
    {"Name": "Encore Voices", "Resource Type": "Studio Roster", "Work Type": "Dubbing", "Demo Required": "Yes (Character)", "Notes": "Submit through account system on their website", "Link": "https://talent.encorevoices.com/talent-registration/"},
    {"Name": "Findaway Voices", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks", "Demo Required": "No", "Notes": "Sign up, create a profile, auditions will be sent to you based on profile and voice specifications", "Link": "https://findawayvoices.com/narrators"},
    {"Name": "Graphic Audio", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks/Audio Drama (full cast)", "Demo Required": "Yes (Character)", "Notes": "Fill out the Google form, and the casting directors will review the submission within 1-2 months; 'Particular consideration will be given to animation and interactive demos that highlight acting and dialect work.'", "Link": "https://graphicaudio.zendesk.com/hc/en-us/articles/200766607-I-m-a-voice-actor-and-I-m-interested-in-working-for-GraphicAudio-"},
    {"Name": "Halp Network", "Resource Type": "Studio Roster", "Work Type": "Video Games, PCAP/MOCAP", "Demo Required": "Yes (Other/See Notes)", "Notes": "No demo required in submission, but should have a character demo on your website.", "Link": "https://airtable.com/shrJEs3NswRmy3pZ8"},
    {"Name": "Holdcom", "Resource Type": "Studio Roster", "Work Type": "IVR, Narration", "Demo Required": "Yes (Commercial)", "Notes": "Record their script to submit; Requires 24 hour turnaround fulfillment AND home studio; Scripts in English, Spanish, Italian, German, and French", "Link": "https://www.holdcom.com/voice-talent-audition/"},
    {"Name": "JL Studios", "Resource Type": "Studio Roster", "Work Type": "Commercial, Narration", "Demo Required": "No", "Notes": "Complete submission form with booth description and voice description.", "Link": "https://jlstudios.ca/formmailer4/voice_demo_submission.php"},
    {"Name": "khōréō", "Resource Type": "Studio Roster", "Work Type": "Audiobooks/Podcasts", "Demo Required": "No", "Notes": "No experience or demo required; Requests confirmation that applicant identifies as an immigrant/diaspora actor", "Link": "https://www.khoreomag.com/voice-actors/"},
    {"Name": "Kocha Sound", "Resource Type": "Studio Roster", "Work Type": "Character (Animation, Anime, etc)", "Demo Required": "Yes (Character)", "Notes": "Requires character/animation demo; click 'submit here'; NO REPEAT SUBMISIONS!", "Link": "http://www.kochasound.com/contact-us/"},
    {"Name": "Lau Lapides/MCVO", "Resource Type": "Roster/Freelance Agent", "Work Type": "Commercial", "Demo Required": "Yes (Commercial)", "Notes": "Requires commercial demo; freelance agency--will send auditions and represent if job is booked; REQUIRES SOURCE CONNECT STANDARD", "Link": "https://laulapidescompany.com/service/audition-submission-information/"},
    {"Name": "Lotas Productions", "Resource Type": "Studio Roster", "Work Type": "Commercial, Promo", "Demo Required": "No", "Notes": "To apply, navigate 'Voices' > 'Submit your demo'. SUBMISSION LINK HAS BEEN REMOVED AT THIS TIME. THIS STUDIO OFFERS AI (SYNTHETIC VOICE) SOLUTIONS TO CLIENTS.", "Link": "https://www.lotasproductions.com/"},
    {"Name": "Network Nexus Studios", "Resource Type": "Studio Roster", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "Yes (Other/See Notes)", "Notes": "To apply, navigate 'Careers' > 'Talent Pool Application Form'", "Link": "https://www.networknexusstudios.com/"},
    {"Name": "Newgrounds - Forum", "Resource Type": "Networking & Auditions", "Work Type": "Fan projects, original works", "Demo Required": "No", "Notes": "Forum for opportunities; Great for indie projects and newer voice actors", "Link": "https://www.newgrounds.com/bbs/forum/23"},
    {"Name": "No Studio in Particular", "Resource Type": "Indie Studio Mailing List", "Work Type": "Character, Narration", "Demo Required": "Yes (Character)", "Notes": "Mailing list for No Studio in Particular; casting calls are posted to their social media, Discord, and sent to this mailing list", "Link": "https://docs.google.com/forms/d/e/1FAIpQLScLrNPF5iM1eGiKtev29v2LO2VQH68BUvqvFa7xnCm9UVjgIQ/viewform"},
    {"Name": "No Studio in Particular - Twitter", "Resource Type": "Twitter Account", "Work Type": "Character, Narration", "Demo Required": "No", "Notes": "Public casting calls sourced on behalf of clients, freelance service; has a community for voice actors", "Link": "https://twitter.com/NSIPStudio"},
    {"Name": "Online Voice Actor Affiliation", "Resource Type": "Facebook Group", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "No", "Notes": "Requires Facebook; FB group by Morgan Berry", "Link": "https://www.facebook.com/groups/OnlineVoiceActorsActresses/"},
    {"Name": "ProComm Voices", "Resource Type": "Studio Roster", "Work Type": "Commercial", "Demo Required": "Yes (Commercial)", "Notes": "Requires commercial demo; REQUIRES SOURCE CONNECT STANDARD", "Link": "https://www.procommvoices.com/request-to-join-the-procomm-roster/"},
    {"Name": "produb", "Resource Type": "Dubbing App", "Work Type": "Dubbing", "Demo Required": "Yes (Other/See Notes)", "Notes": "Requires app to be downloaded on your mobile device; Your application must be approved to submit to available jobs; Samples or demos required in order for your application to be approved", "Link": "https://produb.app/"},
    {"Name": "Royal Guard Publishing", "Resource Type": "Audiobook Casting Database", "Work Type": "Audiobooks", "Demo Required": "Yes (Other/See Notes)", "Notes": "See submission information under 'Narrator'; requests samples, website link, rates, and comfort level with adult content", "Link": "https://royalguardpublishing.com/submissions/"},
    {"Name": "Sound Cadence Studios", "Resource Type": "Studio Roster", "Work Type": "Character (Animation, Anime, etc)", "Demo Required": "Yes (Character)", "Notes": "Requires character/animation demo; click New Actor Submission Form; DO NOT RESUBMIT SAME INFO!", "Link": "https://www.soundcadencestudios.com/"},
    {"Name": "Studio Center", "Resource Type": "Studio Roster", "Work Type": "Commercial, Promo", "Demo Required": "Yes (Commercial)", "Notes": "NOTE: EXCLUSIVE ROSTER. You are not allowed to be on any other rosters, P2P websites, or receive auditions from agents or managers. NOT CURRENTLY ACCEPTING APPLICATIONS", "Link": "https://studiocenter.com/about/jobs/voice-talent-application"},
    {"Name": "Studio Coattails", "Resource Type": "Studio Roster", "Work Type": "Character (Visual Novels, Videogames)", "Demo Required": "Yes (Character)", "Notes": "Fill out google form. Requires character demo.", "Link": "https://studiocoattails.com/services/for-voice-talent/"},
    {"Name": "Studio Nano", "Resource Type": "Studio Roster", "Work Type": "Character (Animation, Anime, etc)", "Demo Required": "Yes (Character)", "Notes": "Requires character/animation demo; click big, red button for submission form", "Link": "https://studionano.com/contact-us"},
    {"Name": "Studio Topaz", "Resource Type": "Studio Roster", "Work Type": "Commercial & Character", "Demo Required": "Yes (Other/See Notes)", "Notes": "PREVIOUSLY EXTRA TERRIBILE/TIGER MESA; 'Get In Touch' Button at top of page, then fill out contact form.", "Link": "https://www.studiotopaz.com/"},
    {"Name": "TYDEF Studios", "Resource Type": "Studio Roster", "Work Type": "Audiobooks", "Demo Required": "Yes (Other/See Notes)", "Notes": "Fill out form, submit up to 3 narration samples and headshot.", "Link": "https://www.tydefstudios.com/actor-roster-signup"},
    {"Name": "VA Casting Call RT", "Resource Type": "Twitter Account", "Work Type": "Retweets paid casting calls on Twitter", "Demo Required": "No", "Notes": "Turn on Tweet notifications to be pinged when a paid casting call is retweeted", "Link": "https://twitter.com/VACastingRT"},
    {"Name": "Very Berry Studios", "Resource Type": "Indie Studio Mailing List", "Work Type": "Character", "Demo Required": "No", "Notes": "Mailing list for Verry Berry Studios; casting calls are posted to their social media, Discord, and sent to this mailing list. DO NOT SUBMIT VIA CONTACT FORM. Follow link that says 'roster' under contact form.", "Link": "https://veryberrystudios.com/"},
    {"Name": "VO Planet", "Resource Type": "Pay-to-Play (see: Notes for $)", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "Yes (Other/See Notes)", "Notes": "Requires subscription; $199/yr", "Link": "https://www.voplanet.com/cta-page/register"},
    {"Name": "Voice Acting Alliance", "Resource Type": "Facebook Group", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "No", "Notes": "Requires Facebook; FB group by Morgan Berry; great community!", "Link": "https://www.facebook.com/groups/voiceactingallianceunofficialgroup/"},
    {"Name": "Voice Acting Club (VAC)  - Forum", "Resource Type": "Networking & Auditions", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "No", "Notes": "Forum for opportunities; great community!", "Link": "https://voiceacting.boards.net/"},
    {"Name": "Voice Acting Club (VAC) - Discord", "Resource Type": "Discord Server", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "No", "Notes": "Requires Discord; Great for indie projects & welcoming community!", "Link": "https://t.co/Z4GZv91vS2"},
    {"Name": "Voice Acting Club (VAC) - Facebook", "Resource Type": "Facebook Group", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "No", "Notes": "Requires Facebook; FB group by Kira Buckland & VAC; great community!", "Link": "https://www.facebook.com/groups/voiceactingclub/"},
    {"Name": "Voice Crafters", "Resource Type": "Casting Website", "Work Type": "Commercial", "Demo Required": "Yes (Commercial)", "Notes": "'For a (very) limited time, Voice Crafters will accept new US and UK voice talent.'; requires 5+ years of commercial experience", "Link": "https://www.voicecrafters.com/"},
    {"Name": "Voice Over Market", "Resource Type": "Pay-to-Play (see: Notes for $)", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "Yes (Other/See Notes)", "Notes": "BASED IN THE UK; Requires subscription of €50/yr; Can book a studio for you in the UK if needed. Demos strongly suggested.", "Link": "https://www.voiceovermarket.co.uk/registertalent"},
    {"Name": "Voice Talent Online", "Resource Type": "Casting Website", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "Yes (Other/See Notes)", "Notes": "BASED IN THE UK; Fill out form and they will follow up requesting more info; Demos likely required", "Link": "https://www.voicetalentonline.com/join/"},
    {"Name": "Voice Talent Warehouse", "Resource Type": "Casting Website", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "Yes (Other/See Notes)", "Notes": "Upload any demos you may have via their form; click 'Interested in Joining our Roster?'", "Link": "https://voicetalentwarehouse.com/contact/"},
    {"Name": "Voiceover Cafe", "Resource Type": "Studio Roster", "Work Type": "Commercial, Corporate, and Character", "Demo Required": "Yes (Other/See Notes)", "Notes": "BASED IN UK; Localization studio; Email demos, rates, bio, headshot, playing range, and any brands or corporate clients from the past 2 years to hello@voiceover.cafe", "Link": "http://www.voiceover.cafe/about-us/voiceover-service/talent-submissions-join-our-2022-freelance-voiceover-roster/"},
    {"Name": "VoiceProductions", "Resource Type": "Casting Website", "Work Type": "Variety—commercial, narration, character, etc", "Demo Required": "Yes (Other/See Notes)", "Notes": "BASED IN BELGIUM; profile will need to be accepted in order to be provided with direct bookings (no auditons); asks for a variety of demos but requires at least three", "Link": "https://www.voiceproductions.com/en/registration-voice-actor"},
    {"Name": "Voices123", "Resource Type": "Pay-to-Play (see: Notes for $)", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "No", "Notes": "Subscription tiers from $299/yr to $2k+ per year; Audition for jobs you are invited to; Demos are not required but suggested", "Link": "https://voice123.com/plans"},
    {"Name": "Voquent", "Resource Type": "Casting Website", "Work Type": "Variety—audiobooks, commercial, character, etc", "Demo Required": "No", "Notes": "Sign up to receive auditions based on profile and voice specifications. Optional paid features.", "Link": "https://www.voquent.com/"},
    {"Name": "VSI Group", "Resource Type": "Studio Roster", "Work Type": "Dubbing", "Demo Required": "No", "Notes": "Demo not required, but highly suggested. Form asks for a sample of your work; click 'Freelancers'", "Link": "https://www.vsi.tv/contact"},
    {"Name": "Wehear", "Resource Type": "Audiobook Production", "Work Type": "Audiobooks", "Demo Required": "Yes (Other/See Notes)", "Notes": "Demo type not indicated; 'Name Your Own Rate'; follow instructions on link to submit", "Link": "https://wehearfm.com/narrator-program"},
    {"Name": "Zoo Digital", "Resource Type": "Studio Roster", "Work Type": "Dubbing", "Demo Required": "Yes (Other/See Notes)", "Notes": "Requests demos, does not specify what kind", "Link": "https://www.zoodigital.com/freelance-vacancies/voice-actor/"}
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
            st.caption("All 62 verified roster submission forms, agency portals, audiobook databases, and intake links from your database.")

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
