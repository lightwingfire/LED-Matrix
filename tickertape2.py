import json
from adafruit_datetime import datetime, timedelta
# import datetime
import math
from adafruit_display_text.label import Label
import terminalio
import os
import adafruit_requests

class tickertape:

    def __init__(self, x , y):
        self.x = x
        self.y = y
        self.newsLabel = Label(font = terminalio.FONT)
        self.newsLabel.y = self.y
        self.newsLabel.x = self.x = x
        self.color = 0xffffdd
        self.newsLabel.color = self.color

        self.newsLabel2 = Label(font = terminalio.FONT)
        self.newsLabel2.y = self.y
        self.newsLabel2.x = self.newsLabel.x + self.newsLabel.width

        self.color2 = 0xffffff
        self.newsLabel2.color = self.color2

        self.numOfTitles = 0

        self.r = 2
        self.crawlSpeed = 35

        self.lastRefreshed = 0

    def setRequests(self, requests):
        self.requests = requests

    def getArticles(self):
        newsApiKey = os.getenv("NEWS_API_KEY")

        #get todays date
        try:
            todayDate = self.requests.get('http://worldclockapi.com/api/json/est/now').json()['currentDateTime'][0:10]
        except:
            try:
                todayDate = self.requests.get('http://worldtimeapi.org/api/timezone/America/New_York').json()['datetime'][0:10]
            except:
                print("COULD NOT GET TODAYS DATE")
                todayDate = "2023-09-06"

        #convert to yestarday's date  because News api doesn't allow for current news
        yestarday = datetime(int(todayDate[:4]),int(todayDate[5:7]),int(todayDate[8:])) - timedelta(1)
        print(f"yestarday:{yestarday.date()}")

        url = ('https://newsapi.org/v2/everything?'
        'from='+str(yestarday.date())+'&'
        'sortBy=popularity&'
        'page=1&'
        'pageSize=100&'
        'sources=wired,hackaday,abcnews,techcrunch,the-verge,vox&'
        'apiKey='+newsApiKey)

        try:
            articles = self.requests.get(url,allow_redirects=True)
            self.newsJson = articles.json()
            print("getting news stories")
            self.numOfTitles = len(self.newsJson["articles"])
        except:
            articles = open('r.json')
            self.newsJson = json.load(articles)
            print("FAILED - using cached stories")
            self.numOfTitles = len(self.newsJson["articles"])
            

        self.r = 0

        newsTitle = self.newsJson["articles"][self.r]["title"]+"||"
        newsAuthor = str(self.newsJson["articles"][self.r]["source"]["name"])
        self.newsLabel.text = newsTitle.upper() + newsAuthor.upper()

        self.r = 1

        newsTitle2 = str(self.newsJson["articles"][self.r]["title"]+"||")
        newsAuthor2 = str(self.newsJson["articles"][self.r]["source"]["name"])
        self.newsLabel2.text = newsTitle2.upper() + newsAuthor2.upper()
        
        self.r = 2

    def getLabels(self):
        return [self.newsLabel, self.newsLabel2]

    def getLastRefreshed(self):
        return self.lastRefreshed

    def setLastRefreshed(self, refreshed):
        self.lastRefreshed = refreshed

    def updateNews(self,dt):

        self.newsLabel.x =  math.ceil(self.newsLabel.x - self.crawlSpeed*dt)
        if self.newsLabel.x < -30 - self.newsLabel.width:
            self.newsLabel.x = self.newsLabel2.x + self.newsLabel2.width + 3
            newsTitle = self.newsJson["articles"][self.r]["title"]+"||"
            newsAuthor = str(self.newsJson["articles"][self.r]["source"]["name"])
            self.newsLabel.text = newsTitle.upper() + newsAuthor.upper()
            self.r = self.r + 1
            # print("refreshing")

        self.newsLabel2.x = math.ceil(self.newsLabel2.x - self.crawlSpeed*dt)
        if self.newsLabel2.x < -30 - self.newsLabel2.width:
            self.newsLabel2.x = self.newsLabel.x + self.newsLabel.width + 3
            newsTitle2 = str(self.newsJson["articles"][self.r]["title"]+"||")
            newsAuthor2 = str(self.newsJson["articles"][self.r]["source"]["name"])
            self.newsLabel2.text = newsTitle2.upper() + newsAuthor2.upper()
            self.r = self.r + 1
            # print("refreshing")

        if self.r==self.numOfTitles:
            self.r = 0

    def fadeOff(self):

        if self.color < 1:
            return
        factor = 0.005

        red = (self.color >> 16) & 0xFF
        green = (self.color >> 8) & 0xFF
        blue = self.color & 0xFF

        red = max(0, red - int(255 * factor))
        green = max(0, green - int(255 * factor))
        blue = max(0, blue - int(255 * factor))

        reduced_color_int = (red << 16) | (green << 8) | blue


        reduced_color = "0x{:06X}".format(reduced_color_int)
        print(reduced_color)
        self.color = int(reduced_color,16)
        self.newsLabel.color = self.color
        self.newsLabel2.color = self.color

    def fadeIn(self):
        if self.color >= 0xFFFFDD:
            return
        factor = 0.005

        red = (self.color >> 16) & 0xFF
        green = (self.color >> 8) & 0xFF
        blue = self.color & 0xFF

        red = max(0, red + int(255 * factor))
        green = max(0, green + int(255 * factor))
        blue = max(0, blue + int(255 * factor))

        reduced_color_int = (red << 16) | (green << 8) | blue


        reduced_color = "0x{:06X}".format(reduced_color_int)
        print(reduced_color)

        self.color = int(reduced_color,16)

        self.newsLabel.color = self.color
        self.newsLabel2.color = self.color




