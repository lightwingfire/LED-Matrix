from weather import weather
import os
class weathermanager:

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.today = weather(x,y)
        self.tomorrow = weather(x+18,y)
        self.nextTomorrow = weather(x+36,y)

        self.today.setDay(0)
        self.tomorrow.setDay(1)
        self.nextTomorrow.setDay(2)

        self.lastRefreshed = 30

    def setRequest(self, requests):
        self.requests = requests

    def getDisplay(self):
        list = self.today.getDisplay()+self.tomorrow.getDisplay()+self.nextTomorrow.getDisplay()
        # print(list)
        return list

    def getWeather(self):
        api_key = os.getenv("WEATHERAPI_KEY")
        location = os.getenv("WEATHER_LOCATION")
        # url = f'http://api.weatherapi.com/v1/current.json?key={api_key}&q={location}'
        url = f'http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days=3&aqi=no&alerts=no'
        l = self.requests.get(url)

        self.today.getWeather(l)
        self.tomorrow.getWeather(l)
        self.nextTomorrow.getWeather(l)

    def getLastRefreshed(self):
        return self.lastRefreshed
    
    def setLastRefreshed(self, v):
        self.lastRefreshed = v

    def setOff(self):
        self.today.setOff()
        self.tomorrow.setOff()
        self.nextTomorrow.setOff()

    def setOn(self):
        self.today.setOn()
        self.tomorrow.setOn()
        self.nextTomorrow.setOn()

    def updateWeather(self,dt):
        self.today.updateWeather(dt)
        self.tomorrow.updateWeather(dt)
        self.nextTomorrow.updateWeather(dt)

    
        # self.today.
        # self.tomorrow.
        # self.nextTomorrow.