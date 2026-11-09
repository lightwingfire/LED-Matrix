#Jakob Coughlan 12-29-2024

import asyncio
import time
try:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
except:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
from ser import ser
import threading
# import RPi.GPIO as GPIO
from PIL import Image
from clock import ClockFace
from weather import weatherManager
from tickertape import ticktape, TickerTapeManager

async def main():
    webpage = ser()
    threading.Thread(target=webpage.start).start()

    # GPIOPin = 2
    # GPIO.setmode(GPIO.BCM)  
    # GPIO.setup(GPIOPin, GPIO.OUT)
    # GPIO.output(GPIOPin, GPIO.LOW)
    # buttonState = GPIO.input(GPIOPin)

    # webpage.start()
    print ("hello World!")
    options = RGBMatrixOptions()
    options.gpio_slowdown = 2
    options.cols = 128
    options.show_refresh_rate = 60
    # options.pwm_bits = 11
    # options.pwm_lsb_nanoseconds = 300
    matrix = RGBMatrix(options = options)

    canvas = matrix.CreateFrameCanvas()

    clock = ClockFace(4,16,canvas)
    wM = weatherManager(canvas)
    tt = TickerTapeManager(canvas)
    asyncio.create_task(tt.refreshInfo())

    change = 0

    start_time = time.monotonic()
    current_time = time.monotonic()
    dt = current_time - start_time
    start_time = current_time

    #adjusts sleep time to account for fluxuations in time
    if dt < 1.0 / 60:
        time.sleep((1.0 / 60) - dt)

    def updateDeltaTime():
        clock.updateFace()
        wM.update(dt)
        tt.update(dt)

    async def refreshAPI():
        
        asyncio.create_task(tt.refreshInfo())
        asyncio.create_task(wM.refreshInfo())

        # try:
        #     tt.refreshInfo()
        #     print("SUCCESSFULLY GOT NEWS")
        # except:
        #     print("FAILED TO GET NEWS")
        # try:
        #     wM.refreshInfo()
        #     print("SUCCESSFULLY GOT WEATHER")
        # except:
        #     print("FAILED TO GET WEATHER")
        # print("top of the hour")

    # await asyncio.sleep(0.1)
    def render():
        clock.render()
        wM.render()
        tt.render()

    def checkForChange():
        if tt.changed() or clock.changed() or wM.changed() or change != webpage.getSlider():
            return True
        
        return False

    while True:
        await asyncio.sleep((1.0 / 240) - dt)
        updateDeltaTime()
        if clock.newHour():
            await refreshAPI()

        if checkForChange():
            canvas.Clear()

            if change != webpage.getSlider():
                clock.setBrightness(webpage.getSlider())
                wM.brightness(webpage.getSlider())
                tt.setBrightness(webpage.getSlider())
                change = webpage.getSlider() 

            render()
            
            

        canvas = matrix.SwapOnVSync(canvas)
        current_time = time.monotonic()
        dt = current_time - start_time
        start_time = current_time

        #adjusts sleep time to account for fluxuations in time
        if dt < 1.0 / 240:
            time.sleep((1.0 / 240) - dt)
        



if __name__ == '__main__':
    asyncio.run(main())
    
  
    
