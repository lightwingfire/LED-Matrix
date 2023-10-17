import os
from adafruit_display_text.label import Label
import displayio
from adafruit_matrixportal.matrix import Matrix
import adafruit_requests
import terminalio
from adafruit_datetime import datetime
import json

class weather:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        # self.newsLabel = Label(font = terminalio.FONT)
        # self.temp
        self.tempLabel = Label(font = terminalio.FONT)
        self.tempLabel.x = self.x-1
        self.tempLabel.y = self.y + 4
        self.tempLabel.y = self.y + 4
        self.tempLabel.text = "##"
        self.temp = ""

        self.dayLabel = Label(font = terminalio.FONT)
        self.dayLabel.x = x-1
        self.dayLabel.y = y+15


        self.bitmap_file = open("day\\weatherspritesheet.bmp", "rb")
        self.bitmap = displayio.OnDiskBitmap(self.bitmap_file)
        self.sprite = displayio.TileGrid(
            self.bitmap,
            pixel_shader=self.bitmap.pixel_shader,
            width=1,
            height=1,
            tile_width=10,
            tile_height=10
        )
        self.sprite.x = self.x
        self.sprite.y = self.y
        self.sprite.hidden = True
        
        self.lastRefreshed = 0
        self.lastChanged = 0
        self.time = 0

        self.allHidden = False


    def setDay(self, day):
        self.day = day

    def getWeekDay(self, day = '2023-10-17'):
        # format YYYY-MM-DD
        
        dayConverted = datetime(int(day[:4]),int(day[5:7]),int(day[8:11]))

        #try:
            #todayDate = self.requests.get('http://worldclockapi.com/api/json/est/now').json()['currentDateTime'][0:10]
        #except:
            #todayDate = "2023-09-06"
        # print (f"date:{dayConverted} today:{datetime(int(todayDate[:4]),int(todayDate[5:7]),int(todayDate[9:]))}")
        #if dayConverted == datetime(int(todayDate[:4]),int(todayDate[5:7]),int(todayDate[9:])):
            #self.day = "TD"
            #return
        print(f"day:{dayConverted}")
        weekDay = dayConverted.weekday()

        if weekDay == 0:
            self.dayLabel.text = "MO"
        if weekDay == 1:
            self.dayLabel.text = "TU"
        if weekDay == 2:
            self.dayLabel.text = "WD"
        if weekDay == 3:
            self.dayLabel.text = "TH"
        if weekDay == 4:
            self.dayLabel.text = "FR"
        if weekDay == 5:
            self.dayLabel.text = "SA"
        if weekDay == 6:
            self.dayLabel.text = "SU"


    def setRequest(self, requests):
        self.requests = requests

    def getLastRefreshed(self):
        return self.lastRefreshed

    def setLastRefreshed(self, lastRefreshed):
        self.lastRefreshed = lastRefreshed

    def getWeather(self,l):
        # api_key = os.getenv("WEATHERAPI_KEY")
        # location = os.getenv("WEATHER_LOCATION")
        # # url = f'http://api.weatherapi.com/v1/current.json?key={api_key}&q={location}'
        # url = f'http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days=3&aqi=no&alerts=no'
        # l = self.requests.get(url)
        try:
            if self.day == 0:
                self.getWeekDay(l.json()["current"]["last_updated"])
                print(l.json()["current"]["temp_f"])
                self.temp = str(l.json()["current"]["temp_f"])[:2]

                self.tempLabel.text = self.temp
                # self.dayLabel.text = self.day
                self.load_image(l.json()["current"][ "condition"]["code"])
                return
            
            forecast = l.json()["forecast"]["forecastday"][self.day]
            self.getWeekDay(forecast["date"])
            self.temp = str(forecast["day"]["maxtemp_f"])[:2]

            self.tempLabel.text = self.temp
            # self.dayLabel.text = self.day
            self.load_image(forecast["day"]["condition"]["code"])
        except:
            self.temp = '##'
            self.tempLabel.text = self.temp
            self.load_image()
            print("COULD NOT LOAD WEATHER")


    def setOff(self):
        if self.allHidden == False:
            self.allHidden = True
            self.tempLabel.hidden = True
            self.dayLabel.hidden = True
            self.sprite.hidden = True
        return

    def setOn(self):
        if self.allHidden == True:
            self.allHidden = False
            self.tempLabel.hidden = False
            self.dayLabel.hidden = False
            self.sprite.hidden = True
        return
        #self.tempLabel.hidden = True
        #self.dayLabel.hidden = True

    def load_image(self, status = 1000):
        codes = open('weather_conditions.json')
        codesJson = json.load(codes)

        for i in codesJson:
            if i["code"] == status:
                print(f"condidtion:{i['day']}")
                self.sprite[0] = i["spritesheet"]
                # filePath = "day\\" + str(i['icon']) + ".bmp"
                # print(filePath)
                # self.bitmap_file.close()
                # self.bitmap_file = open(filePath, "rb")
                # self.bitmap = displayio.OnDiskBitmap(self.bitmap_file)
                # self.sprite = displayio.TileGrid(
                #     self.bitmap,
                #     pixel_shader=self.bitmap.pixel_shader,
                #     tile_width=self.bitmap.width,
                #     tile_height=self.bitmap.height
                # )
                # self.sprite.x = self.x
                # self.sprite.y = self.y
                # self.sprite.hidden = True
                return

        #self.bitmap_file = open("cloudy.bmp", "rb")
        sprite = displayio.TileGrid(
            self.bitmap,
            pixel_shader=self.bitmap.pixel_shader,
            tile_width=self.bitmap.width,
            tile_height=self.bitmap.height
        )
        self.sprite = sprite

    def getDisplay(self):
        return[self.sprite,self.tempLabel, self.dayLabel]

    def updateWeather(self,dt):
        if self.allHidden:
            return
        self.time = self.time + dt
        #print(self.tempLabel.hidden)
        if dt*60*3< self.time:
            self.time = 0
            # print("blink")
            #self.lastChanged = 0
            # self.tempLabel.hidden = not self.tempLabel.hidden
            if self.sprite.hidden:
                self.sprite.hidden = False
                self.tempLabel.hidden = True
            else:
                self.sprite.hidden = True
                self.tempLabel.hidden = False
        # self.tempLabel.text = self.temp
        # if self.tempLabel.text !=86:
            # print("test")
            # self.tempLabel.hidden = True
        return
