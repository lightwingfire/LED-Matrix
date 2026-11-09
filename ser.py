# import the Flask library
from flask import Flask, render_template, request, jsonify
import os
from config import PROJECT_DIR
import socket
class ser():
     
    def __init__(self):
        self.app = Flask(__name__, template_folder=str(PROJECT_DIR / "Templates"))
        self.ip = os.getenv("WEB_HOST", "127.0.0.1")
        self.sliderValue = 100
        self.app.add_url_rule('/','page',self.page, methods=['GET', 'POST'])
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
            return render_template("index.html",ip = self.ip, sliderValue = self.sliderValue)
            
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
