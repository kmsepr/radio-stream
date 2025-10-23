import subprocess
import time
from flask import Flask, Response, render_template_string, request

app = Flask(__name__)

# 📡 List of radio stations
RADIO_STATIONS = {
    "muthnabi_radio": "http://cast4.my-control-panel.com/proxy/muthnabi/stream",
    "radio_keralam": "http://ice31.securenetsystems.net/RADIOKERAL",
    "malayalam_1": "http://167.114.131.90:5412/stream",
    "radio_digital_malayali": "https://radio.digitalmalayali.in/listen/stream/radio.mp3",
    "malayalam_90s": "https://stream-159.zeno.fm/gm3g9amzm0hvv?zs-x-7jq8ksTOav9ZhlYHi9xw",
    "aural_oldies": "https://stream-162.zeno.fm/tksfwb1mgzzuv?zs=SxeQj1-7R0alsZSWJie5eQ",
    "radio_malayalam": "https://radiomalayalamfm.com/radio/8000/radio.mp3",
    "swaranjali": "https://stream-161.zeno.fm/x7mve2vt01zuv?zs-D4nK05-7SSK2FZAsvumh2w",
    "radio_beat_malayalam": "http://live.exertion.in:8050/radio.mp3",
    "shahul_radio": "https://stream-150.zeno.fm/cynbm5ngx38uv?zs=Ktca5StNRWm-sdIR7GloVg",
    # ... include all other stations
}

# 🔄 Streaming function
def generate_stream(url):
    process = None
    while True:
        if process:
            process.kill()

        process = subprocess.Popen(
            [
                "ffmpeg", "-reconnect", "1", "-reconnect_streamed", "1",
                "-reconnect_delay_max", "10", "-fflags", "nobuffer", "-flags", "low_delay",
                "-i", url, "-vn", "-ac", "1", "-b:a", "24k", "-buffer_size", "1024k", "-f", "mp3", "-"
            ],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=8192
        )

        print(f"🎵 Streaming from: {url} (Mono, 24kbps)")

        try:
            for chunk in iter(lambda: process.stdout.read(8192), b""):
                yield chunk
        except GeneratorExit:
            process.kill()
            break
        except Exception as e:
            print(f"⚠️ Stream error: {e}")

        print("🔄 FFmpeg stopped, restarting stream...")
        time.sleep(5)

# 🌍 API to stream a station
@app.route("/<station_name>")
def stream(station_name):
    url = RADIO_STATIONS.get(station_name)
    if not url:
        return "⚠️ Station not found", 404
    return Response(generate_stream(url), mimetype="audio/mpeg")

# 📄 Paginated list view
@app.route("/")
def index():
    page = int(request.args.get("page", 1))
    per_page = 5  # 5 stations per page
    stations = list(RADIO_STATIONS.items())
    total_pages = (len(stations) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated_stations = stations[start:end]

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Radio Stations</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { padding: 20px; background: #f8f9fa; }
            .station-list { list-style-type: none; padding: 0; }
            .station-list li { background: #fff; margin-bottom: 10px; padding: 15px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        </style>
    </head>
    <body>
        <h2 class="mb-4">🎵 Radio Stations</h2>
        <ul class="station-list">
            {% for name, url in stations %}
            <li>
                <strong>{{ name.replace('_', ' ').title() }}</strong>
                <a href="/{{ name }}" class="btn btn-primary btn-sm float-end">Listen</a>
            </li>
            {% endfor %}
        </ul>

        <nav aria-label="Page navigation">
            <ul class="pagination">
                {% if page > 1 %}
                <li class="page-item"><a class="page-link" href="/?page={{ page-1 }}">Previous</a></li>
                {% endif %}
                {% for p in range(1, total_pages + 1) %}
                <li class="page-item {% if p == page %}active{% endif %}">
                    <a class="page-link" href="/?page={{ p }}">{{ p }}</a>
                </li>
                {% endfor %}
                {% if page < total_pages %}
                <li class="page-item"><a class="page-link" href="/?page={{ page+1 }}">Next</a></li>
                {% endif %}
            </ul>
        </nav>
    </body>
    </html>
    """
    return render_template_string(html, stations=paginated_stations, page=page, total_pages=total_pages)

# 🚀 Launch the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)