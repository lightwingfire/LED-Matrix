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
from datetime import datetime, timedelta,date, timezone

class ticktape:
    def __init__(self,x,y,canvas):
        self.x = x
        self.y = y
        self.canvas = canvas
        self.change = True
        self.kind = 'news'


        self.font= graphics.Font()
        self.font.LoadFont("5x8.bdf")
        self.brightness = 1.0
        self.textColorRaw = graphics.Color(255, 255, 0)
        self.textColor = self.textColorRaw
        self.text = self.get_ip_address()
        self.scrollSpeed = 18

        # articles = open('cachedArticles.json')
        # self.newsJson = json.load(articles)
        # # print("FAILED - using cached stories")
        # self.numOfTitles = len(self.newsJson["articles"])

    def get_ip_address(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"

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

    def render(self, canvas=None):
        canvas = canvas if canvas is not None else self.canvas
        x = math.floor(self.x)
        text = self.text
        if text.startswith('🎵 '):
            # The BDF font has no emoji glyph: draw a small musical note in pixels.
            note = ('00111', '00101', '00101', '00101', '11101', '11111', '00011')
            for row, pixels in enumerate(note):
                for column, pixel in enumerate(pixels):
                    if pixel == '1' and 0 <= x + column < canvas.width:
                        canvas.SetPixel(x + column, self.y - 7 + row,
                                        self.textColor.red, self.textColor.green, self.textColor.blue)
            x += 10
            text = text[2:]
        graphics.DrawText(canvas, self.font, x, self.y, self.textColor, text)

    def update(self,dt):  
        self.x -= self.scrollSpeed * dt
        # self.x = math.ceil(self.x - 1)
        # print (dt*self.scrollSpeed)
        # if self.x+self.getWidth() <1:
        #     self.x = 128
        self.change = True


import random

class TickerTapeManager:
    def __init__(self,canvas):
        self.scrollSpeed = 18
        self.queque = [ticktape(128,32,canvas)]
        self.canvas = canvas
        self.change = True
        self.yestarday = "2023-09-06"
        # articles = open('cachedArticles.json')
        self.newsJson = json
        self.brightness = 1
        self.isHidden = False
        self.newsUpdatedAt = None
        self.newsCached = True
        self.newsPlaylist = []
        self.newsPlaylistSource = ()
        self.lastHeadline = None
        self.nowPlaying = None
        self.spotifyNext = False

        with open('cachedArticles.json', 'r') as file:
            # print(json.load(file))
            self.newsJson = json.load(file)
        

    def setSpeed(self, speed):
        self.scrollSpeed = speed

    def setBrightness(self,br):
        self.brightness = br
        for words in self.queque:
            words.setBrightness(br)

    def getBrightness(self):
        return self.brightness

    def setHidden(self):
        self.setEnabled(False)

    def setEnabled(self, enabled):
        hidden = not enabled
        if self.isHidden != hidden:
            self.isHidden = hidden
            self.change = True

    async def refreshInfo(self):
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

        url = ('https://newsapi.org/v2/everything?'
        'from='+str(yestarday)+'&'
        'sortBy=popularity&'
        'page=1&'
        'pageSize=100&'
        'sources=wired,hackaday,abcnews,techcrunch,the-verge,vox&'
        'apiKey='+newsApiKey)

        # try:
        print("getting news stories")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url) as response:
                    articles = await response.json()
        # articles = requests.get(url,allow_redirects=True,timeout=5)
        
        print("News response received")
        if articles.get("status") != "ok" or not isinstance(articles.get("articles"), list):
            raise ValueError("News provider returned an unsuccessful response")
        if not articles["articles"]:
            raise ValueError("News provider returned no stories")
        self.newsJson = articles
        self.yestarday = yestarday
        self.newsUpdatedAt = datetime.now(timezone.utc).isoformat()
        self.newsCached = False

            # self.numOfTitles = len(self.newsJson["articles"])
        # except:
        #     articles = open('cachedArticles.json')
        #     self.newsJson = json.load(articles)
        #     print("FAILED - using cached stories")
        #     # self.numOfTitles = len(self.newsJson["articles"])
        
        return

    def setNowPlaying(self, text):
        """Insert a green music entry next, keeping queued news and scroll position."""
        if not isinstance(text, str):
            text = None
        if text == self.nowPlaying:
            return
        self.nowPlaying = text
        self.queque = [words for words in self.queque if words.kind != 'spotify']
        # Removing or changing a music item must not leave gaps in the queue.
        for previous, words in zip(self.queque, self.queque[1:]):
            words.x = previous.x + previous.getWidth() + 1
        if text:
            index = next((i for i, words in enumerate(self.queque) if words.x >= 128), len(self.queque))
            x = max(128, self.queque[index - 1].x + self.queque[index - 1].getWidth() + 1) if index else 128
            words = ticktape(x, 32, self.canvas)
            words.kind = 'spotify'
            words.setText(text + ' ')
            words.setTTColor(graphics.Color(30, 215, 96))
            words.setBrightness(self.brightness)
            self.queque.insert(index, words)
            for previous, following in zip(self.queque[index:], self.queque[index + 1:]):
                following.x = previous.x + previous.getWidth() + 1
        if not self.queque:
            self.queque.append(ticktape(128, 32, self.canvas))
            self.queque[-1].setText(self.getNextInfo())
        self.spotifyNext = False
        self.change = True

    def getNextInfo(self):
        if self.nowPlaying and self.spotifyNext:
            self.spotifyNext = False
            self.queque[-1].kind = 'spotify'
            self.queque[-1].setTTColor(graphics.Color(30, 215, 96))
            self.queque[-1].setBrightness(self.brightness)
            return self.nowPlaying + ' '
        self.spotifyNext = bool(self.nowPlaying)
        self.queque[-1].kind = 'news'
        # Deduplicate and validate titles before building a complete rotation.
        headlines = []
        for article in self.newsJson.get("articles", []):
            title = article.get("title") if isinstance(article, dict) else None
            if isinstance(title, str) and title.strip() and title.strip() != "[Removed]":
                headlines.append(title.strip())
        source = tuple(dict.fromkeys(headlines))
        if source != self.newsPlaylistSource:
            self.newsPlaylistSource = source
            self.newsPlaylist = []

        if not source:
            return "ERROR - NO ARTICLES WERE RETRIEVED "
        if not self.newsPlaylist:
            self.newsPlaylist = list(source)
            random.shuffle(self.newsPlaylist)
            # Avoid repeating the same headline across two rotations.
            if len(self.newsPlaylist) > 1 and self.newsPlaylist[-1] == self.lastHeadline:
                self.newsPlaylist[0], self.newsPlaylist[-1] = self.newsPlaylist[-1], self.newsPlaylist[0]
        self.lastHeadline = self.newsPlaylist.pop()
        text = self.lastHeadline + " "
        possibleColors = [graphics.Color(0,255,255),graphics.Color(0, 150, 255),graphics.Color(0, 163, 108)]
        
        self.queque[-1].setTTColor(random.choice(possibleColors))
        self.queque[-1].setBrightness(self.brightness)
        return text

    def update(self,dt):
        if self.isHidden:
            return
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
            self.queque[-1].x = (self.queque[-2].x + self.queque[-2].getWidth() + 1
                                   if len(self.queque) > 1 else 128)
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
            words.scrollSpeed = self.scrollSpeed
            words.update(dt)
        self.change = True

        # print(len(self.queque))
    
    def render(self, canvas=None):
        if self.isHidden:
            return
        for words in self.queque:
            words.render(canvas)

    def changed(self):
        change = self.change
        self.change = False
        return change
    
            
