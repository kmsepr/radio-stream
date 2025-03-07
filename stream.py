import subprocess
import time
import threading
from flask import Flask, Response

app = Flask(__name__)

# 📡 List of YouTube Live Streams
YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/@MediaoneTVLive/live",
    "shajahan_rahmani": "https://www.youtube.com/@ShajahanRahmaniOfficial/live",
    "qsc_mukkam": "https://www.youtube.com/c/quranstudycentremukkam/live",
    "valiyudheen_faizy": "https://www.youtube.com/@voiceofvaliyudheenfaizy600/live",
    "skicr_tv": "https://www.youtube.com/@SKICRTV/live",
    "yaqeen_institute": "https://www.youtube.com/@yaqeeninstituteofficial/live",
    "bayyinah_tv": "https://www.youtube.com/@bayyinah/live",
}

# 🔄 Caching latest stream URLs to avoid frequent yt-dlp calls
stream_cache = {}

def get_audio_url(youtube_url):
    """Fetches and caches the latest direct audio URL from YouTube."""
    if youtube_url in stream_cache and time.time() - stream_cache[youtube_url]["time"] < 300:
        return stream_cache[youtube_url]["url"]  # Return cached URL if it's still valid

    command = [
        "yt-dlp",
        "--cookies", "/mnt/data/cookies.txt",
        "--force-generic-extractor",
        "-f", "91",  # Audio format
        "-g", youtube_url
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        audio_url = result.stdout.strip() if result.stdout else None
        if audio_url:
            stream_cache[youtube_url] = {"url": audio_url, "time": time.time()}  # Update cache
        return audio_url
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error fetching audio URL: {e}")
        return None

def generate_stream(youtube_url):
    """Streams audio using FFmpeg."""
    while True:
        stream_url = get_audio_url(youtube_url)
        if not stream_url:
            print("⚠️ Failed to fetch stream URL")
            return

        process = subprocess.Popen(
            ["ffmpeg", "-re", "-i", stream_url,
             "-vn", "-acodec", "libmp3lame", "-b:a", "64k",
             "-buffer_size", "1024k", "-f", "mp3", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=8192
        )

        print(f"🎵 Streaming from: {youtube_url}")

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

@app.route("/play/<station_name>")
def stream(station_name):
    youtube_url = YOUTUBE_STREAMS.get(station_name)
    if not youtube_url:
        return "⚠️ Station not found", 404

    return Response(generate_stream(youtube_url), mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)