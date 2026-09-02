import subprocess
import time
import json
import urllib.request
import threading
import re
import os
import sys
from flask import Flask, Response, render_template_string, request, url_for

# Mock subprocess fallback if required
if __name__ != "__main__":
    class MockProcess:
        def __init__(self): pass
        def kill(self): pass
        def stdout(self):
            yield b""
            
    class MockSubprocess:
        PIPE = 0
        DEVNULL = 1
        def Popen(self, *args, **kwargs): return MockProcess()
    
    if 'subprocess' not in sys.modules or not hasattr(sys.modules['subprocess'], 'Popen'):
        subprocess = MockSubprocess()

app = Flask(__name__)

# 📡 Categorized Radio & TV Stations
STATION_CATEGORIES = {
    # 1. AIR Section (Initial fallbacks; replaced with full list from GitHub in background)
    "air": {
        "air_calicut": {"title": "Akashvani Kozhikode (AIR Calicut)", "url": "https://d3hrxqn1tritdh.cloudfront.net/8321393de70015fc/8321393de70015fc.m3u8"},
        "manjeri_fm": {"title": "AIR Manjeri FM", "url": "https://d3hrxqn1tritdh.cloudfront.net/58390a2ed33cea4a/58390a2ed33cea4a.m3u8"},
        "air_kavarati": {"title": "Akashvani Kavaratti", "url": "https://d1cvqgmbcpg5yn.cloudfront.net/ffb3825f86c4b9e3/ffb3825f86c4b9e3.m3u8"},
        "real_fm": {"title": "Real FM Kozhikode", "url": "http://air.pc.cdn.bitgravity.com/air/live/pbaudio083/playlist.m3u8"},
        "fm_gold": {"title": "FM Gold Delhi", "url": "https://airhlspush.pc.cdn.bitgravity.com/httppush/hispbaudio005/hispbaudio00564kbps.m3u8"},
    },
    # 2. TV Streams Section
    "tv": {
        "safari_tv": {"title": "Safari TV", "url": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8"},
        "victers_tv": {"title": "Victers TV", "url": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/victers/tv1/chunks.m3u8"},
        "kairali_we": {"title": "Kairali WE", "url": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/wetv_nim_https/050522/wetv/playlist.m3u8"},
        "mazhavil_manorama": {"title": "Mazhavil Manorama", "url": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/mazhavilmanorama_nim_https/050522/mazhavilmanorama/playlist.m3u8"},
        "24_news": {"title": "24 News", "url": "https://segment.yuppcdn.net/110322/channel24/playlist.m3u8"},
        "amrita_tv": {"title": "Amrita TV", "url": "https://ddash74r36xqp.cloudfront.net/master.m3u8"},
        "asianet_news": {"title": "Asianet News", "url": "https://amg13737-amg13737c1-amgplt0016.playout.now3.amagi.tv/playlist/amg13737-amg13737c1-amgplt0016/playlist.m3u8"},
        "media_one": {"title": "Media One", "url": "https://cdn-3.pishow.tv/live/1481/master.m3u8"},
        "manorama_news": {"title": "Manorama News", "url": "https://mmtvnews1.akamaized.net/v1/master/673630b269b766886555eebfddd4f27f3de3ab50/mmtvNewsCampaign1/index.m3u8"},
        "en_vivo": {"title": "RT En Vivo", "url": "https://rt-esp.rttv.com/dvr/rtesp/playlist_1600Kb.m3u8"},
    },
    # 3. Other Stations Section
    "others": {
        "muthnabi_radio": {"title": "Muthnabi Radio", "url": "http://cast4.my-control-panel.com/proxy/muthnabi/stream"},
        "radio_nellikka": {"title": "Radio Nellikka", "url": "https://usa20.fastcast4u.com:2130/stream"},
        "radio_mattoli": {"title": "Radio Mattoli", "url": "https://cast1.my-control-panel.com/proxy/radiomattoli/stream"},
        "malayalam_1": {"title": "Malayalam 1", "url": "http://167.114.131.90:5412/stream"},
        "radio_digital_malayali": {"title": "Radio Digital Malayali", "url": "https://radio.digitalmalayali.in/listen/stream/radio.mp3"},
        "malayalam_90s": {"title": "Malayalam 90s", "url": "https://stream-159.zeno.fm/gm3g9amzm0hvv?zs-x-7jq8ksTOav9ZhlYHi9xw"},
        "aural_oldies": {"title": "Aural Oldies", "url": "https://stream-162.zeno.fm/tksfwb1mgzzuv?zs=SxeQj1-7R0alsZSWJie5eQ"},
        "radio_malayalam": {"title": "Radio Malayalam", "url": "https://radiomalayalamfm.com/radio/8000/radio.mp3"},
        "swaranjali": {"title": "Swaranjali", "url": "https://stream-161.zeno.fm/x7mve2vt01zuv?zs-D4nK05-7SSK2FZAsvumh2w"},
        "radio_beat_malayalam": {"title": "Radio Beat Malayalam", "url": "http://live.exertion.in:8050/radio.mp3"},
        "shahul_radio": {"title": "Shahul Radio", "url": "https://stream-150.zeno.fm/cynbm5ngx38uv?zs=Ktca5StNRWm-sdIR7GloVg"},
        "raja_radio": {"title": "Raja Radio", "url": "http://159.203.111.241:8026/stream"},
        "nonstop_hindi": {"title": "Nonstop Hindi", "url": "http://s5.voscast.com:8216/stream"},
        "motivational_series": {"title": "Motivational Series", "url": "http://104.7.66.64:8010"},
        "deenagers_radio": {"title": "Deenagers Radio", "url": "http://104.7.66.64:8003/"},
        "hajj_channel": {"title": "Hajj Channel", "url": "http://104.7.66.64:8005"},
        "abc_islam": {"title": "ABC Islam", "url": "http://s10.voscast.com:9276/stream"},
        "eram_fm": {"title": "Eram FM", "url": "http://icecast2.edisimo.com:8000/eramfm.mp3"},
        "al_sumood_fm": {"title": "Al Sumood FM", "url": "http://us3.internet-radio.com/proxy/alsumoodfm2020?mp=/stream"},
        "nur_ala_nur": {"title": "Nur Ala Nur", "url": "http://104.7.66.64:8011/"},
        "ruqya_radio": {"title": "Ruqya Radio", "url": "http://104.7.66.64:8004"},
        "seiyun_radio": {"title": "Seiyun Radio", "url": "http://s2.radio.co/s26c62011e/listen"},
        "noor_al_eman": {"title": "Noor Al Eman", "url": "http://edge.mixlr.com/channel/boaht"},
        "sam_yemen": {"title": "Sam Yemen", "url": "https://edge.mixlr.com/channel/kijwr"},
        "afaq": {"title": "Afaq", "url": "https://edge.mixlr.com/channel/rumps"},
        "alfasi_radio": {"title": "Alfasi Radio", "url": "https://qurango.net/radio/mishary_alafasi"},
        "tafsir_quran": {"title": "Tafsir Quran", "url": "https://radio.quranradiotafsir.com/9992/stream"},
        "sirat_al_mustaqim": {"title": "Sirat Al Mustaqim", "url": "http://104.7.66.64:8091/stream"},
        "river_nile_radio": {"title": "River Nile Radio", "url": "http://104.7.66.64:8087"},
        "quran_radio_cairo": {"title": "Quran Radio Cairo", "url": "http://n02.radiojar.com/8s5u5tpdtwzuv"},
        "quran_radio_nablus": {"title": "Quran Radio Nablus", "url": "http://www.quran-radio.org:8002/"},
        "al_nour": {"title": "Al Nour", "url": "http://audiostreaming.itworkscdn.com:9066/"},
        "allahu_akbar_radio": {"title": "Allahu Akbar Radio", "url": "http://66.45.232.132:9996/stream"},
        "omar_abdul_kafi_radio": {"title": "Omar Abdul Kafi Radio", "url": "http://104.7.66.64:8007"},
        "urdu_islamic_lecture": {"title": "Urdu Islamic Lecture", "url": "http://144.91.121.54:27001/channel_02.aac"},
        "hob_nabi": {"title": "Hob Nabi", "url": "http://216.245.210.78:8098/stream"},
        "sanaa_radio": {"title": "Sanaa Radio", "url": "http://dc5.serverse.com/proxy/pbmhbvxs/stream"},
        "rubat_ataq": {"title": "Rubat Ataq", "url": "http://stream.zeno.fm/5tpfc8d7xqruv"},
        "al_jazeera": {"title": "Al Jazeera", "url": "http://live-hls-audio-web-aja.getaj.net/VOICE-AJA/index.m3u8"},
        "oman_radio": {"title": "Oman Radio", "url": "https://partwota.cdn.mgmlcdn.com/omanrdoorg/omanrdo.stream_aac/chunklist.m3u8"},
        "radio_jornal": {"title": "Radio Jornal", "url": "https://player-ne10-radiojornal-app.stream.uol.com.br/live/radiojornalrecifeapp.m3u8"},
        "arabic": {"title": "Arabic Radio", "url": "https://live.arabicradio.net/hls/arabic.m3u8"},
    }
}

# Stream lookup mapping
RADIO_STATIONS = {}

def sync_radio_stations():
    """Flattens categorized stations into a fast-lookup dictionary."""
    RADIO_STATIONS.clear()
    for cat in STATION_CATEGORIES.values():
        for st_id, st_info in cat.items():
            RADIO_STATIONS[st_id] = st_info["url"]

sync_radio_stations()

# 🔄 Akashvani Full Repository Downloader & Sync
GITHUB_JSON_URLS = [
    "https://raw.githubusercontent.com/codito/akashvani/master/stations.json",
    "https://raw.githubusercontent.com/codito/akashvani/main/stations.json",
]

def make_slug(name):
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', name.strip()).strip('_').lower()
    return slug or "air_station"

def fetch_all_akashvani_stations():
    """Fetches every station available in the codito/akashvani repository."""
    for url in GITHUB_JSON_URLS:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Flask Radio Player)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    extracted = []
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                name = item.get("channel_name") or item.get("name") or item.get("title") or ""
                                stream = item.get("stream_url") or item.get("url") or item.get("stream") or ""
                                if name and stream:
                                    extracted.append((name.strip(), stream.strip()))
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, str):
                                extracted.append((k.strip(), v.strip()))
                            elif isinstance(v, dict):
                                name = v.get("channel_name") or v.get("name") or k
                                stream = v.get("stream_url") or v.get("url") or v.get("stream") or ""
                                if stream:
                                    extracted.append((name.strip(), stream.strip()))
                    return extracted
        except Exception as err:
            print(f"⚠️ Note: Failed fetching from {url}: {err}")
    return []

def update_all_akashvani():
    """Populates STATION_CATEGORIES['air'] with ALL stations from GitHub."""
    stations = fetch_all_akashvani_stations()
    if not stations:
        print("ℹ️ Using default fallback AIR stations.")
        return

    new_air_stations = {}
    for name, stream_url in stations:
        slug_base = make_slug(name)
        slug = slug_base
        count = 1
        while slug in new_air_stations:
            count += 1
            slug = f"{slug_base}_{count}"

        new_air_stations[slug] = {
            "title": name,
            "url": stream_url
        }

    STATION_CATEGORIES["air"] = new_air_stations
    sync_radio_stations()
    print(f"✅ Successfully loaded {len(new_air_stations)} Akashvani stations from GitHub.")

def schedule_periodic_updates(interval_hours=12):
    """Background worker: fetches on launch and refreshes every 12 hours without blocking startup."""
    def worker():
        # Fetch in background so Flask binds to port immediately
        update_all_akashvani()
        while True:
            time.sleep(interval_hours * 3600)
            update_all_akashvani()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

# Start background sync immediately (non-blocking)
schedule_periodic_updates(interval_hours=12)


# 🔄 FFmpeg audio proxy
def generate_stream(url):

    def build_command(is_amagi):
        base = [
            "ffmpeg",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "10",
        ]

        if is_amagi:
            base += [
                "-user_agent", "Mozilla/5.0",
                "-headers", "Referer: https://www.google.com\r\n",
                "-protocol_whitelist", "file,http,https,tcp,tls",
            ]

        base += ["-i", url]

        if is_amagi:
            base += ["-map", "a:0"]

        base += [
            "-vn",
            "-ac", "1",
            "-b:a", "64k",
            "-f", "mp3",
            "-"
        ]

        return base

    is_amagi = "amagi.tv" in url

    while True:
        try:
            command = build_command(is_amagi)

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=16384
            )

            got_data = False

            while True:
                chunk = process.stdout.read(16384)
                if not chunk:
                    break
                got_data = True
                yield chunk

            if is_amagi and not got_data:
                print("⚠️ Asianet fallback retry...")
                fallback_cmd = build_command(False)
                process = subprocess.Popen(
                    fallback_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=16384
                )

                while True:
                    chunk = process.stdout.read(16384)
                    if not chunk:
                        break
                    yield chunk

        except Exception as e:
            print("FFmpeg error:", e)

        time.sleep(1)


# 🌍 API to stream a station
@app.route("/stream/<station_name>")
def stream_station(station_name): 
    url = RADIO_STATIONS.get(station_name)
    if not url:
        return "⚠️ Station not found", 404
    return Response(generate_stream(url), mimetype="audio/mpeg")


# 📻 Keypad-friendly interface with 3 Tabs & Instant Search
@app.route("/")
def index():
    stream_base_url = url_for('stream_station', station_name='_DUMMY_', _external=True).replace('_DUMMY_', '')
    
    all_stations = []
    for cat_key, stations in STATION_CATEGORIES.items():
        for st_id, st_info in stations.items():
            all_stations.append({
                "id": st_id,
                "title": st_info["title"],
                "url": st_info["url"]
            })

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>📻 Keypad Radio</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                background: black; 
                color: lime; 
                font-family: monospace; 
                text-align: center; 
                margin: 0; 
                padding: 5px;
                padding-bottom: 130px;
            }
            h2 { 
                font-size: 18px; 
                margin: 8px 0 10px; 
                color: #00ff00; 
            }

            /* Search Filter Box */
            .search-box {
                margin-bottom: 10px;
                padding: 0 5px;
            }
            .search-box input {
                width: 92%;
                max-width: 450px;
                padding: 8px 12px;
                background: #111;
                color: yellow;
                border: 1px solid lime;
                border-radius: 4px;
                font-family: monospace;
                font-size: 13px;
                outline: none;
            }
            .search-box input:focus {
                border-color: #00ff00;
                box-shadow: 0 0 6px lime;
            }

            /* Tab Navigation Bar */
            .tab-nav {
                display: flex;
                justify-content: center;
                gap: 6px;
                margin-bottom: 12px;
                position: sticky;
                top: 0;
                background: black;
                padding: 5px 0;
                z-index: 100;
            }

            .tab-btn {
                flex: 1;
                max-width: 140px;
                background: #111;
                color: lime;
                border: 1px solid lime;
                padding: 8px 4px;
                font-family: monospace;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .tab-btn.active {
                background: #00ff00;
                color: black;
                box-shadow: 0 0 6px lime;
            }

            .tab-btn:hover:not(.active) {
                background: #003300;
                color: #fff;
            }

            /* Tab Panes */
            .tab-pane {
                display: none;
            }

            .tab-pane.active {
                display: block;
            }

            /* Grid Layout */
            .station-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
                gap: 8px;
                list-style: none;
                padding: 0;
                margin: 0;
            }

            /* Station Card */
            .station { 
                background: #111; 
                color: yellow; 
                padding: 8px; 
                border: 1px solid #0f0; 
                border-radius: 6px; 
                min-height: 75px; 
                display: flex; 
                flex-direction: column; 
                justify-content: space-between; 
                align-items: stretch; 
            }

            .station-title {
                color: yellow; 
                font-size: 12px; 
                font-weight: bold; 
                margin-bottom: 5px; 
                text-align: left; 
                line-height: 1.2; 
                word-break: break-word;
            }

            /* Play Button */
            .controls-group {
                display: flex; 
                justify-content: space-between; 
                gap: 5px; 
            }

            .list-button {
                flex-grow: 1; 
                font-size: 12px; 
                padding: 5px; 
                text-decoration: none; 
                border: 1px solid lime; 
                border-radius: 4px; 
                cursor: pointer; 
                font-weight: bold; 
                background: #003300; 
                color: #fff; 
            }
            .list-button:hover { background: #00ff00; color: black; }

            /* Mini-Player */
            #player {
                position: fixed; 
                bottom: 0; 
                left: 0; 
                width: 100%; 
                background: #111; 
                border-top: 2px solid lime; 
                padding: 6px 0; 
                z-index: 1000; 
            }

            audio { width: 90%; height: 25px; }

            .info { 
                font-size: 12px; 
                color: #0f0; 
                margin: 3px 0; 
            }

            .player-controls {
                display: flex; 
                justify-content: center; 
                align-items: center; 
                gap: 10px; 
            }
            .player-controls button { 
                background: #222; 
                color: #fff; 
                border: 1px solid lime; 
                padding: 3px 6px; 
                font-size: 12px; 
                border-radius: 3px; 
                cursor: pointer; 
            }
            .player-controls button:hover { background: #444; }
        </style>
    </head>
    <body>
        <h2>🎧 Web & Radio Player</h2>

        <!-- Search Bar -->
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="🔍 Search station..." oninput="filterStations()">
        </div>

        <!-- 3 Category Tabs -->
        <div class="tab-nav">
            <button id="btn-air" class="tab-btn active" onclick="switchTab('air')">📻 AIR ({{ categories.air|length }})</button>
            <button id="btn-tv" class="tab-btn" onclick="switchTab('tv')">📺 TV Streams ({{ categories.tv|length }})</button>
            <button id="btn-others" class="tab-btn" onclick="switchTab('others')">🌐 Others ({{ categories.others|length }})</button>
        </div>

        <!-- AIR Tab -->
        <div id="tab-air" class="tab-pane active">
            <div class="station-grid">
                {% for id, item in categories.air.items() %}
                    <div class="station" data-title="{{ item.title }}">
                        <div class="station-title">{{ loop.index }}. {{ item.title }}</div>
                        <div class="controls-group">
                            <a href="javascript:void(0)" onclick="play('{{id}}')" class="list-button">▶ Play</a>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- TV Streams Tab -->
        <div id="tab-tv" class="tab-pane">
            <div class="station-grid">
                {% for id, item in categories.tv.items() %}
                    <div class="station" data-title="{{ item.title }}">
                        <div class="station-title">{{ loop.index }}. {{ item.title }}</div>
                        <div class="controls-group">
                            <a href="javascript:void(0)" onclick="play('{{id}}')" class="list-button">▶ Play</a>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- Others Tab -->
        <div id="tab-others" class="tab-pane">
            <div class="station-grid">
                {% for id, item in categories.others.items() %}
                    <div class="station" data-title="{{ item.title }}">
                        <div class="station-title">{{ loop.index }}. {{ item.title }}</div>
                        <div class="controls-group">
                            <a href="javascript:void(0)" onclick="play('{{id}}')" class="list-button">▶ Play</a>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- Mini-Player -->
        <div id="player" style="display:none;">
            <div class="info" id="nowPlaying"></div>
            <audio id="audio" controls autoplay></audio>
            <div class="player-controls">
                <button onclick="copyUrl()" id="playerCopyButton">🔗 Copy</button>
            </div>
            <div class="info">2=Prev 5=Play/Pause 8=Next 0=Back</div>
        </div>

        <script>
            const allStations = {{ all_stations|tojson }};
            let current = -1;
            const audio = document.getElementById("audio");
            const player = document.getElementById("player");
            const now = document.getElementById("nowPlaying");
            const streamBaseUrl = "{{ stream_base_url }}";
            const playerCopyBtn = document.getElementById("playerCopyButton");

            function switchTab(tabKey) {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

                const btn = document.getElementById('btn-' + tabKey);
                const pane = document.getElementById('tab-' + tabKey);
                if (btn && pane) {
                    btn.classList.add('active');
                    pane.classList.add('active');
                    filterStations();
                }
            }

            function filterStations() {
                const q = document.getElementById('searchInput').value.toLowerCase().trim();
                const activePane = document.querySelector('.tab-pane.active');
                if (!activePane) return;
                const cards = activePane.querySelectorAll('.station');
                cards.forEach(card => {
                    const title = card.getAttribute('data-title') || card.innerText;
                    card.style.display = title.toLowerCase().includes(q) ? 'flex' : 'none';
                });
            }

            function play(id){
                current = allStations.findIndex(s => s.id === id);
                if (current === -1) return;
                const st = allStations[current];
                audio.src = streamBaseUrl + st.id; 
                audio.play(); 
                now.textContent = "▶ " + st.title.toUpperCase();
                player.style.display = "block";
                playerCopyBtn.textContent = '🔗 Copy';
                window.scrollTo(0, document.body.scrollHeight);
            }

            function copyUrl(){
                if(current === -1) return;
                const stationId = allStations[current].id;
                const streamUrl = streamBaseUrl + stationId;
                navigator.clipboard?.writeText(streamUrl);
                playerCopyBtn.textContent = '✅ Copied!';
                setTimeout(() => playerCopyBtn.textContent = '🔗 Copy', 2000);
            }

            function prev(){ 
                if(current > 0) {
                    play(allStations[current-1].id);
                }
            }
            function next(){ 
                if(current < allStations.length-1) {
                    play(allStations[current+1].id);
                }
            }
            function back(){ 
                player.style.display = "none"; 
                audio.pause(); 
                current = -1; 
            }

            document.addEventListener("keydown", e=>{
                const k = e.key;
                if(player.style.display === "block"){
                    if(k==="2") prev();
                    else if(k==="8") next();
                    else if(k==="5") (audio.paused?audio.play():audio.pause());
                    else if(k==="0") back();
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(
        html,
        categories=STATION_CATEGORIES,
        all_stations=all_stations,
        stream_base_url=stream_base_url
    )

if __name__ == "__main__":
    # Dynamically bind to Koyeb's assigned PORT environment variable, default to 8000
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
