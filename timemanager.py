# from timemanager import Timemanager
import time

class Timemanager:

    # def __init__(self):
        # self.tickertape = None
        # self.weather = None
        # self.clockface = None
        # now = time.localtime()
        # self.lastRefreshedTime = 0
        # self.lastRefreshedNews = 0
        # self.lastRefreshedWeather = 0

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Timemanager, cls).__new__(cls)
        return cls.instance


    @staticmethod
    def getInstance():
        if Timemanager.instance is None:
            return Timemanager()

        return Timemanager.instance

    def setTickerTape(self,tickertape):
        Timemanager().tickertape = tickertape

    def setWeather(self,weather):
        Timemanager().weather = weather

    def setClockFace(self,clockface):
        Timemanager().clockface = clockface

    def updateInstance(self, dt):
        now = time.localtime()
        hours = now[3]
        minutes = now[4]

        #CLOCK
        Timemanager().clockface.setTime(now)
        if hours >= 18 or hours <=7:
            Timemanager().clockface.setColor(0x200000)
        else:
            Timemanager().clockface.setColor(0x006600)

        # #NEWS
        if Timemanager().tickertape.getLastRefreshed() + 3 <= hours or Timemanager().tickertape.getLastRefreshed() > hours:
            Timemanager().tickertape.setLastRefreshed(hours)
            Timemanager().tickertape.getArticles()
            print("Refreshing articles")

        if hours >=20 or hours <=7:
          Timemanager().tickertape.fadeOff()
          Timemanager().weather.setOff()
        else:
          Timemanager().tickertape.fadeIn()
          Timemanager().weather.setOn()

        #WEATHER
        # print(f"lrw:{Timemanager().weather.getLastRefreshed()} minutes:{minutes}")
        if Timemanager().weather.getLastRefreshed() + 30 <= minutes or Timemanager().weather.getLastRefreshed() > minutes:
            print("Refreshing Weather")
            Timemanager().weather.setLastRefreshed(minutes)
            Timemanager().weather.getWeather()


        return
