
# Flask Radio Streamer

This is a lightweight Flask app that streams audio from various online radio stations using FFmpeg. The stream is converted to mono MP3 at 40 kbps and served to any HTTP audio client.

## Features

- Stream from 50+ Malayalam, Islamic, Hindi, and International radio stations
- Converts all sources to MP3 (mono, 40kbps) using FFmpeg
- Auto-restarts FFmpeg on stream failure
- Designed for compatibility with legacy devices and low-bandwidth environments

## Requirements

- Python 3.7+
- FFmpeg installed and accessible from system PATH

## Installation

```bash
git clone https://github.com/yourusername/flask-radio-streamer.git
cd flask-radio-streamer
pip install -r requirements.txt

Running the App

python app.py

By default, the app runs at http://localhost:8000.

Usage

Visit:

http://<your-server>:8000/<station_name>

Example:

http://localhost:8000/muthnabi_radio

You can also view a list of all available stations at:

http://localhost:8000/

Available Stations

A wide range of stations including:

Malayalam: Muthnabi Radio, Radio Keralam, Malayalam 90s, Swaranjali

Islamic: Deenagers Radio, Quran Cairo, Mishary Alafasi, Omar Abdul Kafi Radio

Hindi/Urdu: Nonstop Hindi, Urdu Islamic Lecture, Aaj Tak

News & TV: Manorama News, Victers TV, France 24, Bloomberg TV


For a full list, see the RADIO_STATIONS dictionary in app.py.

Advanced Options (Optional)

You can change stream bitrate and audio channels via query parameters:

http://localhost:8000/muthnabi_radio?bitrate=64k&channels=2

License

MIT License

