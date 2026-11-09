try:
    from RGBMatrixEmulator import graphics
except:
    from rgbmatrix import graphics
from datetime import date
from PIL import Image
import json
import aiohttp
from drawGraphics import drawGraphic

class weather:
    def __init__(self,x,y,canvas):
        self.x = x
        self.y = y
        self.canvas = canvas
        self.font= graphics.Font()
        self.font.LoadFont("5x8.bdf")
        self.textColor = graphics.Color(255, 255, 0)
        self.sprite = drawGraphic(self.x,self.y,10,10,self.canvas)
        # self.sprite = Image.open('day\\113.bmp')
        self.text = "50"
        self.date = '2023-10-17'
        self.weekDay = "MO"
        self.temp = "50"
        self.hidden = True
        self.brightness = 1

    def setWeatherIcon(self, status = 1000):
        codes = open('weather_conditions.json')
        codesJson = json.load(codes)

        for i in codesJson:
            if status == i['code']:
                # self.sprite = Image.open(f'day\\{str(i["icon"])}.bmp')
                self.sprite.loadImage(f'day/{str(i["icon"])}.bmp')
                # print("HEEEEEEERRRRREEEEEEE")
                return

    def setBrightness(self,br):
        self.brightness = br
        if self.hidden:
            return
        
        self.textColor = graphics.Color(br *255, br* 255, br* 0)
        self.sprite.setBrightness(br)

    def setDay(self, day = '2023-10-17'):
        self.date = day
        dayConverted = date(int(day[:4]),int(day[5:7]),int(day[8:11]))
        weekDay = dayConverted.weekday()
        if weekDay == 0:
            self.weekDay = "MO"
        elif weekDay == 1:
            self.weekDay = "TU"
        elif weekDay == 2:
            self.weekDay = "WD"
        elif weekDay == 3:
            self.weekDay = "TH"
        elif weekDay == 4:
            self.weekDay = "FR"
        elif weekDay == 5:
            self.weekDay = "SA"
        elif weekDay == 6:
            self.weekDay = "SU"
        else:
            self.weekDay = "NA"

    def setTemp(self,temp):
        self.temp = temp

    def setHidden(self, state):
        self.hidden = state
        if self.hidden:
            self.textColor = graphics.Color(0 *255, 0* 255, 0* 0)
            self.sprite.setBrightness(0)
        else:
            self.setBrightness(self.brightness)

    def render(self, canvas=None):
        canvas = canvas if canvas is not None else self.canvas
        graphics.DrawText(canvas,self.font,self.x,self.y+21,self.textColor,self.temp)
        self.sprite.toCanvas(canvas)

    def update(self):
        # self.setWeatherIcon(1006)
        graphics.DrawText(self.canvas,self.font,self.x,self.y+21,self.textColor,self.temp)
        self.sprite.toCanvas()
        # self.canvas.SetImage(self.sprite.convert('RGB'),self.x,self.y)

import time
class weatherToday:
    def __init__(self,canvas):
        # self.x = x
        # self.y = y
        self.canvas = canvas
        self.font= graphics.Font()
        self.font.LoadFont("5x8.bdf")
        self.textColorDay = graphics.Color(190, 190, 190)
        self.textColorOdd = graphics.Color(255, 165, 0)
        self.textColor = graphics.Color(255, 255, 0)
        self.spriteNow = drawGraphic(69, 1,10,10,self.canvas)
        self.text = "50"
        self.date = '2023-10-17'
        self.weekDay = "MON"
        self.tempNow = "50"

        self.textTime1 = "00"
        self.temp1 = "50"
        self.sprite1 = drawGraphic(86, 1,10,10,self.canvas)

        self.textTime2 = "00"
        self.temp2 = "50"
        self.sprite2 = drawGraphic(97, 1,10,10,self.canvas)

        self.textTime3 = "00"
        self.temp3 = "50"
        self.sprite3 = drawGraphic(107, 1,10,10,self.canvas)

        self.textTime4 = "00"
        self.temp4 = "50"
        self.sprite4 = drawGraphic(118, 1,10,10,self.canvas)


    def setWeatherIcon(self, status = 1000):
        codes = open('weather_conditions.json')
        codesJson = json.load(codes)

        for i in codesJson:
            if status == i['code']:
                # self.sprite = Image.open(f'day\\{str(i["icon"])}.bmp')
                self.spriteNow.loadImage(f'day/{str(i["icon"])}.bmp')
                # print("HEEEEEEERRRRREEEEEEE")
                return
            
    def setWeatherIcon(self, status, sprite):
        codes = open('weather_conditions.json')
        codesJson = json.load(codes)

        for i in codesJson:
            if status == i['code']:
                # self.sprite = Image.open(f'day\\{str(i["icon"])}.bmp')
                sprite.loadImage(f'day/{str(i["icon"])}.bmp')
                # print("HEEEEEEERRRRREEEEEEE")
                return

    def setBrightness(self,br):
        self.textColor = graphics.Color(br *255, br* 255, br* 0)
        self.textColorDay = graphics.Color(br *190,br * 190,br * 190)
        self.textColorOdd = graphics.Color(br *255,br * 165,br * 0)
        self.spriteNow.setBrightness(br)
        self.sprite1.setBrightness(br)
        self.sprite2.setBrightness(br)
        self.sprite3.setBrightness(br)
        self.sprite4.setBrightness(br)

    def setDay(self, day = '2023-10-17'):
        self.date = day
        dayConverted = date(int(day[:4]),int(day[5:7]),int(day[8:11]))
        weekDay = dayConverted.weekday()
        if weekDay == 0:
            self.weekDay = "MON"
        elif weekDay == 1:
            self.weekDay = "TUE"
        elif weekDay == 2:
            self.weekDay = "WED"
        elif weekDay == 3:
            self.weekDay = "THR"
        elif weekDay == 4:
            self.weekDay = "FRI"
        elif weekDay == 5:
            self.weekDay = "SAT"
        elif weekDay == 6:
            self.weekDay = "SUN"
        else:
            self.weekDay = "NAN"

    def setTemp(self,temp):
        self.tempNow = temp

    def setForcast(self,json):
        #epoch time
        now = int(time.time())

        upComingWeather = []

        for forecast in json:
            for hour in forecast["hour"]:
                if len(upComingWeather)>8:
                    break
                if now <= int(hour["time_epoch"]):
                    # pass
                    # print(hour["time"])
                    if int(hour["time"][11:13]) < 12:
                        upComingWeather.append((hour["time"][11:13],str(hour["temp_f"])[:2],hour["condition"]["code"]))
                    else:
                        upComingWeatherHour ='{:02.0f}'.format(int(hour["time"][11:13]) - 12)
                        print(upComingWeatherHour)
                        upComingWeather.append((upComingWeatherHour,str(hour["temp_f"])[:2],hour["condition"]["code"]))
                

        print(upComingWeather)

        self.textTime1 = upComingWeather[1][0]
        self.temp1 = upComingWeather[1][1]
        self.setWeatherIcon(upComingWeather[1][2],self.sprite1)

        self.textTime2 = upComingWeather[3][0]
        self.temp2 = upComingWeather[3][1]
        self.setWeatherIcon(upComingWeather[3][2],self.sprite2)

        self.textTime3 = upComingWeather[5][0]
        self.temp3 = upComingWeather[5][1]
        self.setWeatherIcon(upComingWeather[5][2],self.sprite3)

        self.textTime4 = upComingWeather[7][0]
        self.temp4 = upComingWeather[7][1]
        self.setWeatherIcon(upComingWeather[7][2],self.sprite4)        

    def render(self, canvas=None):
        canvas = canvas if canvas is not None else self.canvas
        graphics.DrawText(canvas,self.font,70,24,self.textColorDay,self.weekDay)
        graphics.DrawText(canvas,self.font,70,17,self.textColor,self.tempNow)
        self.spriteNow.toCanvas(canvas)

        graphics.DrawText(canvas,self.font,86,24,self.textColorOdd,self.textTime1)
        graphics.DrawText(canvas,self.font,86,17,self.textColorOdd,self.temp1)
        self.sprite1.toCanvas(canvas)

        graphics.DrawText(canvas,self.font,97,24,self.textColor,self.textTime2)
        graphics.DrawText(canvas,self.font,97,17,self.textColor,self.temp2)
        self.sprite2.toCanvas(canvas)

        graphics.DrawText(canvas,self.font,107,24,self.textColorOdd,self.textTime3)
        graphics.DrawText(canvas,self.font,107,17,self.textColorOdd,self.temp3)
        self.sprite3.toCanvas(canvas)

        graphics.DrawText(canvas,self.font,118,24,self.textColor,self.textTime4)
        graphics.DrawText(canvas,self.font,118,17,self.textColor,self.temp4)
        self.sprite4.toCanvas(canvas)

    def update(self):
        pass
        # self.setWeatherIcon(1006)
        # graphics.DrawText(self.canvas,self.font,70,24,self.textColor,self.weekDay)
        # self.sprite1.toCanvas()
        # self.canvas.SetImage(self.sprite.convert('RGB'),self.x,self.y)


import requests
import os
import math
class weatherManager:
    def __init__(self,canvas):
        self.location = os.getenv("WEATHER_LOCATION", "08865")
        self.weather0 = weather(70,2,canvas)
        self.weather1 = weather(85,2,canvas)
        self.weather2 = weather(100,2,canvas)
        self.weather3 = weather(115,2,canvas)
        self.change = True
        self.canvas = canvas
        self.swapTime = 0
        self.weather0.setHidden(True)
        self.weather1.setHidden(True)
        self.weather2.setHidden(True)
        self.weather3.setHidden(True)

        self.weatherToday = weatherToday(canvas)
        self.brightnessV = 1.0


    async def refreshInfo(self):
        await self.getWeather()

    async def getWeather(self):
        # api_key = os.getenv("WEATHERAPI_KEY")
        # location = os.getenv("WEATHER_LOCATION")
        api_key = os.environ["WEATHERAPI_KEY"]
        location = self.location

        url = f'https://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days=5&aqi=no&alerts=no'


        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                    async with session.get(url) as response:
                        l= await response.json()



        print("Weather forecast received")
        # try:
        #     l = requests.get(url,timeout=10)
            
            
        #     # with open('data.json', 'w', encoding='utf-8') as f:
        #     #     json.dump(l.json(), f, ensure_ascii=False, indent=4)

        # except requests.exceptions.Timeout:
        #     print("Weather TimeOut")
        #     return
        # except requests.exceptions.JSONDecodeError:
        #     print("WEATHER JSON ERROR WEE WOO")
        # except:
        #     print("COULD NOT GET WEATHER WEE WOO")
        #     print("\n\n")
        #     print(l.json())
        #     return
        try:
            forecast = l["current"]
            self.weather0.setDay(forecast["last_updated"])
            self.weather0.setTemp(str(forecast["temp_f"])[:2])
            self.weather0.setWeatherIcon(forecast["condition"]["code"])

            forecast = l["forecast"]["forecastday"][0]
            self.weather1.setDay(forecast["date"])
            self.weather1.setTemp(str(forecast["day"]["maxtemp_f"])[:2])
            self.weather1.setWeatherIcon(forecast["day"]["condition"]["code"])

            forecast = l["forecast"]["forecastday"][1]
            self.weather2.setDay(forecast["date"])
            self.weather2.setTemp(str(forecast["day"]["maxtemp_f"])[:2])
            self.weather2.setWeatherIcon(forecast["day"]["condition"]["code"])

            forecast = l["forecast"]["forecastday"][2]
            self.weather3.setDay(forecast["date"])
            self.weather3.setTemp(str(forecast["day"]["maxtemp_f"])[:2])
            self.weather3.setWeatherIcon(forecast["day"]["condition"]["code"])

            forecast = l["current"]
            self.weatherToday.setDay(forecast["last_updated"])
            self.weatherToday.setTemp(str(forecast["temp_f"])[:2])
            self.weatherToday.setWeatherIcon(forecast["condition"]["code"],self.weatherToday.spriteNow)
            forecast = l["forecast"]["forecastday"]
            self.weatherToday.setForcast(forecast)
        except:
            print("Error updating weather icons")

        # print(l.json())

        

    def display(self):
        pass
    def brightness(self,br):
        self.weather0.setBrightness(br)
        self.weather1.setBrightness(br)
        self.weather2.setBrightness(br)
        self.weather3.setBrightness(br)
        self.weatherToday.setBrightness(br)

    def changed(self):
        change = self.change
        self.change = False
        return change
    
    def drawRectangle(self,canvas, x1,y1,x2,y2):
        # br = 1
        colorOfFrame = 75,75,75
        # for r in range((x2-x1)+1):
        #     canvas.SetPixel(x1+r,y1, self.brightnessV *colorOfFrame[0], self.brightnessV * colorOfFrame[1], self.brightnessV * colorOfFrame[2])
        # for r in range((x2-x1)+1):
        #     canvas.SetPixel(x1+r,y2, self.brightnessV *colorOfFrame[0], self.brightnessV * colorOfFrame[1], self.brightnessV * colorOfFrame[2])

        # for r in range((y2-y1+1)):
        #     canvas.SetPixel(x1,y1+r, self.brightnessV *colorOfFrame[0], self.brightnessV * colorOfFrame[1], self.brightnessV * colorOfFrame[2])
        #     canvas.SetPixel(x2,y1+r, self.brightnessV *colorOfFrame[0], self.brightnessV * colorOfFrame[1], self.brightnessV * colorOfFrame[2])

    def render(self, canvas=None):
        canvas = canvas if canvas is not None else self.canvas
        if not self.weather0.hidden:
            self.weather0.render(canvas)
            self.weather1.render(canvas)
            self.weather2.render(canvas)
            self.weather3.render(canvas)
            self.drawRectangle(canvas,68,0,81,24)
        else:
            self.weatherToday.render(canvas)
            self.drawRectangle(canvas,68,0,127,24)
    
    def update(self,dt):
        self.swapTime += dt
        # print(self.swapTime)
        if self.swapTime > 10:
            val = not self.weather0.hidden
            self.weather0.setHidden(val)
            self.weather1.setHidden(val)
            self.weather2.setHidden(val)
            self.weather3.setHidden(val)
            self.swapTime = 0

        # self.render()
        # self.weather0.update()
        # self.weather1.update()
        # self.weather2.update()
        return
