#Jakob Coughlan

from adafruit_datetime import datetime, timedelta
import time
import rtc
from rtc import RTC
import board
import digitalio
import displayio
import terminalio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix
import rgbmatrix
import framebufferio
import json

from tickertape2 import tickertape
from weather import weather
from timemanager import Timemanager
from clockface import ClockFace
from weathermanager import weathermanager

import os
import ipaddress
import ssl
import wifi
import socketpool
import adafruit_requests

import adafruit_ntp

start_time = time.monotonic()
dt=0.0

for network in wifi.radio.start_scanning_networks():
    print("\t%s\t\tRSSI: %d\tChannel: %d" % (str(network.ssid, "utf-8"),
                                             network.rssi, network.channel))
wifi.radio.stop_scanning_networks()

print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")
print(f"My IP address: {wifi.radio.ipv4_address}")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# --- Display setup ---
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=128, height=32, bit_depth=3, tile=1, serpentine=True,
    rgb_pins=[board.MTX_R1,
              board.MTX_G1,
              board.MTX_B1,
              board.MTX_R2,
              board.MTX_G2,
              board.MTX_B2],
    addr_pins=[board.MTX_ADDRA,
               board.MTX_ADDRB,
               board.MTX_ADDRC,
               board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE)

matrix.brightness = .3
display = framebufferio.FramebufferDisplay(matrix)
network = Network(status_neopixel=board.NEOPIXEL, debug=False)

# --- Drawing setup ---
group = displayio.Group()  # Create a Group
# bitmap = displayio.Bitmap(64, 32, 4)  # Create a bitmap object,width, height, bit depth
# color = displayio.Palette(4)  # Create a color palette
# color[0] = 0x000000  # black background
# color[1] = 0x330000  # red
# color[2] = 0xee4b00  # amber
# color[3] = 0x006600  # greenish

# # Create a TileGrid using the Bitmap and Palette
# tile_grid = displayio.TileGrid(bitmap, pixel_shader=color)
# group.append(tile_grid)  # Add the TileGrid to the Group
display.show(group)

#creates the ticker tape at the bottom of the screen
news = tickertape(128,28)
news.setRequests(requests)
news.getArticles()

#add both labels for the tickertape
for i in news.getLabels():
    group.append(i)

#creates clock face and adds labels
clockface = ClockFace(0,9)
group.append(clockface.getClockFace())


weatherDisplay = weathermanager(72,1)
# weatherDisplay.setDay('today')
weatherDisplay.setRequest(requests)
weatherDisplay.getWeather()
for i in weatherDisplay.getDisplay():
    group.append(i)
#group.append(weatherDisplay.load_image())

tm = Timemanager()
tm.setWeather(weatherDisplay)
tm.setTickerTape(news)
tm.setClockFace(clockface)

try:
    network.get_local_time()
    # network.get_strftime()
except:
    print("couldn't get time from network")
    try:
        r = requests.get("https://www.timeapi.io/api/Time/current/zone?timeZone=America/New_York")

        tn = r.json()["dateTime"]
        rd = rtc.RTC()
        rd.datetime = time.struct_time((int(tn[:4]), int(tn[5:7]), int(tn[8:10]), int(tn[11:13]), int(tn[14:16]), int(tn[17:19]), 0, -1, -1))
    except:
        print("couldn't get time from timeapi.io")
    # print(tn)
    # os.system("time "+ str(tn))
    # # pass

displayButton = digitalio.DigitalInOut(board.BUTTON_DOWN)
displayButton.direction = digitalio.Direction.INPUT
print("starting")
while True:

    tm.updateInstance(dt)

    news.updateNews(dt)
    clockface.updateFace()
    weatherDisplay.updateWeather(dt)

    if displayButton.value:
        group.hidden = not group.hidden
    # Get the current time at the beginning of each frame
    # Calculate delta time in seconds
    # Update the start time for the next frame
    current_time = time.monotonic()
    dt = current_time - start_time
    start_time = current_time

    #adjusts sleep time to account for fluxuations in time
    if dt < 1.0 / 60:
        time.sleep((1.0 / 60) - dt)
