import os
import time
import feedparser
import threading
import requests
import re
import shutil
import random
from datetime import datetime
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import json
from gtts import gTTS

import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# ============================================================
# FIRESTORE
# ============================================================

_firestore_db = None

def get_firestore():
    global _firestore_db
    if _firestore_db is not None:
        return _firestore_db

    firebase_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not firebase_json:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not configured")

    try:
        service_account_info = json.loads(firebase_json)
    except json.JSONDecodeError as e:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON") from e

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(service_account_info))

    _firestore_db = firestore.client()
    return _firestore_db

# ============================================================
# CONFIG
# ============================================================

AUDIO_FOLDER = "static/audio"
XML_FOLDER = "telegram_xml"
ARCHIVE_FOLDER = "archive"

TELEGRAM_CHANNELS = {
    "Pathravarthakal": "https://t.me/s/Pathravarthakal",
    "DailyCa": "https://t.me/s/DailyCAMalayalam",
}

os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(XML_FOLDER, exist_ok=True)
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

# ============================================================
# TELEGRAM FEED
# ============================================================

def archive_feed(xml_path):
    try:
        if not os.path.exists(xml_path):
            return
        month_folder = datetime.now().strftime("%Y-%m")
        archive_dir = os.path.join(ARCHIVE_FOLDER, month_folder)
        os.makedirs(archive_dir, exist_ok=True)
        archive_path = os.path.join(archive_dir, os.path.basename(xml_path))
        shutil.copy2(xml_path, archive_path)
        print("[Feed Archived]", archive_path)
    except Exception as e:
        print("[Archive Error]", e)

def fetch_telegram_xml(name, url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        rss_root = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss_root, "channel")
        ET.SubElement(channel, "title").text = f"{name} Telegram Feed"

        for msg in soup.select(".tgme_widget_message_wrap")[:80]:
            date_tag = msg.select_one("a.tgme_widget_message_date")
            link = date_tag.get("href", url) if date_tag else url
            text_tag = msg.select_one(".tgme_widget_message_text")
            desc_html = text_tag.decode_contents() if text_tag else ""
            clean_text = BeautifulSoup(desc_html, "html.parser").get_text(" ", strip=True)

            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = clean_text[:100]
            ET.SubElement(item, "link").text = link
            ET.SubElement(item, "description").text = clean_text

        xml_path = os.path.join(XML_FOLDER, f"{name}.xml")
        ET.ElementTree(rss_root).write(xml_path, encoding="utf-8", xml_declaration=True)
        archive_feed(xml_path)
        print("[Feed Updated]", name)
    except Exception as e:
        print("[Telegram Error]", name, e)

def telegram_updater():
    while True:
        for name, url in TELEGRAM_CHANNELS.items():
            fetch_telegram_xml(name, url)
        time.sleep(600)

# ============================================================
# AUDIO
# ============================================================

def generate_audio_from_feed(channel_name):
    path = os.path.join(XML_FOLDER, f"{channel_name}.xml")
    if not os.path.exists(path):
        fetch_telegram_xml(channel_name, TELEGRAM_CHANNELS[channel_name])

    feed = feedparser.parse(path)
    entries = list(feed.entries)[-25:]
    full_text = "ഇന്നത്തെ പ്രധാന വാർത്തകൾ.\n\n"

    for entry in entries:
        text = entry.get("description", "")
        text = re.sub(r"[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F\u2600-\u27BF\uFE0F\u200D]", " ", text)
        text = re.sub(r"#\w+|http\S+|@\w+", "", text)
        text = re.sub(r"(join\s*@\w+.*)$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[!?:;]+", ". ", text)
        text = re.sub(r"[\"'(){}\[\]<>]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 5:
            text = entry.get("title", "")
        if text:
            full_text += text + ".\n\n"

    if len(full_text.strip()) < 10:
        full_text = "ഇന്ന് വാർത്തകൾ ലഭ്യമല്ല."

    try:
        output_path = os.path.join(AUDIO_FOLDER, f"{channel_name}.mp3")
        gTTS(full_text, lang="ml").save(output_path)
        print("[Audio Updated]", channel_name)
    except Exception as e:
        print("[TTS Error]", e)

def audio_updater():
    while True:
        for name in TELEGRAM_CHANNELS:
            generate_audio_from_feed(name)
        time.sleep(600)

# ============================================================
# TELEGRAM PAGES
# ============================================================

@app.route("/telegram/<channel_name>")
def telegram_html(channel_name):
    if channel_name not in TELEGRAM_CHANNELS:
        return "Invalid channel", 404

    path = os.path.join(XML_FOLDER, f"{channel_name}.xml")
    if request.args.get("refresh") == "1":
        fetch_telegram_xml(channel_name, TELEGRAM_CHANNELS[channel_name])
    if not os.path.exists(path):
        fetch_telegram_xml(channel_name, TELEGRAM_CHANNELS[channel_name])

    feed = feedparser.parse(path)
    posts = ""
    for entry in list(feed.entries)[::-1][:50]:
        posts += f"<div class='post-card'><p>{entry.get('description','')}</p></div>"

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{font-family:system-ui;background:#f5f7fb;margin:0;padding:16px}}
.header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}}
.btn{{background:linear-gradient(135deg,#00695c,#004d40);color:white;padding:10px 14px;border-radius:12px;text-decoration:none;font-weight:600;box-shadow:0 4px 10px rgba(0,105,92,.3)}}
.post-card{{background:white;padding:14px;border-radius:14px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.05)}}
</style>
</head>
<body>
<div class="header"><h2>{channel_name}</h2><a class="btn" href="?refresh=1">🔄 Refresh</a></div>
{posts}
</body>
</html>
"""

# ============================================================
# ARCHIVES
# ============================================================

@app.route("/archives")
def archives():
    months = sorted(os.listdir(ARCHIVE_FOLDER), reverse=True) if os.path.exists(ARCHIVE_FOLDER) else []
    html = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:system-ui;padding:16px;background:#f5f7fb}.card{background:white;padding:16px;border-radius:16px;margin-bottom:16px;box-shadow:0 4px 12px rgba(0,0,0,.05)}.file{display:block;padding:10px;margin-top:8px;background:#e3f2fd;border-radius:10px;text-decoration:none;color:#1565c0;font-weight:500}</style></head><body><h2>📦 Feed Archives</h2>"""
    if not months:
        html += "<p>No archives found.</p>"
    for month in months:
        month_path = os.path.join(ARCHIVE_FOLDER, month)
        if not os.path.isdir(month_path):
            continue
        html += f"<div class='card'><h3>{month}</h3>"
        for filename in os.listdir(month_path):
            html += f"<a class='file' href='/archive/{month}/{filename}'>{filename}</a>"
        html += "</div>"
    html += "</body></html>"
    return html

@app.route("/archive/<month>/<filename>")
def archive_file(month, filename):
    archive_path = os.path.join(ARCHIVE_FOLDER, month, filename)
    if not os.path.exists(archive_path):
        return "Archive not found", 404
    feed = feedparser.parse(archive_path)
    posts = ""
    for entry in list(feed.entries)[::-1][:100]:
        posts += f"<div class='post'><h3>{entry.get('title','')}</h3><p>{entry.get('description','')}</p><a href='{entry.get('link','#')}' target='_blank'>Open Source</a></div>"
    return f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{{font-family:system-ui;padding:16px;background:#f5f7fb}}.post{{background:white;padding:16px;border-radius:16px;margin-bottom:16px;box-shadow:0 4px 12px rgba(0,0,0,.05)}}</style></head><body><h2>📦 Archive Feed</h2>{posts}</body></html>"""

# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);margin:0;padding:20px;color:#333;text-align:center}
h1{color:white;font-size:28px;margin-bottom:20px}
.section{color:white;font-weight:700;margin:20px 0 10px;font-size:14px;letter-spacing:.5px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.btn{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;font-size:16px;font-weight:700;text-decoration:none;border-radius:18px;background:white;box-shadow:0 8px 20px rgba(0,0,0,.15);transition:.2s}
.btn:active{transform:scale(.97)}
.icon{font-size:28px;margin-bottom:6px}
.audio{color:#1565c0}
.feed{color:#2e7d32}
.archive{color:#ef6c00}
</style>
</head>
<body>
<h1>📰 വാർത്തകൾ</h1>
<div class="section">🎧 AUDIO</div>
<div class="grid">
<a class="btn audio" href="/static/audio/Pathravarthakal.mp3"><div class="icon">🎙️</div>Pathravarthakal</a>
<a class="btn audio" href="/static/audio/DailyCa.mp3"><div class="icon">🎙️</div>Daily CA</a>
</div>
<div class="section">📰 NEWS FEEDS</div>
<div class="grid">
<a class="btn feed" href="/telegram/Pathravarthakal"><div class="icon">📰</div>Pathravarthakal</a>
<a class="btn feed" href="/telegram/DailyCa"><div class="icon">📰</div>Daily CA</a>
</div>
<div class="section">📦 ARCHIVES</div>
<a class="btn archive" href="/archives"><div class="icon">📦</div>Feed Archives</a>
</body>
</html>
"""

# ============================================================
# QUIZ PAGE - ATTRACTIVE UI
# ============================================================
@app.route("/quiz")
def quiz_app():
    firebase_web_config = {
        "apiKey": os.environ.get("FIREBASE_WEB_API_KEY", ""),
        "authDomain": os.environ.get("FIREBASE_WEB_AUTH_DOMAIN", ""),
        "projectId": os.environ.get("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.environ.get("FIREBASE_WEB_APP_ID", "")
    }

    config_json = json.dumps(firebase_web_config)

    html = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CA Blockbuster</title>

<script src="https://www.gstatic.com/firebasejs/11.10.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/11.10.0/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/11.10.0/firebase-firestore-compat.js"></script>

<style>
*{box-sizing:border-box}
:root{
  --bg:#f7f7fb;
  --bg2:#eef2ff;
  --panel:#ffffff;
  --text:#151522;
  --muted:#716f80;
  --line:#e9e3f7;
  --purple:#6756e8;
  --purple2:#7a49ad;
  --soft:#eee7ff;
  --shadow:0 12px 35px rgba(86,65,180,.10);
}
body.dark{
  --bg:#0d1020;
  --bg2:#16172b;
  --panel:#191c2d;
  --text:#f6f5fb;
  --muted:#a9a7b8;
  --line:#2b2e42;
  --soft:#292342;
  --shadow:0 12px 35px rgba(0,0,0,.28);
}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  background:linear-gradient(135deg,var(--bg2),var(--bg));
  margin:0;
  color:var(--text);
  min-height:100vh;
}
button,input{font:inherit}
button{cursor:pointer}
.hidden{display:none!important}

.container{max-width:1180px;margin:auto;padding:18px}
.header{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:24px;
  padding:13px 18px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  box-shadow:var(--shadow);
  position:sticky;
  top:10px;
  z-index:20;
}
.brand{display:flex;align-items:center;gap:12px;min-width:220px}
.brandIcon{
  width:42px;height:42px;border-radius:14px;
  display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,#7659f3,#25a9d8);
  color:white;font-size:20px;
}
.brand h1{margin:0;font-size:16px;line-height:1.1}
.brand p{margin:3px 0 0;font-size:10px;color:var(--muted);letter-spacing:.5px}
.headerRight{display:flex;align-items:center;gap:12px}
.nav{display:flex;align-items:center;gap:10px}
.navBtn{
  border:1px solid var(--line);background:var(--panel);color:var(--text);
  padding:8px 12px;border-radius:14px;font-size:13px;font-weight:700;
  display:flex;align-items:center;justify-content:center;transition:.15s;
}
.navBtn:hover,.navBtn.active{background:var(--soft);color:var(--purple);border-color:#ded3ff}

/* Info / Instructions Top Bar Icon Button */
.infoIconBtn{
  border:1px solid var(--line);background:var(--panel);color:var(--purple);
  width:38px;height:38px;border-radius:50%;font-size:16px;font-weight:800;
  display:flex;align-items:center;justify-content:center;cursor:pointer;
  transition:.15s;box-shadow:var(--shadow);
}
.infoIconBtn:hover{background:var(--soft);border-color:#ded3ff}

/* Small Profile Chip Icon on Top Bar */
.userChip{
  display:flex;align-items:center;gap:8px;
  background:var(--soft);border:1px solid #ded3ff;
  border-radius:22px;padding:4px 8px 4px 4px;
  cursor:pointer;color:var(--text);
}
.userChip:hover{filter:brightness(.98)}
.userAvatar{
  width:32px;height:32px;border-radius:50%;
  background:linear-gradient(135deg,#7259e8,#1aa8d6);
  color:white;display:flex;align-items:center;justify-content:center;
  font-weight:800;overflow:hidden;font-size:12px;
}
.userAvatar img{width:100%;height:100%;object-fit:cover}

.page{padding:28px 6px}
.topLine{display:flex;align-items:center;justify-content:space-between;gap:15px;margin-bottom:20px}
.search{
  max-width:420px;flex:1;position:relative;
}
.search input{
  width:100%;border:1px solid var(--line);background:var(--panel);
  color:var(--text);border-radius:16px;padding:14px 16px 14px 42px;
  outline:none;box-shadow:var(--shadow);
}
.search span{position:absolute;left:15px;top:12px;color:#999;font-size:20px}
.quizCount{color:var(--muted);font-size:14px;white-space:nowrap}

/* Instructions Modal Overlay */
.modalOverlay{
  position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;
  z-index:100;padding:20px;backdrop-filter:blur(4px);
}
.modalBox{
  background:var(--panel);border:1px solid var(--line);
  border-radius:24px;padding:24px;max-width:500px;width:100%;
  box-shadow:0 20px 40px rgba(0,0,0,0.2);animation:modalPopup .2s ease-out;
}
@keyframes modalPopup{
  from{transform:scale(.95);opacity:0}
  to{transform:scale(1);opacity:1}
}
.modalHeader{
  display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;
}
.modalHeader h3{margin:0;font-size:18px;color:var(--purple);display:flex;align-items:center;gap:8px}
.modalCloseBtn{
  background:var(--bg2);border:0;border-radius:50%;width:32px;height:32px;
  font-weight:800;cursor:pointer;color:var(--text);display:flex;align-items:center;justify-content:center;
}
.modalBody{color:var(--muted);font-size:14px;line-height:1.6}
.modalBody ul{margin:0;padding-left:20px}
.modalBody li{margin-bottom:8px}

.quizList{display:flex;flex-direction:column;gap:15px}
.quizCard{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:22px;
  padding:20px 18px;
  display:flex;
  align-items:center;
  gap:18px;
  box-shadow:var(--shadow);
  transition:.18s;
}
.quizCard:hover{transform:translateY(-2px)}
.quizNumber{
  width:72px;height:72px;border-radius:18px;
  background:linear-gradient(135deg,#6754e7,#15a8d4);
  color:white;display:flex;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;flex:0 0 auto;
}
.quizMain{min-width:0;flex:1}
.quizTitleLine{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.quizTitle{font-size:18px;font-weight:800;color:var(--text)}
.statusPill{
  padding:5px 10px;border-radius:999px;
  background:#eee2ff;color:#6234bd;font-size:11px;font-weight:800;
}
.statusPill.completed{
  background:#e7f8ed;color:#145c31;
}
.statusPill.comingsoon{
  background:#fff3cd;color:#856404;
}
.quizDesc{color:var(--muted);font-size:14px;margin-top:8px}
.quizMeta{display:flex;gap:17px;flex-wrap:wrap;margin-top:12px;color:#49445b;font-size:12px;font-weight:700}
body.dark .quizMeta{color:#c0bdce}
.quizActions{display:flex;align-items:center;gap:10px}
.startBtn{
  border:0;border-radius:20px;padding:11px 17px;
  background:#eee3ff;color:#6332c3;font-weight:800;
}
.startBtn:hover{filter:brightness(.96)}
.startBtn.disabled{
  background:#e2dfed;color:#9e9ab8;cursor:not-allowed;
}
.shareBtn{
  border:1px solid var(--line);border-radius:50%;width:42px;height:42px;
  background:var(--panel);color:var(--text);display:flex;align-items:center;justify-content:center;
  font-size:16px;transition:.15s;
}
.shareBtn:hover{background:var(--soft);color:var(--purple);border-color:#ded3ff}
.empty{padding:30px;text-align:center;background:var(--panel);border-radius:18px;color:var(--muted)}

/* Tabs Navigation Style */
.tabsContainer{
  display:flex;
  gap:8px;
  margin-bottom:25px;
  background:var(--panel);
  border:1px solid var(--line);
  padding:6px;
  border-radius:20px;
  box-shadow:var(--shadow);
  overflow-x:auto;
}
.tabBtn{
  flex:1;
  padding:12px 16px;
  border:0;
  background:transparent;
  color:var(--muted);
  font-weight:800;
  font-size:14px;
  border-radius:14px;
  transition:.15s;
  white-space:nowrap;
  text-align:center;
}
.tabBtn:hover{color:var(--purple);background:var(--bg2)}
.tabBtn.active{
  background:linear-gradient(135deg,#6754e7,#15a8d4);
  color:white;
  box-shadow:0 4px 15px rgba(103,84,232,0.3);
}

.sectionHeading{
  font-size:18px;
  font-weight:800;
  color:var(--text);
  margin:25px 0 15px 0;
  display:flex;
  align-items:center;
  gap:8px;
}

/* Profile Tab Design */
.profileScreen{max-width:800px;margin:auto;padding:24px 0}
.profileCard{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:24px;
  padding:30px;
  box-shadow:var(--shadow);
  display:flex;
  flex-direction:column;
  gap:24px;
}
.profileHeaderInfo{
  display:flex;
  align-items:center;
  gap:20px;
}
.profileBigAvatar{
  width:72px;height:72px;border-radius:50%;
  background:linear-gradient(135deg,#7259e8,#1aa8d6);
  color:white;display:flex;align-items:center;justify-content:center;
  font-size:28px;font-weight:900;overflow:hidden;
}
.profileBigAvatar img{width:100%;height:100%;object-fit:cover}
.profileMetaDetails h2{margin:0 0 4px 0;font-size:20px}
.profileMetaDetails p{margin:0;color:var(--muted);font-size:13px}
.profileSettingsList{
  display:flex;
  flex-direction:column;
  gap:12px;
}
.settingRow{
  display:flex;
  justify-content:space-between;
  align-items:center;
  background:var(--bg2);
  padding:16px 20px;
  border-radius:16px;
  font-weight:700;
  font-size:14px;
}
.settingRow button{
  border:0;
  border-radius:12px;
  padding:10px 16px;
  font-weight:800;
  font-size:13px;
}
.themeToggleBtn{
  background:var(--panel);
  color:var(--text);
  border:1px solid var(--line)!important;
}
.logoutActionBtn{
  background:#fff0f2;
  color:#d84f62;
}

.visitor{
  margin-top:18px;text-align:center;color:var(--muted);font-size:13px;
}
.visitor b{color:var(--text)}

.quizScreen,.resultScreen{max-width:1180px;margin:auto;padding:24px 0}
.backBtn{
  border:0;background:var(--panel);color:var(--text);
  padding:10px 14px;border-radius:13px;border:1px solid var(--line);
}
.card{
  background:var(--panel);border:1px solid var(--line);
  border-radius:20px;padding:20px;box-shadow:var(--shadow);
}
.question{font-size:20px;font-weight:800;line-height:1.5}
.option{
  background:var(--panel);border:2px solid var(--line);color:var(--text);
  padding:15px;margin:11px 0;border-radius:14px;cursor:pointer;
}
.option.correct{background:#e7f8ed;border-color:#3bad69;color:#145c31}
.option.wrong{background:#ffe8eb;border-color:#df596a;color:#842b38}
body.dark .option.correct{background:#183b29;color:#9ce8b6}
body.dark .option.wrong{background:#45262c;color:#ffabb5}
.quizTop{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}
.timer{font-weight:800;color:#e45769}
.nextBtn{
  border:0;border-radius:13px;padding:12px 18px;
  background:linear-gradient(135deg,#6655e8,#7047aa);color:white;font-weight:800;
}

.resultHero{text-align:center}
.score{font-size:52px;font-weight:900;color:var(--purple)}
.resultGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}
.resultStat{background:var(--bg2);border-radius:14px;padding:14px;text-align:center}
.resultStat .v{font-size:22px;font-weight:900}
.resultStat .l{font-size:10px;color:var(--muted);margin-top:3px}
.reviewItem{padding:12px;border-radius:14px;margin:9px 0;background:var(--bg2)}
.reviewItem.correct{border-left:5px solid #3bb76e}
.reviewItem.wrong{border-left:5px solid #e85e6e}

.loginPage{
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px;
  background:linear-gradient(135deg,#e9e7ff,#f8f8fc);
}
.loginBox{
  width:100%;max-width:500px;background:white;border-radius:24px;
  overflow:hidden;border:1px solid #ddd8f0;box-shadow:0 18px 50px rgba(72,55,145,.18);
}
.loginHead{
  padding:28px 20px 18px;text-align:center;
  background:linear-gradient(135deg,#6675e7,#7848a8);color:white;
}
.loginLogo{
  width:50px;height:50px;border-radius:50%;margin:auto auto 12px;
  background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;
  font-size:24px;
}
.loginHead h1{font-size:23px;margin:0 0 4px}
.loginHead p{margin:0;font-size:14px;opacity:.9}
.loginBody{padding:22px}
.google{
  width:100%;border:1px solid #ddd;border-radius:12px;
  padding:14px;background:white;color:#222;font-weight:600;
  display:flex;align-items:center;justify-content:center;gap:10px;
  font-size:15px;
}
.google:hover{background:#f8f9fa}
.google svg{width:20px;height:20px}
.loginError{background:#fff0f2;color:#a32e40;padding:10px;border-radius:10px;font-size:12px;margin-bottom:12px}
.loading{text-align:center;color:#777;padding:30px}

@media(max-width:800px){
  .brand{min-width:0;flex:1}
  .userName{display:none}
}
@media(max-width:650px){
  .container{padding:10px}
  .header{position:relative;top:0;padding:10px 12px}
  .topLine{align-items:stretch;flex-direction:column}
  .search{max-width:none}
  .quizCard{align-items:flex-start}
  .quizNumber{width:58px;height:58px;font-size:18px}
  .quizTitle{font-size:16px}
  .quizDesc{font-size:12px}
  .quizActions{flex-direction:column}
  .startBtn{padding:9px 14px}
  .resultGrid{grid-template-columns:repeat(2,1fr)}
}
@media(max-width:430px){
  .quizCard{display:grid;grid-template-columns:58px 1fr}
  .quizActions{grid-column:1 / -1;flex-direction:row;justify-content:flex-end}
}
</style>
</head>

<body>

<div id="loginPage" class="loginPage">
  <div class="loginBox">
    <div class="loginHead">
      <div class="loginLogo">🎓</div>
      <h1>CA Blockbuster</h1>
      <p>Welcome back</p>
    </div>
    <div class="loginBody">
      <div id="loginError" class="loginError hidden"></div>

      <button class="google" id="googleButton" type="button">
        <svg viewBox="0 0 24 24">
          <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"/>
          <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.19v3.15C3.17 21.32 7.23 24 12 24z"/>
          <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.19C.43 8.1 0 9.8 0 12s.43 3.9 1.19 5.42l4.09-3.15z"/>
          <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.23 0 3.17 2.68 1.19 6.58l4.09 3.15c.95-2.83 3.6-4.98 6.72-4.98z"/>
        </svg>
        Continue with Google
      </button>
    </div>
  </div>
</div>

<div id="appPage" class="hidden">
  <div class="container">

    <header class="header">
      <div class="brand">
        <div class="brandIcon">🎓</div>
      </div>

      <div class="headerRight">
        <nav class="nav">
          <button class="navBtn active" id="homeNav" type="button" title="Home">🏠</button>
        </nav>
        <button class="infoIconBtn" id="infoModalBtn" title="Instructions to Candidates">ℹ</button>
        <div class="userChip" id="topProfileChip" title="Go to Profile">
          <div class="userAvatar" id="userAvatar">S</div>
        </div>
      </div>
    </header>

    <!-- Instructions Modal Popup -->
    <div id="instructionsModal" class="modalOverlay hidden">
      <div class="modalBox">
        <div class="modalHeader">
          <h3>📌 Instruction to Candidates</h3>
          <button class="modalCloseBtn" id="modalCloseBtn">✕</button>
        </div>
        <div class="modalBody">
          <ul>
            <li>All questions must be answered completely before submitting the quiz.</li>
            <li>Quizzes are timed at <b>30 seconds per question</b> (e.g., 5 minutes for 10 questions).</li>
            <li>Quizzes marked as <b>"Preparing"</b> are currently being updated by the admin and will unlock once fully compiled.</li>
            <li>Scores and points are added <b>only from fresh attempts on uncompleted tests ("Not started")</b>. Once marked as <b>"Completed"</b>, re-attempting practices questions without adding extra points.</li>
          </ul>
        </div>
      </div>
    </div>

    <main id="homePage" class="page">
      <!-- Tabs Navigation Bar -->
      <div class="tabsContainer">
        <button class="tabBtn active" onclick="switchTab('daily')">⚡ Daily</button>
        <button class="tabBtn" onclick="switchTab('weekly')">📆 Weekly</button>
        <button class="tabBtn" onclick="switchTab('monthly')">📅 Monthly</button>
      </div>

      <!-- Quizzes List Header -->
      <div class="sectionHeading" id="quizListHeading">⚡ Daily CA Quizzes</div>
      <div class="topLine">
        <div class="search">
          <span>⌕</span>
          <input id="searchInput" type="search" placeholder="Search quizzes...">
        </div>
        <div class="quizCount" id="quizCount">0 quizzes</div>
      </div>

      <div id="quizList" class="quizList">
        <div class="loading">Loading quizzes...</div>
      </div>

      <div class="visitor" id="visitorCount">👥 Today: <b>0</b> visitors</div>
    </main>

    <!-- Profile Tab Screen -->
    <section id="profilePage" class="profileScreen hidden">
      <div class="profileCard">
        <div class="profileHeaderInfo">
          <div class="profileBigAvatar" id="profileBigAvatar">S</div>
          <div class="profileMetaDetails">
            <h2 id="profileNameDisplay">Aspirant</h2>
            <p id="profileEmailDisplay">aspirant@example.com</p>
          </div>
        </div>
        <div class="profileSettingsList">
          <div class="settingRow">
            <span>Appearance (Dark Mode)</span>
            <button class="settingRowBtn themeToggleBtn" id="profileThemeToggle" type="button">☼ Toggle</button>
          </div>
          <div class="settingRow">
            <span>Account Session</span>
            <button class="settingRowBtn logoutActionBtn" id="profileLogoutBtn" type="button">Sign Out</button>
          </div>
        </div>
      </div>
    </section>

    <section id="quizPage" class="quizScreen hidden">
      <div class="quizTop">
        <button class="backBtn" id="quizBack">✕ Exit Quiz</button>
        <span class="timer" id="timer">⏱ 00:00</span>
      </div>
      <h2 id="testTitle"></h2>
      <div id="questionNumber" style="color:var(--muted);margin-bottom:12px"></div>
      <div class="card"><div id="questionText" class="question">Loading...</div></div>
      <div id="options"></div>
      <div id="explanationCard" class="card hidden"><b>Explanation</b><div id="explanation"></div></div>
      <div style="text-align:right;margin-top:12px">
        <button class="nextBtn" id="nextButton">Next →</button>
      </div>
    </section>

    <section id="resultPage" class="resultScreen hidden">
      <button class="backBtn" id="resultHome">← Back to quizzes</button>
      <div class="card" style="margin-top:15px">
        <div class="resultHero">
          <h2>🎉 Result</h2>
          <div id="scoreText" class="score">0 / 0</div>
          <div id="gradeText"></div>
        </div>
        <div class="resultGrid">
          <div class="resultStat"><div id="correctStat" class="v">0</div><div class="l">Correct</div></div>
          <div class="resultStat"><div id="wrongStat" class="v">0</div><div class="l">Wrong</div></div>
          <div class="resultStat"><div id="pointsStat" class="v">0</div><div class="l">Points</div></div>
          <div class="resultStat"><div id="accuracyStat" class="v">0%</div><div class="l">Accuracy</div></div>
        </div>
        <div id="performanceText" style="text-align:center;color:var(--muted)"></div>
        <div id="review" style="margin-top:15px"></div>
      </div>
    </section>

  </div>
</div>

<script>
"use strict";

const FIREBASE_CONFIG = __FIREBASE_CONFIG__;
let firebaseReady = false;

try{
  if(FIREBASE_CONFIG.apiKey && FIREBASE_CONFIG.projectId){
    firebase.initializeApp(FIREBASE_CONFIG);
    firebaseReady = true;
  }
}catch(e){
  console.error("Firebase initialization failed:",e);
}

const $ = id => document.getElementById(id);

let allTests = [];
let filteredTests = [];
let currentQuestions = [];
let selectedTest = null;
let currentQuestion = 0;
let score = 0;
let correctCount = 0;
let wrongCount = 0;
let questionResults = [];
let answered = false;
let timerSeconds = 0;
let elapsedSeconds = 0;
let timerInterval = null;
let currentTab = 'daily';

function getUserStorageKey(){
  const user = firebase.auth().currentUser;
  return user ? "ca_stats_" + user.uid : "ca_stats_guest";
}

function loadUserStats(){
  try{
    const raw = localStorage.getItem(getUserStorageKey());
    if(raw) return JSON.parse(raw);
  }catch(e){}
  return { attempts: [], bestStars: {}, bestScores: {} };
}

function saveUserStats(stats){
  try{
    localStorage.setItem(getUserStorageKey(), JSON.stringify(stats));
  }catch(e){}
}

function esc(value){
  return String(value ?? "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;")
    .replace(/'/g,"&#039;");
}

async function apiGet(url){
  const response = await fetch(url,{headers:{Accept:"application/json"}});
  let data;
  try{data=await response.json();}
  catch(e){throw new Error("Server returned invalid JSON.");}
  if(!response.ok) throw new Error(data.error || "Server error: "+response.status);
  return data;
}

function showError(message){
  $("loginError").textContent = message;
  $("loginError").classList.remove("hidden");
}
function clearError(){ $("loginError").classList.add("hidden"); }

async function googleLogin(){
  clearError();
  if(!firebaseReady){showError("Firebase Authentication is not configured.");return;}

  try{
    const provider = new firebase.auth.GoogleAuthProvider();
    await firebase.auth().signInWithPopup(provider);
  }catch(error){
    showError(authError(error));
  }
}

function authError(error){
  const code=error && error.code ? error.code : "";
  const messages={
    "auth/popup-closed-by-user":"Google sign-in was cancelled.",
    "auth/popup-blocked":"Please allow pop-ups for Google sign-in.",
    "auth/too-many-requests":"Too many attempts. Please try again later."
  };
  return messages[code] || error.message || "Authentication failed.";
}

function updateUserUI(user){
  if(!user)return;
  const name = user.displayName || user.email?.split("@")[0] || "Aspirant";
  const email = user.email || "";

  $("profileNameDisplay").textContent = name;
  $("profileEmailDisplay").textContent = email;

  if(user.photoURL){
    $("userAvatar").innerHTML='<img src="'+esc(user.photoURL)+'" alt="">';
    $("profileBigAvatar").innerHTML='<img src="'+esc(user.photoURL)+'" alt="">';
  }else{
    $("userAvatar").textContent = name.charAt(0).toUpperCase();
    $("profileBigAvatar").textContent = name.charAt(0).toUpperCase();
  }
}

function showApp(){
  $("loginPage").classList.add("hidden");
  $("appPage").classList.remove("hidden");
  showHome();
  loadData();
  loadVisitorCount();
}

function showLogin(){
  $("appPage").classList.add("hidden");
  $("loginPage").classList.remove("hidden");
}

if(firebaseReady){
  firebase.auth().onAuthStateChanged(user=>{
    if(user){
      updateUserUI(user);
      showApp();
    }else{
      showLogin();
    }
  });
}else{
  showLogin();
  showError("Firebase Authentication is not configured. Add the Firebase Web environment variables in Koyeb.");
}

async function loadData(){
  $("quizList").innerHTML='<div class="loading">Loading quizzes...</div>';
  try{
    allTests=await apiGet("/quiz/api/tests");
    if(!Array.isArray(allTests))throw new Error("Invalid test data.");
    switchTab(currentTab);
  }catch(error){
    $("quizList").innerHTML='<div class="empty">'+esc(error.message)+'</div>';
  }
}

function renderTests(tests){
  filteredTests=tests;
  $("quizCount").textContent=tests.length+" quizzes";

  if(!tests.length){
    $("quizList").innerHTML='<div class="empty">No quizzes found for this tab.</div>';
    return;
  }

  const userStats = loadUserStats();
  const attemptedTestIds = new Set(Object.keys(userStats.bestScores || {}));

  $("quizList").innerHTML="";
  tests.forEach((test,index)=>{
    const card=document.createElement("div");
    card.className="quizCard";

    const number=String(index+1).padStart(2,"0");
    const title=test.title || test.id || "Quiz";
    const description=test.subtitle || "Self-paced MCQ practice with instant results after you submit.";
    const questions=Number(test.questionCount||0);
    const duration = Math.max(1, Math.ceil((questions * 30) / 60));
    const difficulty=test.difficulty || "Practice";
    const topicId=String(test.topicId || "").toLowerCase();
    const titleLower = title.toLowerCase();
    const subtitleLower = String(test.subtitle || "").toLowerCase();
    
    const isPyqOrMock = titleLower.includes("pyq") || subtitleLower.includes("pyq") || 
                       titleLower.includes("mock") || subtitleLower.includes("mock") || 
                       topicId.includes("pyq") || topicId.includes("mock");

    const isMonthly = topicId.includes("monthly") || titleLower.includes("monthly");
    const requiredThreshold = isMonthly ? 20 : 10;
    
    const isPreparing = !isPyqOrMock && (questions < requiredThreshold);
    const isCompleted = attemptedTestIds.has(test.id);
    
    let statusBadgeHtml = '<span class="statusPill">Not started</span>';
    if(isPreparing){
      statusBadgeHtml = `<span class="statusPill comingsoon">Preparing (${questions}/${requiredThreshold} qns)</span>`;
    }else if(isCompleted){
      statusBadgeHtml = '<span class="statusPill completed">Completed ✓</span>';
    }

    card.innerHTML=
      '<div class="quizNumber">'+number+'</div>'+
      '<div class="quizMain">'+
        '<div class="quizTitleLine">'+
          '<div class="quizTitle">'+esc(title)+'</div>'+
          statusBadgeHtml+
        '</div>'+
        '<div class="quizDesc">'+esc(description)+'</div>'+
        '<div class="quizMeta">'+
          '<span>❓ '+questions+(isPyqOrMock ? ' questions' : ' / '+requiredThreshold+' questions')+'</span>'+
          '<span>👥 '+esc(difficulty)+'</span>'+
          '<span>⏱ '+duration+' min</span>'+
        '</div>'+
      '</div>'+
      '<div class="quizActions">'+
        '<button class="shareBtn" title="Share Quiz">🔗</button>'+
        '<button class="startBtn '+(isPreparing ? 'disabled' : '')+'">'+(isPreparing ? 'Soon' : 'Start →')+'</button>'+
      '</div>';

    const startBtn = card.querySelector(".startBtn");
    if(isPreparing){
      startBtn.addEventListener("click",()=>{
        alert(`This quiz is currently being compiled (${questions} of ${requiredThreshold} questions added). Please check back when complete!`);
      });
    }else{
      startBtn.addEventListener("click",()=>startQuiz(test));
    }

    card.querySelector(".shareBtn").addEventListener("click",()=>{
      const shareText = `Check out this quiz: ${title} - ${description} on CA Blockbuster!`;
      if(navigator.share){
        navigator.share({title: title, text: shareText, url: window.location.href}).catch(()=>{});
      }else{
        navigator.clipboard.writeText(window.location.href);
        alert("Quiz link copied to clipboard!");
      }
    });

    $("quizList").appendChild(card);
  });
}

$("searchInput").addEventListener("input",()=>{
  const q=$("searchInput").value.trim().toLowerCase();
  const filtered=filteredTests.filter(t=>
    String(t.title||"").toLowerCase().includes(q) ||
    String(t.subtitle||"").toLowerCase().includes(q) ||
    String(t.topicId||"").toLowerCase().includes(q)
  );
  $("quizCount").textContent=filtered.length+" quizzes";
  if(!filtered.length){
    $("quizList").innerHTML='<div class="empty">No matching quizzes found.</div>';
  }else{
    renderTests(filtered);
  }
});

function hidePages(){
  $("homePage").classList.add("hidden");
  $("profilePage").classList.add("hidden");
  $("quizPage").classList.add("hidden");
  $("resultPage").classList.add("hidden");
  
  $("homeNav").classList.remove("active");
}

function showHome(){
  clearInterval(timerInterval);
  hidePages();
  $("homePage").classList.remove("hidden");
  $("homeNav").classList.add("active");
  switchTab(currentTab);
}

function showProfile(){
  clearInterval(timerInterval);
  hidePages();
  $("profilePage").classList.remove("hidden");
}

function switchTab(tabKey){
  currentTab = tabKey;
  
  const buttons = document.querySelectorAll('.tabsContainer .tabBtn');
  buttons.forEach(btn => btn.classList.remove('active'));
  
  if(tabKey === 'daily'){
    buttons[0].classList.add('active');
    $("quizListHeading").textContent = "⚡ Daily CA Quizzes";
    renderTests(allTests.filter(t => !String(t.topicId||"").toLowerCase().includes('weekly') && !String(t.topicId||"").toLowerCase().includes('monthly')));
  } else if(tabKey === 'weekly'){
    buttons[1].classList.add('active');
    $("quizListHeading").textContent = "📆 Weekly Revision Quizzes";
    const weeklyTests = [
      { id: "weekly_aug_w1", topicId: "weekly", title: "August 2026 - Week 1 Revision", subtitle: "Shuffled weekly review test (10 Questions)", difficulty: "Medium", durationMinutes: 5, questionCount: 10 },
      { id: "weekly_aug_w2", topicId: "weekly", title: "August 2026 - Week 2 Revision", subtitle: "Shuffled weekly review test (10 Questions)", difficulty: "Medium", durationMinutes: 5, questionCount: 10 }
    ];
    renderTests(weeklyTests);
  } else if(tabKey === 'monthly'){
    buttons[2].classList.add('active');
    $("quizListHeading").textContent = "📅 Monthly Wise Quizzes";
    const monthlyTests = allTests.filter(t => {
      const tid = String(t.topicId || "").toLowerCase();
      const ttl = String(t.title || "").toLowerCase();
      const sub = String(t.subtitle || "").toLowerCase();
      return tid.includes('monthly') || ttl.includes('monthly') || sub.includes('monthly');
    });
    renderTests(monthlyTests);
  }
}

async function startQuiz(test){
  selectedTest=test;
  hidePages();
  $("quizPage").classList.remove("hidden");
  $("testTitle").textContent=test.title||test.id;
  $("questionText").textContent="Loading questions...";
  $("options").innerHTML="";

  try{
    currentQuestions=await apiGet("/quiz/api/questions/"+encodeURIComponent(test.id));
    if(!Array.isArray(currentQuestions)||!currentQuestions.length)
      throw new Error("No questions found.");

    currentQuestion=0;
    score=0;
    correctCount=0;
    wrongCount=0;
    questionResults=new Array(currentQuestions.length).fill(null);
    answered=false;

    const dynamicMinutes = (currentQuestions.length * 30) / 60;
    startTimer(dynamicMinutes);
    displayQuestion();
  }catch(error){
    $("questionText").textContent="";
    $("options").innerHTML='<div class="empty">'+esc(error.message)+'</div>';
  }
}

function displayQuestion(){
  const q=currentQuestions[currentQuestion];
  if(!q){finishQuiz();return;}

  answered = questionResults[currentQuestion] !== undefined && questionResults[currentQuestion] !== null;
  
  $("questionNumber").textContent="Question "+(currentQuestion+1)+" / "+currentQuestions.length;
  $("questionText").textContent=q.questionText||"";
  
  if(answered && questionResults[currentQuestion]){
    $("explanation").textContent=q.explanation || "";
    if(q.explanation) $("explanationCard").classList.remove("hidden");
    else $("explanationCard").classList.add("hidden");
  } else {
    $("explanationCard").classList.add("hidden");
  }

  $("nextButton").textContent=currentQuestion===currentQuestions.length-1?"Finish ✓":"Next →";

  const options=$("options");
  options.innerHTML="";
  [q.option0||"",q.option1||"",q.option2||"",q.option3||""].forEach((option,index)=>{
    const div=document.createElement("div");
    div.className="option";
    
    if(answered && questionResults[currentQuestion]){
      const res = questionResults[currentQuestion];
      if(index === res.correct) div.classList.add("correct");
      else if(index === res.selected && !res.isCorrect) div.classList.add("wrong");
    }

    div.textContent=option;
    div.addEventListener("click",()=>selectAnswer(index,div));
    options.appendChild(div);
  });
}

function selectAnswer(index,element){
  if(answered)return;
  answered=true;

  const q=currentQuestions[currentQuestion];
  const correct=Number(q.correctOptionIndex);
  const options=document.querySelectorAll(".option");
  const isCorrect=index===correct;

  if(isCorrect){
    element.classList.add("correct");
    correctCount++;
  }else{
    element.classList.add("wrong");
    wrongCount++;
    if(options[correct])options[correct].classList.add("correct");
  }

  questionResults[currentQuestion]={
    question:q.questionText||"",
    selected:index,
    correct:correct,
    isCorrect:isCorrect,
    explanation:q.explanation||"",
    selectedText:[q.option0,q.option1,q.option2,q.option3][index]||"",
    correctText:[q.option0,q.option1,q.option2,q.option3][correct]||""
  };

  if(q.explanation){
    $("explanation").textContent=q.explanation;
    $("explanationCard").classList.remove("hidden");
  }
}

function nextQuestion(){
  const q=currentQuestions[currentQuestion];
  if(!answered && (!questionResults[currentQuestion])) {
    alert("Please select an answer before proceeding.");
    return;
  }

  if(currentQuestion>=currentQuestions.length-1){
    const totalQ = currentQuestions.length;
    const answeredQ = questionResults.filter(r => r !== null && r !== undefined).length;
    
    if(answeredQ < totalQ){
      alert("You must answer all " + totalQ + " questions before finishing the test! You have answered " + answeredQ + " so far.");
      return;
    }
    
    finishQuiz();
    return;
  }
  currentQuestion++;
  displayQuestion();
}

function startTimer(minutes){
  clearInterval(timerInterval);
  const limit=Number(minutes)>0;
  timerSeconds=limit?Number(minutes)*60:0;
  elapsedSeconds=0;
  updateTimer();

  timerInterval=setInterval(()=>{
    elapsedSeconds++;
    if(limit){
      timerSeconds--;
      updateTimer();
      if(timerSeconds<=0){
        clearInterval(timerInterval);
        finishQuiz(true);
      }
    }else{
      timerSeconds++;
      updateTimer();
    }
  },1000);
}

function updateTimer(){
  const min=Math.floor(timerSeconds/60);
  const sec=timerSeconds%60;
  $("timer").textContent="⏱ "+String(min).padStart(2,"0")+":"+String(sec).padStart(2,"0");
}

function finishQuiz(timeExpired=false){
  clearInterval(timerInterval);
  const total=currentQuestions.length;
  if(!total)return;

  const answeredQ = questionResults.filter(r => r !== null && r !== undefined).length;
  if(answeredQ < total && !timeExpired) {
    alert("Cannot submit incomplete test. Please complete all questions.");
    return;
  }

  for(let i=0; i<total; i++){
    if(!questionResults[i]){
      const q = currentQuestions[i];
      questionResults[i] = {
        question: q.questionText || "",
        selected: null,
        correct: Number(q.correctOptionIndex),
        isCorrect: false,
        unanswered: true,
        explanation: q.explanation || "",
        selectedText: "Not started",
        correctText: [q.option0, q.option1, q.option2, q.option3][Number(q.correctOptionIndex)] || ""
      };
      wrongCount++;
    }
  }

  const accuracyPct = (correctCount / total) * 100;

  let starsEarned = 0;
  if(accuracyPct >= 90){
    starsEarned = 3;
  }else if(accuracyPct >= 60){
    starsEarned = 2;
  }else if(accuracyPct >= 40){
    starsEarned = 1;
  }

  const userStats = loadUserStats();
  const testId = selectedTest ? (selectedTest.id || "default") : "default";

  const alreadyCompleted = userStats.bestScores && userStats.bestScores[testId];

  if(!alreadyCompleted){
    if(!userStats.bestScores) userStats.bestScores = {};
    if(!userStats.bestStars) userStats.bestStars = {};

    userStats.bestScores[testId] = {
      correctCount,
      totalQuestions: total,
      accuracyPct,
      starsEarned,
      timestamp: Date.now()
    };
    userStats.bestStars[testId] = starsEarned;
    saveUserStats(userStats);
  }

  $("scoreText").textContent = correctCount + " / " + total;
  $("gradeText").textContent = starsEarned === 3 ? "⭐⭐⭐" : starsEarned === 2 ? "⭐⭐" : starsEarned === 1 ? "⭐" : "❌";
  $("correctStat").textContent = correctCount;
  $("wrongStat").textContent = wrongCount;
  $("pointsStat").textContent = correctCount * 10;
  $("accuracyStat").textContent = Math.round(accuracyPct) + "%";

  $("performanceText").innerHTML =
    "<b>" + Math.round(accuracyPct) + "% accuracy</b> • " +
    (alreadyCompleted ? "Re-attempt (Score locked to initial completion)" : "Completed for the first time");

  renderReview();
  hidePages();
  $("resultPage").classList.remove("hidden");
}

function renderReview(){
  const container=$("review");
  container.innerHTML="<h3>📋 Answer Review</h3>";

  questionResults.forEach((r,i)=>{
    if(!r)return;
    const cls=r.unanswered?"unanswered":(r.isCorrect?"correct":"wrong");
    const icon=r.unanswered?"🟡":(r.isCorrect?"✅":"❌");

    container.innerHTML+=
      '<div class="reviewItem '+cls+'">'+
      '<b>'+icon+' Q'+(i+1)+'. '+esc(r.question)+'</b>'+
      '<div style="font-size:12px;color:var(--muted);margin-top:5px">Your answer: '+esc(r.selectedText)+'</div>'+
      '<div style="font-size:12px;color:var(--muted);margin-top:3px">Correct answer: '+esc(r.correctText)+'</div>'+
      (r.explanation?'<div style="font-size:12px;color:var(--muted);margin-top:3px">💡 '+esc(r.explanation)+'</div>':'')+
      '</div>';
  });
}

async function loadVisitorCount(){
  try{
    const key="ca_blockbuster_visited_"+new Date().toISOString().slice(0,10);

    if(!localStorage.getItem(key)){
      const response=await fetch("/quiz/api/visit",{
        method:"POST",
        headers:{"Accept":"application/json"}
      });
      if(response.ok)localStorage.setItem(key,"1");
    }

    const data=await apiGet("/quiz/api/visitors");
    $("visitorCount").innerHTML="👥 Today: <b>"+Number(data.count||0)+"</b> visitors";
  }catch(error){
    console.error("[Visitor Counter]",error);
  }
}

// Modal Toggle Handlers for Instructions Icon
$("infoModalBtn").addEventListener("click",()=>{
  $("instructionsModal").classList.remove("hidden");
});
$("modalCloseBtn").addEventListener("click",()=>{
  $("instructionsModal").classList.add("hidden");
});
$("instructionsModal").addEventListener("click",(e)=>{
  if(e.target === $("instructionsModal")){
    $("instructionsModal").classList.add("hidden");
  }
});

$("googleButton").addEventListener("click",googleLogin);

$("homeNav").addEventListener("click",showHome);
$("topProfileChip").addEventListener("click",showProfile);
$("quizBack").addEventListener("click",()=>{
  if(confirm("Exit this quiz? Your progress will be lost.")){
    showHome();
  }
});
$("resultHome").addEventListener("click",showHome);
$("nextButton").addEventListener("click",nextQuestion);

$("profileThemeToggle").addEventListener("click",()=>{
  document.body.classList.toggle("dark");
  const dark=document.body.classList.contains("dark");
  localStorage.setItem("ca_theme",dark?"dark":"light");
  $("profileThemeToggle").textContent = dark ? "☀ Toggle" : "☽ Toggle";
});

$("profileLogoutBtn").addEventListener("click",async()=>{
  if(firebaseReady)await firebase.auth().signOut();
});

if(localStorage.getItem("ca_theme")==="dark"){
  document.body.classList.add("dark");
  $("profileThemeToggle").textContent = "☀ Toggle";
}else{
  $("profileThemeToggle").textContent = "☽ Toggle";
}
</script>
</body>
</html>
"""

    html = html.replace("__FIREBASE_CONFIG__", config_json)
    return html


# ============================================================
# DAILY VISITOR COUNTER
# ============================================================

@app.route("/quiz/api/visit", methods=["POST"])
def quiz_visit():
    try:
        db = get_firestore()

        today = datetime.now().strftime("%Y-%m-%d")
        doc_ref = db.collection("daily_visitors").document(today)
        transaction = db.transaction()

        @firestore.transactional
        def update_visitor_count(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                data = snapshot.to_dict() or {}
                count = int(data.get("count", 0) or 0) + 1
                transaction.update(doc_ref, {
                    "count": count,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
            else:
                count = 1
                transaction.set(doc_ref, {
                    "date": today,
                    "count": count,
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
            return count

        count = update_visitor_count(transaction, doc_ref)
        return jsonify({"success": True, "count": count})

    except Exception as e:
        print("[Visitor Counter Error]", e)
        return jsonify({"error": str(e)}), 500


@app.route("/quiz/api/visitors")
def quiz_visitors():
    try:
        db = get_firestore()
        today = datetime.now().strftime("%Y-%m-%d")
        doc = db.collection("daily_visitors").document(today).get()

        count = 0
        if doc.exists:
            data = doc.to_dict() or {}
            count = int(data.get("count", 0) or 0)

        return jsonify({"date": today, "count": count})

    except Exception as e:
        print("[Visitor Count Error]", e)
        return jsonify({"error": str(e)}), 500


# ============================================================
# QUIZ FIRESTORE API
# ============================================================

@app.route("/quiz/api/tests")
def quiz_tests():
    try:
        db = get_firestore()
        tests = []
        for doc in db.collection("custom_tests").stream():
            data = doc.to_dict()
            # If timestamp field in Firestore is used, we can read it directly
            tests.append({
                "id": data.get("id") or doc.id,
                "topicId": data.get("topicId") or "",
                "title": data.get("title") or "",
                "subtitle": data.get("subtitle") or "",
                "durationMinutes": data.get("durationMinutes") or 0,
                "difficulty": data.get("difficulty") or "",
                "dateMillis": data.get("dateMillis") or data.get("timestamp") or 0,
                "questionCount": 0,
            })
        question_counts = {}
        for doc in db.collection("custom_questions").stream():
            data = doc.to_dict()
            test_id = data.get("testId")
            if test_id:
                question_counts[test_id] = question_counts.get(test_id, 0) + 1
        for test in tests:
            test["questionCount"] = question_counts.get(test["id"], 0)

        # Sort strictly using the numeric value of timestamp (or dateMillis) in ascending order:
        # Aug 4 (1786962194141) -> Aug 5 (1786962194268) -> Aug 6 (1786962194440)
        tests.sort(key=lambda t: int(t.get("dateMillis") or 0), reverse=False)

        return jsonify(tests)
    except Exception as e:
        print("[Quiz Firestore tests error]", e)
        return jsonify({"error": str(e)}), 500

@app.route("/quiz/api/questions/<path:test_id>")
def quiz_questions(test_id):
    try:
        db = get_firestore()
        questions = []
        
        if "weekly" in str(test_id).lower():
            all_q_docs = db.collection("custom_questions").stream()
            for doc in all_q_docs:
                data = doc.to_dict()
                questions.append({
                    "id": data.get("id") or doc.id,
                    "testId": data.get("testId") or "",
                    "topicId": data.get("topicId") or "",
                    "questionText": data.get("questionText") or "",
                    "option0": data.get("option0") or "",
                    "option1": data.get("option1") or "",
                    "option2": data.get("option2") or "",
                    "option3": data.get("option3") or "",
                    "correctOptionIndex": data.get("correctOptionIndex", 0),
                    "explanation": data.get("explanation") or "",
                    "hint": data.get("hint") or "",
                })
            random.shuffle(questions)
            questions = questions[:10]
        else:
            docs = db.collection("custom_questions").where("testId", "==", test_id).stream()
            for doc in docs:
                data = doc.to_dict()
                questions.append({
                    "id": data.get("id") or doc.id,
                    "testId": data.get("testId") or "",
                    "topicId": data.get("topicId") or "",
                    "questionText": data.get("questionText") or "",
                    "option0": data.get("option0") or "",
                    "option1": data.get("option1") or "",
                    "option2": data.get("option2") or "",
                    "option3": data.get("option3") or "",
                    "correctOptionIndex": data.get("correctOptionIndex", 0),
                    "explanation": data.get("explanation") or "",
                    "hint": data.get("hint") or "",
                })
        return jsonify(questions)
    except Exception as e:
        print("[Quiz Firestore questions error]", e)
        return jsonify({"error": str(e)}), 500

# ============================================================
# RUN (Koyeb Port Configured)
# ============================================================

if __name__ == "__main__":
    print("[Startup] CA Blockbuster server starting...")
    print("[Startup] Firestore configured:", bool(os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")))
    threading.Thread(target=telegram_updater, daemon=True).start()
    threading.Thread(target=audio_updater, daemon=True).start()
    
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
