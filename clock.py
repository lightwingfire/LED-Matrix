try:
    from RGBMatrixEmulator import graphics
except:
    from rgbmatrix import graphics
import time


class ClockFace:

    def __init__(self,x,y,canvas) :
        self.BLINK = True
        self.font = graphics.Font()
        self.font.LoadFont("texgyre-27.bdf")
        self.textColor = graphics.Color(255, 255, 0)
        self.canvas = canvas
        self.x = x
        self.y = y
        self.change = True
        self.text = "00:00"
        self.hour = "01"
        # font = terminalio.FONT
        # self.clockLabel = Label(font)
        # self.clockLabel.x = x
        # self.clockLabel.y = y
        # self.clockLabel.color = 0x330000

    def setTime(self,now):
        self.now = now

    def setColor(self, color):
        self.textColor = graphics.Color(color)

    def setBrightness(self, br):
        self.textColor = graphics.Color(int(255*br),int(255*br),0)

    # def getClockFace(self):
    #     return self.clockLabel

    def newHour(self):
        hn = self.text[:2].replace(':', ' ')
        if self.hour != hn:
            print (self.hour,hn)
            self.hour = hn

            return True
        return False

    def getHour(self):
        return self.now[3]

    def changed(self):
        change = self.change
        self.change = False
        return change

    def render(self, canvas=None):
        graphics.DrawText(canvas if canvas is not None else self.canvas,
                          self.font,self.x,self.y,self.textColor,self.text)

    def updateFace(self,*, hours=None, minutes=None, show_colon=False):
        self.now = time.localtime()  # Get the time values we need
        if hours is None:
            hours = self.now[3]
        # if hours >= 18 or hours < 6:  # evening hours to morning
        #     clock_label.color = color[1]
        # else:
        #     clock_label.color = color[3]  # daylight hours
        if hours > 12:  # Handle times later than 12:59
            hours -= 12
        elif not hours:  # Handle times between 0:00 and 0:59
            hours = 12

        # if hours>=21 or hours<5:
        #     news.fadeOff()
        # # else:
        # #     news.fadeIn()
        
        if minutes is None:
            minutes = self.now[4]

        if self.BLINK:
            colon = ":" if show_colon or self.now[5] % 2 else " "
        else:
            colon = ":"

        if self.text != "{hours}{colon}{minutes:02d}".format(
            hours=hours, minutes=minutes, colon=colon
        ):
            self.text = "{hours}{colon}{minutes:02d}".format(
                hours=hours, minutes=minutes, colon=colon
            )
            self.change = True

        # graphics.DrawText(self.canvas,self.font,self.x,self.y,self.textColor,self.text)

        # bbx, bby, bbwidth, bbh = self.clockLabel.bounding_box
        # Center the label
        # clock_label.x = round(display.width / 2 - bbwidth / 2)
        # clock_label.y = display.height // 2
        # if DEBUG:
        #     print("Label bounding box: {},{},{},{}".format(bbx, bby, bbwidth, bbh))
        #     print("Label x: {} y: {}".format(clock_label.x, clock_label.y))
