try:
    from RGBMatrixEmulator import graphics
except:
    from rgbmatrix import graphics
import requests
import json
import math
import aiohttp
import socket
import os
from datetime import datetime, timedelta,date

class ticktape:
    def __init__(self,x,y,canvas):
        self.x = x
        self.y = y
        self.canvas = canvas
        self.change = True


        self.font= graphics.Font()
        self.font.LoadFont("5x8.bdf")
        self.brightness = 1.0
        self.textColorRaw = graphics.Color(255, 255, 0)
        self.textColor = self.textColorRaw
        self.text = self.get_ip_address()
        self.scrollSpeed = 15

        # articles = open('cachedArticles.json')
        # self.newsJson = json.load(articles)
        # # print("FAILED - using cached stories")
        # self.numOfTitles = len(self.newsJson["articles"])

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    def changed(self):
        change = self.change
        self.change = False
        return change

    def getWidth(self):
        width = len(self.text) * 5
        return width
    
    def setBrightness(self,br):
        self.brightness = br
        self.textColor = graphics.Color(br*self.textColorRaw.red, br*self.textColorRaw.green,br* self.textColorRaw.blue)

    def setTTColor(self, color):
        # print("setting color")
        self.textColorRaw = color
        self.setBrightness(self.brightness)
    
    def setText(self, text):
        self.text = text

    def render(self):
        graphics.DrawText(self.canvas,self.font,math.floor(self.x),self.y,self.textColor,self.text)

    def update(self,dt):  
        self.x = self.x - .3
        # self.x = math.ceil(self.x - 1)
        # print (dt*self.scrollSpeed)
        # if self.x+self.getWidth() <1:
        #     self.x = 128
        self.change = True


import random

class TickerTapeManager:
    def __init__(self,canvas):
        self.queque = [ticktape(128,32,canvas)]
        self.canvas = canvas
        self.change = True
        self.yestarday = "2023-09-06"
        # articles = open('cachedArticles.json')
        self.newsJson = json
        self.brightness = 1
        self.isHidden = False

        with open('cachedArticles.json', 'r') as file:
            # print(json.load(file))
            self.newsJson = json.load(file)
        

    def setBrightness(self,br):
        if self.isHidden:
            return
        self.brightness = br
        for words in self.queque:
            words.setBrightness(br)

    def getBrightness(self):
        return self.brightness

    def setHidden(self):
        self.brightness = 0
        for words in self.queque:
            words.setBrightness(self.brightness)
        self.isHidden = True

    async def refreshInfo(self):
        self.queque[-1].setText(f"ip:{self.queque[0].get_ip_address()} Articles Date: {self.yestarday}")
        await self.getNews()

    async def getNews(self):
        newsApiKey = os.environ["NEWS_API_KEY"]
        if self.yestarday == "2025-08-20":
            return
        #get todays date
        # try:
        print("Getting yestarday's date")
        # async with aiohttp.ClientSession() as session:
        #             async with session.get('http://worldclockapi.com/api/json/est/now') as response:
        #                 todayDate = await response.json()
        #                 todayDate = todayDate['currentDateTime'][0:10]
        # except:
        #     print("COULD NOT GET TODAYS DATE")
        #     todayDate = "2024-12-30"
        # try:
        #     todayDate = requests.get('http://worldclockapi.com/api/json/est/now',timeout=5).json()['currentDateTime'][0:10]
        # except:
        #     try:
        #         todayDate = requests.get('http://worldtimeapi.org/api/timezone/America/New_York',timeout=5).json()['datetime'][0:10]
        #     except:
        #         print("COULD NOT GET TODAYS DATE")
        #         todayDate = "2024-05-05"

        #convert to yestarday's date  because News api doesn't allow for current news
        # yestarday = datetime(int(todayDate[:4]),int(todayDate[5:7]),int(todayDate[8:])) - timedelta(1)
        yestarday = date.today() - timedelta(1)
        print(yestarday)
        if self.yestarday == yestarday:
            return
        self.yestarday = yestarday

        url = ('https://newsapi.org/v2/everything?'
        'from='+str(yestarday)+'&'
        'sortBy=popularity&'
        'page=1&'
        'pageSize=100&'
        'sources=wired,hackaday,abcnews,techcrunch,the-verge,vox&'
        'apiKey='+newsApiKey)

        # try:
        print("getting news stories")
        async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    articles = await response.json()
        # articles = requests.get(url,allow_redirects=True,timeout=5)
        
        print(url)
        try:
            if len(articles["articles"])  == 0:
                issueJson = [articles["status"],articles["code"],articles["message"]]
                self.newsJson[articles] = issueJson
                raise Exception("no articles found")
                
            else:
                self.newsJson = articles
        except:
            "could not get new articles"

            # self.numOfTitles = len(self.newsJson["articles"])
        # except:
        #     articles = open('cachedArticles.json')
        #     self.newsJson = json.load(articles)
        #     print("FAILED - using cached stories")
        #     # self.numOfTitles = len(self.newsJson["articles"])
        
        return

    def getNextInfo(self):
        # Wurd = ["test BUDDYHOLLY"," KING sHIT butt","Hello Worly","heh hehhe HEHEHE HHEHE"]
        # return random.choice(Wurd)
        # newsApiKey = os.getenv("NEWS_API_KEY")
        
        text = ""
        # check = True
        newsList = []
        for r in self.newsJson["articles"]:
            newsList.append(r["title"])
        
        if len(newsList)>0:
            text = random.choice(newsList) + " "
        else:
            text = "ERROR - NO ARTICLES WERE RETRIEVED"
        # randHue = random.uniform(.5,1)
        # if self.queque[-2].textColor == graphics.Color(0,255,255):
        #     self.queque[-1].textColor = graphics.Color(205,205,0)
        #     return text
        possibleColors = [graphics.Color(0,255,255),graphics.Color(0, 150, 255),graphics.Color(0, 163, 108)]
        
        self.queque[-1].setTTColor(random.choice(possibleColors))
        # self.queque[-1].textColor = graphics.Color(int(255 * randHue),int(255 * randHue),0)
        return text

    def update(self,dt):
        #removes parts that have scrolled off screen
        # quequeNum = 0
        # for words in self.queque:
        #     quequeNum = quequeNum + 1 
        #     if words.x + words.getWidth() < 0:
        #         self.queque.pop(quequeNum)
        #         print(quequeNum)
        # if self.queque[0].x + self.queque[0].getWidth() < 0:
        #     del self.queque[0]
            # if words.x + words.getWidth() > 3:
            #     break

        totalWidth = 0
        while totalWidth<228:
            totalWidth = 0
            
            for words in self.queque:
                totalWidth = totalWidth + words.getWidth()
            if totalWidth >228:
                break
            self.queque.append(
                ticktape(self.queque[-1].x+self.queque[-1].getWidth() + 1,
                         32,
                         self.canvas))
            
            # word_site = "https://www.mit.edu/~ecprice/wordlist.10000"

            # response = requests.get(word_site)
            # WORDS = response.content.splitlines()
            # print(WORDS)
            # Wurd = ["test BUDDYHOLLY"," KING sHIT butt","Hello Worly","heh hehhe HEHEHE HHEHE"]
            self.queque[-1].setText(self.getNextInfo())
        
        shuffleCount = 0
        while self.queque[0].getWidth() + self.queque[0].x < 1:
            self.queque = self.queque[1:] + self.queque[:1]
            # Wurd = ["test BUDDY HOLLY"," KING SHIT butt","Hello Worly","heh heh heHEHEHEH HEHE"]
            # self.queque[-1].setText(random.choice(Wurd))
            self.queque[-1].x = self.queque[-2].x + self.queque[-2].getWidth() + 1
            self.queque[-1].setText(self.getNextInfo())
            shuffleCount = shuffleCount + 1 
            if shuffleCount > len(self.queque):
                print("QUEUE IS BROKEN RIP BOZO")
                break


       #UNCOMMENT TO SEE X POSITION OF CURRENT TICKER TAPE 
        # wards  = ""
        # for words in self.queque:
        #     wards = wards + f"({words.x},{words.x+words.getWidth()},{words.text})"

        # print(wards)

        for words in self.queque:
            words.update(dt)
        self.change = True

        # print(len(self.queque))
    
    def render(self):
        for words in self.queque:
            words.render()

    def changed(self):
        change = self.change
        self.change = False
        return change
    
            
