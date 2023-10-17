from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
import terminalio

class ClockFace:

    def __init__(self,x,y) :
        self.BLINK = True
        font = bitmap_font.load_font("/IBMPlexMono-Medium-24_jep.bdf")
        # font = terminalio.FONT
        self.clockLabel = Label(font)
        self.clockLabel.x = x
        self.clockLabel.y = y
        self.clockLabel.color = 0x330000

    def setTime(self,now):
        self.now = now

    def setColor(self, color):
        self.clockLabel.color = color

    def getClockFace(self):
        return self.clockLabel

    def updateFace(self,*, hours=None, minutes=None, show_colon=False):
        # now = time.localtime()  # Get the time values we need
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

        self.clockLabel.text = "{hours}{colon}{minutes:02d}".format(
            hours=hours, minutes=minutes, colon=colon
        )
        bbx, bby, bbwidth, bbh = self.clockLabel.bounding_box
        # Center the label
        # clock_label.x = round(display.width / 2 - bbwidth / 2)
        # clock_label.y = display.height // 2
        # if DEBUG:
        #     print("Label bounding box: {},{},{},{}".format(bbx, bby, bbwidth, bbh))
        #     print("Label x: {} y: {}".format(clock_label.x, clock_label.y))