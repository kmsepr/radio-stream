import subprocess
import time
import json
import urllib.request
import threading
import re
import sys
from flask import Flask, Response, render_template_string, request, url_for

# Check if we are running the Flask app directly
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
    "air": {
        "air_calicut": "https://d3hrxqn1tritdh.cloudfront.net/8321393de70015fc/8321393de70015fc.m3u8",
        "manjeri_fm": "https://d3hrxqn1tritdh.cloudfront.net/58390a2ed33cea4a/58390a2ed33cea4a.m3u8",
        "air_kavarati": "https://d1cvqgmbcpg5yn.cloudfront.net/ffb3825f86c4b9e3/ffb3825f86c4b9e3.m3u8",
        "real_fm": "http://air.pc.cdn.bitgravity.com/air/live/pbaudio083/playlist.m3u8",
        "fm_gold": "https://airhlspush.pc.cdn.bitgravity.com/httppush/hispbaudio005/hispbaudio00564kbps.m3u8",
    },
    "tv": {
        "safari_tv": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
        "victers_tv": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/victers/tv1/chunks.m3u8",
        "kairali_we": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/wetv_nim_https/050522/wetv/playlist.m3u8",
        "mazhavil_manorama": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/mazhavilmanorama_nim_https/050522/mazhavilmanorama/playlist.m3u8",
        "24_news": "https://segment.yuppcdn.net/110322/channel24/playlist.m3u8",
        "amrita_tv": "https://ddash74r36xqp.cloudfront.net/master.m3u8",
        "asianet_news": "https://amg13737-amg13737c1-amgplt0016.playout.now3.amagi.tv/playlist/amg13737-amg13737c1-amgplt0016/playlist.m3u8",
        "media_one": "https://cdn-3.pishow.tv/live/1481/master.m3u8",
        "manorama_news": "https://mmtvnews1.akamaized.net/v1/master/673630b269b766886555eebfddd4f27f3de3ab50/mmtvNewsCampaign1/index.m3u8",
        "en_vivo": "https://rt-esp.rttv.com/dvr/rtesp/playlist_1600Kb.m3u8",
    },
    "others": {
        "muthnabi_radio": "http://cast4.my-control-panel.com/proxy/muthnabi/stream",
        "radio_nellikka": "https://usa20.fastcast4u.com:2130/stream",
        "radio_mattoli": "https://cast1.my-control-panel.com/proxy/radiomattoli/stream",
        "malayalam_1": "http://167.114.131.90:5412/stream",
        "radio_digital_malayali": "https://radio.digitalmalayali.in/listen/stream/radio.mp3",
        "malayalam_90s": "https://stream-159.zeno.fm/gm3g9amzm0hvv?zs-x-7jq8ksTOav9ZhlYHi9xw",
        "aural_oldies": "https://stream-162.zeno.fm/tksfwb1mgzzuv?zs=SxeQj1-7R0alsZSWJie5eQ",
        "radio_malayalam": "https://radiomalayalamfm.com/radio/8000/radio.mp3",
        "swaranjali": "https://stream-161.zeno.fm/x7mve2vt01zuv?zs-D4nK05-7SSK2FZAsvumh2w",
        "radio_beat_malayalam": "http://live.exertion.in:8050/radio.mp3",
        "shahul_radio": "https://stream-150.zeno.fm/cynbm5ngx38uv?zs=Ktca5StNRWm-sdIR7GloVg",
        "raja_radio": "http://159.203.111.241:8026/stream",
        "nonstop_hindi": "http://s5.voscast.com:8216/stream",
        "motivational_series": "http://104.7.66.64:8010",
        "deenagers_radio": "http://104.7.66.64:8003/",
        "hajj_channel": "http://104.7.66.64:8005",
        "abc_islam": "http://s10.voscast.com:9276/stream",
        "eram_fm": "http://icecast2.edisimo.com:8000/eramfm.mp3",
        "al_sumood_fm": "http://us3.internet-radio.com/proxy/alsumoodfm2020?mp=/stream",
        "nur_ala_nur": "http://104.7.66.64:8011/",
        "ruqya_radio": "http://104.7.66.64:8004",
        "seiyun_radio": "http://s2.radio.co/s26c62011e/listen",
        "noor_al_eman": "http://edge.mixlr.com/channel/boaht",
        "sam_yemen": "https://edge.mixlr.com/channel/kijwr",
        "afaq": "https://edge.mixlr.com/channel/rumps",
        "alfasi_radio": "https://qurango.net/radio/mishary_alafasi",
        "tafsir_quran": "https://radio.quranradiotafsir.com/9992/stream",
        "sirat_al_mustaqim": "http://104.7.66.64:8091/stream",
        "river_nile_radio": "http://104.7.66.64:8087",
        "quran_radio_cairo": "http://n02.radiojar.com/8s5u5tpdtwzuv",
        "quran_radio_nablus": "http://www.quran-radio.org:8002/",
        "al_nour": "http://audiostreaming.itworkscdn.com:9066/",
        "allahu_akbar_radio": "http://66.45.232.132:9996/stream",
        "omar_abdul_kafi_radio": "http://104.7.66.64:8007",
        "urdu_islamic_lecture": "http://144.91.121.54:27001/channel_02.aac",
        "hob_nabi": "http://216.245.210.78:8098/stream",
        "sanaa_radio": "http://dc5.serverse.com/proxy/pbmhbvxs/stream",
        "rubat_ataq": "http://stream.zeno.fm/5tpfc8d7xqruv",
        "al_jazeera": "http://live-hls-audio-web-aja.getaj.net/VOICE-AJA/index.m3u8",
        "oman_radio": "https://partwota.cdn.mgmlcdn.com/omanrdoorg/omanrdo.stream_aac/chunklist.m3u8",
        "radio_jornal": "https://player-ne10-radiojornal-app.stream.uol.com.br/live/radiojornalrecifeapp.m3u8",
        "arabic": "https://live.arabicradio.net/hls/arabic.m3u8",
    }
}

# Flattened dictionary for quick lookup by endpoint
RADIO_STATIONS = {}
for cat in STATION_CATEGORIES.values():
    RADIO_STATIONS.update(cat)

# 🔄 Akashvani URL Auto-Updater
GITHUB_JSON_URLS = [
    "https://raw.githubusercontent.com/codito/akashvani/master/stations.json",
    "https://raw.githubusercontent.com/codito/akashvani/main/stations.json",
]

AIR_KEY_MATCHERS = {
    "air_calicut": [r"kozhikode", r"calicut"],
    "manjeri_fm": [r"manjeri"],
    "air_kavarati": [r"kavaratti", r"kavarati"],
    "real_fm": [r"real\s*fm"],
    "fm_gold": [r"fm\s*gold.*delhi", r"fm\s*gold"],
}

def fetch_akashvani_stations():
    """Fetches station streams from the codito/akashvani repository."""
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
                                    extracted.append((name, stream))
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, str):
                                extracted.append((k, v))
                            elif isinstance(v, dict):
                                name = v.get("channel_name") or v.get("name") or k
                                stream = v.get("stream_url") or v.get("url") or v.get("stream") or ""
                                if stream:
                                    extracted.append((name, stream))
                    return extracted
        except Exception as err:
            print(f"⚠️ Failed fetching from {url}: {err}")
    return []

def update_akashvani_urls():
    """Updates matching AIR URLs in STATION_CATEGORIES['air'] and RADIO_STATIONS."""
    stations = fetch_akashvani_stations()
    if not stations:
        print("ℹ️ Using default/cached AIR station URLs.")
        return

    updated_count = 0
    for target_key, patterns in AIR_KEY_MATCHERS.items():
        for name, stream_url in stations:
            matched = any(re.search(pat, name, re.IGNORECASE) for pat in patterns)
            if matched:
                STATION_CATEGORIES["air"][target_key] = stream_url
                RADIO_STATIONS[target_key] = stream_url
                updated_count += 1
                break

    print(f"✅ Akashvani station URLs refreshed ({updated_count} stations updated).")

def schedule_periodic_updates(interval_hours=12):
    def worker():
        while True:
            time.sleep(interval_hours * 3600)
            update_akashvani_urls()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

update_akashvani_urls()
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
            "-b:a", "40k",
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


# 📻 Keypad-friendly interface with 3 Tabs
@app.route("/")
def index():
    stream_base_url = url_for('stream_station', station_name='_DUMMY_', _external=True).replace('_DUMMY_', '')
    all_stations = list(RADIO_STATIONS.items())

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
                margin: 8px 0 12px; 
                color: #00ff00; 
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
                font-size: 13px;
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

            /* Tab Content Panes */
            .tab-pane {
                display: none;
            }

            .tab-pane.active {
                display: block;
            }

            /* Compact grid */
            .station-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 8px;
                list-style: none;
                padding: 0;
                margin: 0;
            }

            /* Small compact cards */
            .station { 
                background: #111; 
                color: yellow; 
                padding: 8px; 
                border: 1px solid #0f0; 
                border-radius: 6px; 
                min-height: 70px; 
                display: flex; 
                flex-direction: column; 
                justify-content: space-between; 
                align-items: stretch; 
            }

            .station-title {
                color: yellow; 
                font-size: 13px; 
                font-weight: bold; 
                margin-bottom: 5px; 
                text-align: left; 
                line-height: 1.2; 
            }

            /* Button group */
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

            /* Fixed mini-player */
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

        <!-- 3 Category Tabs -->
        <div class="tab-nav">
            <button id="btn-air" class="tab-btn active" onclick="switchTab('air')">📻 AIR ({{ categories.air|length }})</button>
            <button id="btn-tv" class="tab-btn" onclick="switchTab('tv')">📺 TV Streams ({{ categories.tv|length }})</button>
            <button id="btn-others" class="tab-btn" onclick="switchTab('others')">🌐 Others ({{ categories.others|length }})</button>
        </div>

        <!-- AIR Tab -->
        <div id="tab-air" class="tab-pane active">
            <div class="station-grid">
                {% for name, url in categories.air.items() %}
                    <div class="station">
                        <div class="station-title">{{ loop.index }}. {{ name.replace('_',' ').title() }}</div>
                        <div class="controls-group">
                            <a href="#" onclick="play('{{name}}')" class="list-button">▶ Play</a>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- TV Streams Tab -->
        <div id="tab-tv" class="tab-pane">
            <div class="station-grid">
                {% for name, url in categories.tv.items() %}
                    <div class="station">
                        <div class="station-title">{{ loop.index }}. {{ name.replace('_',' ').title() }}</div>
                        <div class="controls-group">
                            <a href="#" onclick="play('{{name}}')" class="list-button">▶ Play</a>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- Others Tab -->
        <div id="tab-others" class="tab-pane">
            <div class="station-grid">
                {% for name, url in categories.others.items() %}
                    <div class="station">
                        <div class="station-title">{{ loop.index }}. {{ name.replace('_',' ').title() }}</div>
                        <div class="controls-group">
                            <a href="#" onclick="play('{{name}}')" class="list-button">▶ Play</a>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- Fixed Mini-Player -->
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
                }
            }

            function play(name){
                current = allStations.findIndex(s => s[0] === name);
                audio.src = streamBaseUrl + name; 
                audio.play(); 
                now.textContent = "▶ " + name.replace(/_/g, " ").toUpperCase();
                player.style.display = "block";
                playerCopyBtn.textContent = '🔗 Copy';
                window.scrollTo(0, document.body.scrollHeight);
            }

            function copyUrl(){
                if(current === -1) return;
                const stationName = allStations[current][0];
                const streamUrl = streamBaseUrl + stationName;
                navigator.clipboard?.writeText(streamUrl);
                playerCopyBtn.textContent = '✅ Copied!';
                setTimeout(() => playerCopyBtn.textContent = '🔗 Copy', 2000);
            }

            function prev(){ if(current > 0) play(allStations[current-1][0]); }
            function next(){ if(current < allStations.length-1) play(allStations[current+1][0]); }
            function back(){ player.style.display = "none"; audio.pause(); current = -1; }

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
    app.run(host="0.0.0.0", port=8000, debug=True)
