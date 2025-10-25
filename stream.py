import subprocess
import time
from flask import Flask, Response, render_template_string, request, url_for
import sys

# Check if we are running the Flask app directly
# This section ensures the app can run even if the environment lacks a real 'subprocess'
# or if it's imported for testing without the necessary libraries.
if __name__ != "__main__":
    class MockProcess:
        def __init__(self): pass
        def kill(self): pass
        def stdout(self):
            # Mock read function for iter
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
            "-i", url, "-vn", "-ac", "1", "-b:a", "24k", "-buffer_size", "1024k", "-f", "mp3", "-"
        ]
        
        try:
            # Note: subprocess must be a real module for this to work outside of the mock environment
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=8192
            )
        except FileNotFoundError:
            # print("⚠️ FFmpeg not found. Ensure it's installed and in your PATH.")
            time.sleep(5)
            continue
        except Exception:
            # print(f"⚠️ Error starting FFmpeg process: {e}")
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

        # print("🔄 FFmpeg stopped, restarting stream...")
        time.sleep(3)


# 🌍 API to stream a station
@app.route("/stream/<station_name>")
def stream_station(station_name): 
    url = RADIO_STATIONS.get(station_name)
    if not url:
        return "⚠️ Station not found", 404
    return Response(generate_stream(url), mimetype="audio/mpeg")

# 📻 Keypad-friendly interface with Copy URL option
@app.route("/")
def index():
    stations = list(RADIO_STATIONS.items())
    
    # 💡 FIX: Generate the base URL *up to* /stream/ and ensure it ends with a slash
    # This results in: http://<host>:<port>/stream/
    stream_base_url = url_for('stream_station', station_name='_DUMMY_', _external=True).replace('_DUMMY_', '')

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Keypad Radio</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: black; color: lime; font-family: monospace; text-align: center; }
            h2 { font-size: 22px; margin: 10px; }
            .station { padding: 10px; border-bottom: 1px solid #333; }
            a { color: yellow; text-decoration: none; display: block; padding: 5px; }
            .active { background: green; color: black; }
            audio { width: 90%; margin-top: 10px; }
            .info { margin-top: 10px; font-size: 16px; }
            .controls button { 
                background: #333; 
                color: white; 
                border: 1px solid lime; 
                padding: 5px 10px; 
                margin: 5px; 
                cursor: pointer; 
                font-family: monospace;
            }
            .controls button:hover { background: #555; }
        </style>
    </head>
    <body>
        <h2>🎧 Radio Player</h2>
        <div id="list">
            {% for name, url in stations %}
                <div class="station">
                    <a href="#" onclick="play('{{name}}')">{{ loop.index }}. {{ name.replace('_',' ').title() }}</a>
                </div>
            {% endfor %}
        </div>
        <div id="player" style="display:none;">
            <div class="info" id="nowPlaying"></div>
            <audio id="audio" controls autoplay></audio>
            <div class="controls">
                <button onclick="copyUrl()" id="copyButton">🔗 Copy Stream URL</button>
            </div>
            <div class="info">Press 2=Prev 5=Play/Pause 8=Next 0=Back</div>
        </div>
        <script>
            const stations = {{ stations|tojson }};
            let current = -1;
            const audio = document.getElementById("audio");
            const player = document.getElementById("player");
            const list = document.getElementById("list");
            const now = document.getElementById("nowPlaying");
            const copyBtn = document.getElementById("copyButton");
            const streamBaseUrl = "{{ stream_base_url }}"; // e.g., http://<host>:8000/stream/

            function play(name){
                current = stations.findIndex(s => s[0] === name);
                const [station, url] = stations[current];
                
                // Constructs the correct URL: /stream/muthnabi_radio
                audio.src = streamBaseUrl + station; 
                
                now.textContent = "▶ " + station.replace(/_/g, " ").toUpperCase();
                player.style.display = "block";
                list.style.display = "none";
                copyBtn.textContent = '🔗 Copy Stream URL'; // Reset button text
            }

            function copyUrl(){
                if(current === -1) return;
                const stationName = stations[current][0];
                
                // Constructs the correct URL to be copied
                const streamUrl = streamBaseUrl + stationName;

                // Use the Clipboard API for modern browsers
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(streamUrl).then(() => {
                        copyBtn.textContent = '✅ Copied!';
                        setTimeout(() => copyBtn.textContent = '🔗 Copy Stream URL', 3000);
                    }).catch(err => {
                        console.error('Could not copy text: ', err);
                        copyBtn.textContent = '❌ Failed to copy!';
                    });
                } else {
                    // Fallback for older browsers 
                    const tempInput = document.createElement('input');
                    document.body.appendChild(tempInput);
                    tempInput.value = streamUrl;
                    tempInput.select();
                    document.execCommand('copy');
                    document.body.removeChild(tempInput);
                    copyBtn.textContent = '✅ Copied (Fallback)!';
                    setTimeout(() => copyBtn.textContent = '🔗 Copy Stream URL', 3000);
                }
            }

            function prev(){
                if(current > 0){ play(stations[current-1][0]); }
            }
            function next(){
                if(current < stations.length-1){ play(stations[current+1][0]); }
            }
            function back(){
                player.style.display = "none";
                list.style.display = "block";
                audio.pause();
            }

            document.addEventListener("keydown", e=>{
                const k = e.key;
                if(k === "2") prev();
                else if(k === "8") next();
                else if(k === "5"){
                    if(audio.paused) audio.play(); else audio.pause();
                }
                else if(k === "0") back();
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html, stations=stations, stream_base_url=stream_base_url)

if __name__ == "__main__":
    # Note: For this application to stream, you must have FFmpeg installed and accessible in your system's PATH.
    app.run(host="0.0.0.0", port=8000, debug=True)
