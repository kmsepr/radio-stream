import subprocess
import time
from flask import Flask, Response, render_template_string, request, url_for
import sys

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

# 📡 List of radio stations
RADIO_STATIONS = {
    "muthnabi_radio": "http://cast4.my-control-panel.com/proxy/muthnabi/stream",
    "radio_nellikka": "https://usa20.fastcast4u.com:2130/stream",
    "air_kavarati": "https://air.pc.cdn.bitgravity.com/air/live/pbaudio189/chunklist.m3u8",
    "air_calicut": "https://air.pc.cdn.bitgravity.com/air/live/pbaudio082/chunklist.m3u8",
    "manjeri_fm": "https://air.pc.cdn.bitgravity.com/air/live/pbaudio101/chunklist.m3u8",
    "real_fm": "http://air.pc.cdn.bitgravity.com/air/live/pbaudio083/playlist.m3u8",
    "safari_tv": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "victers_tv": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/victers/tv1/chunks.m3u8",
    "kairali_we": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/wetv_nim_https/050522/wetv/playlist.m3u8",
    "mazhavil_manorama": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/mazhavilmanorama_nim_https/050522/mazhavilmanorama/playlist.m3u8",
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
    "fm_gold": "https://airhlspush.pc.cdn.bitgravity.com/httppush/hispbaudio005/hispbaudio00564kbps.m3u8",
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
}

# 🔄 FFmpeg audio proxy
def generate_stream(url):
    process = None
    while True:
        if process:
            process.kill() 

        command = [
            "ffmpeg", "-reconnect", "1", "-reconnect_streamed", "1",
            "-reconnect_delay_max", "10", "-fflags", "nobuffer", "-flags", "low_delay",
            "-i", url, "-vn", "-ac", "1", "-b:a", "64k", "-buffer_size", "1024k", "-f", "mp3", "-"
        ]
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=8192
            )
        except FileNotFoundError:
            time.sleep(5)
            continue
        except Exception:
            time.sleep(5)
            continue

        try:
            for chunk in iter(lambda: process.stdout.read(8192), b""):
                yield chunk
        except GeneratorExit:
            process.kill()
            break
        except Exception:
            pass

        time.sleep(3)


# 🌍 API to stream a station
@app.route("/stream/<station_name>")
def stream_station(station_name): 
    url = RADIO_STATIONS.get(station_name)
    if not url:
        return "⚠️ Station not found", 404
    return Response(generate_stream(url), mimetype="audio/mpeg")

# 📻 Keypad-friendly interface with Grid Cards
@app.route("/")
def index():
    stations = list(RADIO_STATIONS.items())
    stream_base_url = url_for('stream_station', station_name='_DUMMY_', _external=True).replace('_DUMMY_', '')

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
                padding-bottom: 130px; /* Space for fixed player */
            }
            h2 { 
                font-size: 18px; 
                margin: 10px 0 15px; 
                color: #00ff00; 
            }

            /* Compact grid */
            #list {
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
        <h2>🎧 Radio Stations</h2>
        <div id="list">
            {% for name, url in stations %}
                <div class="station">
                    <div class="station-title">{{ loop.index }}. {{ name.replace('_',' ').title() }}</div>
                    <div class="controls-group">
                        <a href="#" onclick="play('{{name}}')" class="list-button">▶ Play</a>
                    </div>
                </div>
            {% endfor %}
        </div>

        <div id="player" style="display:none;">
            <div class="info" id="nowPlaying"></div>
            <audio id="audio" controls autoplay></audio>
            <div class="player-controls">
                <button onclick="copyUrl()" id="playerCopyButton">🔗 Copy</button>
            </div>
            <div class="info">2=Prev 5=Play/Pause 8=Next 0=Back</div>
        </div>

        <script>
            const stations = {{ stations|tojson }};
            let current = -1;
            const audio = document.getElementById("audio");
            const player = document.getElementById("player");
            const now = document.getElementById("nowPlaying");
            const streamBaseUrl = "{{ stream_base_url }}";
            const playerCopyBtn = document.getElementById("playerCopyButton");

            function play(name){
                current = stations.findIndex(s => s[0] === name);
                const [station, url] = stations[current];
                audio.src = streamBaseUrl + station; 
                audio.play(); 
                now.textContent = "▶ " + station.replace(/_/g, " ").toUpperCase();
                player.style.display = "block";
                playerCopyBtn.textContent = '🔗 Copy';
                window.scrollTo(0, document.body.scrollHeight);
            }

            function copyUrl(){
                if(current === -1) return;
                const stationName = stations[current][0];
                const streamUrl = streamBaseUrl + stationName;
                navigator.clipboard?.writeText(streamUrl);
                playerCopyBtn.textContent = '✅ Copied!';
                setTimeout(() => playerCopyBtn.textContent = '🔗 Copy', 2000);
            }

            function prev(){ if(current > 0) play(stations[current-1][0]); }
            function next(){ if(current < stations.length-1) play(stations[current+1][0]); }
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
    return render_template_string(html, stations=stations, stream_base_url=stream_base_url)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
