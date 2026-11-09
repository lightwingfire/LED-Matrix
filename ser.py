# import the Flask library
from flask import Flask, render_template, request, jsonify
import os
import re
import threading
from config import PROJECT_DIR, save_weather_location
import socket
class ser():
     
    def __init__(self):
        self.app = Flask(__name__, template_folder=str(PROJECT_DIR / "Templates"))
        self.ip = os.getenv("WEB_HOST", "127.0.0.1")
        self.sliderValue = 100
        self.weatherLocation = os.getenv("WEATHER_LOCATION", "08865")
        self.locationLock = threading.Lock()
        self.app.add_url_rule('/','page',self.page, methods=['GET', 'POST'])
        self.app.add_url_rule('/weather-location', 'weather_location',
                              self.setWeatherLocation, methods=['POST'])
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
            if request.method == 'GET':
                print("this is a test") 
            return render_template("index.html",ip = self.ip, sliderValue = self.sliderValue,
                                   weatherLocation=self.weatherLocation)

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
