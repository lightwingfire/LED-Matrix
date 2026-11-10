# import the Flask library
from flask import Flask, render_template, request, jsonify
import os
import re
import threading
import time
from urllib.parse import urlsplit
from config import PROJECT_DIR, save_weather_location
import socket
class ser():
     
    def __init__(self):
        self.app = Flask(__name__, template_folder=str(PROJECT_DIR / "Templates"),
                         static_folder=str(PROJECT_DIR / "static"))
        self.ip = os.getenv("WEB_HOST", "127.0.0.1")
        self.sliderValue = 100
        self.tickerSpeed = 18
        self.tickerEnabled = True
        self.fishMode = False
        self.shadowMode = False
        self.lastFrame = None
        self.sandLock = threading.Lock()
        self.sandRequested = False
        self.fishLock = threading.Lock()
        self.fishRequested = False
        self.fishes = []
        self.fishCommands = []
        self.weatherLocation = os.getenv("WEATHER_LOCATION", "08865")
        self.locationLock = threading.Lock()
        self.newsLock = threading.Lock()
        self.news = dict(articles=[], updatedAt=None, cached=True, error=None)
        self.app.add_url_rule('/','page',self.page, methods=['GET', 'POST'])
        self.app.add_url_rule('/weather-location', 'weather_location',
                              self.setWeatherLocation, methods=['POST'])
        self.app.add_url_rule('/news', 'news', self.getNews, methods=['GET'])
        self.app.add_url_rule('/ticker-speed', 'ticker_speed', self.setTickerSpeed,
                              methods=['GET', 'POST'])
        self.app.add_url_rule('/ticker-enabled', 'ticker_enabled', self.setTickerEnabled,
                              methods=['GET', 'POST'])
        self.app.add_url_rule('/fish-mode', 'fish_mode', self.setFishMode,
                              methods=['GET', 'POST'])
        self.app.add_url_rule('/health', 'health', self.getHealth, methods=['GET'])
        self.app.add_url_rule('/aquarium/sand', 'generate_sand', self.requestSand,
                              methods=['POST'])
        self.app.add_url_rule('/aquarium/fish', 'generate_fish', self.requestFish,
                              methods=['POST'])
        self.app.add_url_rule('/aquarium/shadow', 'shadow_mode', self.setShadowMode,
                              methods=['GET', 'POST'])
        self.app.add_url_rule('/aquarium/fishes', 'fishes', self.manageFish,
                              methods=['GET', 'POST'])
        self.app.add_url_rule('/aquarium/fishes/<int:fish_id>/regenerate', 'regenerate_fish',
                              self.requestFishRegeneration, methods=['POST'])
        self.app.add_url_rule('/aquarium/fishes/<int:fish_id>', 'delete_fish',
                              self.requestFishDeletion, methods=['DELETE'])
        # threading.Thread(target=self.start()).start()
        # self.start()

    def start(self):
        self.app.run(debug=False, use_reloader=False, host=self.ip,
                     port=int(os.getenv("WEB_PORT", "5000")))
        

    # @app.route('/', methods=['GET', 'POST'])
    def page(self):
            if request.method == 'POST':
                self.sliderValue = max(0, min(100, int(request.get_json()['out'])))
                return jsonify(out=self.sliderValue)
            return render_template("index.html", initial_state=dict(
                ip=self.ip, brightness=self.sliderValue, weatherLocation=self.weatherLocation,
                news=self.newsSnapshot(), tickerSpeed=self.tickerSpeed,
                tickerEnabled=self.tickerEnabled, fishMode=self.fishMode,
                shadowMode=self.shadowMode, fishes=self.fishSnapshot()))

    def setFishStats(self, fishes):
        with self.fishLock:
            self.fishes = [dict(fish) for fish in fishes]

    def fishSnapshot(self):
        with self.fishLock:
            return [dict(fish) for fish in self.fishes]

    def manageFish(self):
        if request.method == 'POST':
            if not self.fishMode:
                return jsonify(error="Turn on FISH mode first."), 409
            with self.fishLock:
                self.fishCommands.append(dict(action='add'))
            return jsonify(queued=True), 202
        response = jsonify(fishes=self.fishSnapshot())
        response.headers['Cache-Control'] = 'no-store'
        return response

    def requestFishRegeneration(self, fish_id):
        if not self.fishMode:
            return jsonify(error="Turn on FISH mode first."), 409
        with self.fishLock:
            if not any(fish['id'] == fish_id for fish in self.fishes):
                return jsonify(error="Fish not found."), 404
            self.fishCommands.append(dict(action='regenerate', id=fish_id))
        return jsonify(queued=True), 202

    def consumeFishCommands(self):
        with self.fishLock:
            commands = self.fishCommands
            self.fishCommands = []
        return commands

    def requestFishDeletion(self, fish_id):
        if not self.fishMode:
            return jsonify(error="Turn on FISH mode first."), 409
        with self.fishLock:
            if not any(fish['id'] == fish_id for fish in self.fishes):
                return jsonify(error="Fish not found."), 404
            self.fishCommands.append(dict(action='delete', id=fish_id))
        return jsonify(queued=True), 202

    def getShadowMode(self):
        return self.shadowMode

    def setShadowMode(self):
        if request.method == 'POST':
            data = request.get_json(silent=True)
            enabled = data.get('enabled') if isinstance(data, dict) else None
            if type(enabled) is not bool:
                return jsonify(error="Enabled must be true or false."), 400
            self.shadowMode = enabled
        return jsonify(enabled=self.shadowMode)

    def getFishMode(self):
        return self.fishMode

    def reportFrame(self):
        self.lastFrame = time.monotonic()

    def getHealth(self):
        last_frame = self.lastFrame
        running = last_frame is not None and time.monotonic() - last_frame < 3
        response = jsonify(displayRunning=running)
        response.headers['Cache-Control'] = 'no-store'
        return response, 200 if running else 503

    def requestSand(self):
        if not self.fishMode:
            return jsonify(error="Turn on FISH mode first."), 409
        with self.sandLock:
            self.sandRequested = True
        return jsonify(queued=True), 202

    def consumeSandRequest(self):
        with self.sandLock:
            requested = self.sandRequested
            self.sandRequested = False
        return requested

    def requestFish(self):
        if not self.fishMode:
            return jsonify(error="Turn on FISH mode first."), 409
        with self.fishLock:
            self.fishRequested = True
        return jsonify(queued=True), 202

    def consumeFishRequest(self):
        with self.fishLock:
            requested = self.fishRequested
            self.fishRequested = False
        return requested

    def setFishMode(self):
        if request.method == 'POST':
            data = request.get_json(silent=True)
            enabled = data.get('enabled') if isinstance(data, dict) else None
            if type(enabled) is not bool:
                return jsonify(error="Enabled must be true or false."), 400
            self.fishMode = enabled
        return jsonify(enabled=self.fishMode)

    def getTickerEnabled(self):
        return self.tickerEnabled

    def setTickerEnabled(self):
        if request.method == 'POST':
            data = request.get_json(silent=True)
            enabled = data.get('enabled') if isinstance(data, dict) else None
            if type(enabled) is not bool:
                return jsonify(error="Enabled must be true or false."), 400
            self.tickerEnabled = enabled
        return jsonify(enabled=self.tickerEnabled)

    def getTickerSpeed(self):
        return self.tickerSpeed

    def setTickerSpeed(self):
        if request.method == 'POST':
            data = request.get_json(silent=True)
            speed = data.get('speed') if isinstance(data, dict) else None
            if type(speed) is not int or not 0 <= speed <= 100:
                return jsonify(error="Choose a speed from 0 to 100 pixels per second."), 400
            self.tickerSpeed = speed
        return jsonify(speed=self.tickerSpeed)

    def setNews(self, data, updated_at=None, cached=True, error=None):
        articles = []
        for article in data.get("articles", []):
            if not isinstance(article, dict):
                continue
            title = article.get("title")
            if not isinstance(title, str) or not title.strip() or title.strip() == "[Removed]":
                continue
            url = article.get("url")
            try:
                parsed = urlsplit(url) if isinstance(url, str) else None
                if not parsed or parsed.scheme not in ("http", "https") or not parsed.netloc:
                    url = None
            except ValueError:
                url = None
            source = article.get("source")
            source = source.get("name") if isinstance(source, dict) else None
            published = article.get("publishedAt")
            articles.append(dict(title=title, url=url,
                                 source=source if isinstance(source, str) else "",
                                 publishedAt=published if isinstance(published, str) else ""))
        with self.newsLock:
            self.news = dict(articles=articles, updatedAt=updated_at,
                             cached=cached, error=error)

    def newsSnapshot(self):
        with self.newsLock:
            return self.news

    def getNews(self):
        response = jsonify(self.newsSnapshot())
        response.headers["Cache-Control"] = "no-store"
        return response

    def getWeatherLocation(self):
        return self.weatherLocation

    def setWeatherLocation(self):
        data = request.get_json(silent=True)
        location = data.get("zipcode") if isinstance(data, dict) else None
        if not isinstance(location, str):
            return jsonify(error="Enter a five-digit ZIP code, such as 08865."), 400
        location = location.strip()
        if not re.fullmatch(r"[0-9]{5}(?:-[0-9]{4})?", location):
            return jsonify(error="Enter a five-digit ZIP code or ZIP+4."), 400
        with self.locationLock:
            try:
                save_weather_location(location)
            except OSError:
                return jsonify(error="Could not save the ZIP code. Check settings.toml permissions."), 500
            self.weatherLocation = location
        return jsonify(zipcode=location)
            
    def getSlider(self):
        if self.sliderValue <1:
             return self.sliderValue
        return  self.sliderValue/100
    
# t = ser()
    # # Start with flask web app with debug as True only 
    # # if this is the starting page
    # if(__name__ == "__main__"):
        


# import http.server
# import socketserver

# #here you create a new handler, you had a new way to handle get request
# class Handler(http.server.SimpleHTTPRequestHandler):
#     def do_GET(self):
#        #this code execute when a GET request happen, then you have to check if the request happenned because the user pressed the button
#         if self.path.find("isButtonPressed=true") != -1:
#             print("Button clicked")
#             #do whatever you want
#         return super().do_GET()
#     def do_POST(self):
#         print ("post")
#     def do_PUT(self):
#         print ("put")
# PORT = 8080
# myHandler = Handler


# with socketserver.TCPServer(("", PORT), myHandler) as httpd:
#     print("serving at port", PORT)
#     httpd.serve_forever()
