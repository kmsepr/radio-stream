import subprocess
import time
import json
import urllib.request
import threading
import re
import os
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
    # 1. AIR Section (Populated dynamically from GitHub on startup)
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
        "media_one": {"title": "Media One", "url": "
