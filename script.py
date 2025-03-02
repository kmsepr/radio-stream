import os
import subprocess

# URL of the YouTube video
# youtube_url = "https://m.youtube.com/watch?v=1wECsnGZcf/live"

# Use yt-dlp to extract audio and pipe it to FFmpeg
command = f'yt-dlp -f bestaudio -o - "{youtube_url}" | ffmpeg -i pipe:0 -acodec libmp3lame -b:a 128k -f mp3 pipe:1'

# Run the command
process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Keep running
try:
    while True:
        output = process.stdout.read(1024)
        if not output:
            break
except KeyboardInterrupt:
    process.terminate()
