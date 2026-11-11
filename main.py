#Jakob Coughlan 12-29-2024

import asyncio
import time
import os
from config import PROJECT_DIR, load_settings

# Fonts, sprites, templates, and emulator configuration live beside this file.
os.chdir(PROJECT_DIR)
load_settings()
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
from aquarium import Aquarium

def create_display():
    # The emulator starts its own event loop; initialize it before asyncio.run.
    options = RGBMatrixOptions()
    options.gpio_slowdown = 2
    options.cols = 128
    if hasattr(options, "disable_hardware_pulsing"):
        # Avoid indefinite waits in the Pi's hardware PWM pulse generator.
        options.disable_hardware_pulsing = os.getenv("HARDWARE_PULSING", "0") != "1"
    if hasattr(options, "browser"):
        options.browser.port = int(os.getenv("EMULATOR_PORT", options.browser.port))
    options.show_refresh_rate = os.getenv("SHOW_REFRESH_RATE", "0") == "1"
    # options.pwm_bits = 11
    # options.pwm_lsb_nanoseconds = 300
    matrix = RGBMatrix(options = options)

    canvas = matrix.CreateFrameCanvas()
    return matrix, canvas


async def main(matrix, canvas):
    webpage = ser()
    threading.Thread(target=webpage.start, daemon=True).start()

    clock = ClockFace(4,16,canvas)
    wM = weatherManager(canvas)
    tt = TickerTapeManager(canvas)
    aquarium = Aquarium(canvas)
    webpage.setFishStats(aquarium.fishStats())
    webpage.setNews(tt.newsJson, updated_at=tt.newsUpdatedAt, cached=tt.newsCached)

    change = 0

    start_time = time.monotonic()
    dt = 0
    previous_fish_mode = False
    previous_spotify = False

    def updateDeltaTime():
        clock.updateFace()
        wM.update(dt)
        tt.update(dt)

    async def refreshAPI(weather_only=False):
        async def refreshNews():
            try:
                await tt.refreshInfo()
            except Exception:
                webpage.setNews(tt.newsJson, updated_at=tt.newsUpdatedAt, cached=tt.newsCached,
                                error="News refresh failed. Showing previously loaded stories.")
                raise
            webpage.setNews(tt.newsJson, updated_at=tt.newsUpdatedAt, cached=tt.newsCached)

        async def refresh(name, callback):
            try:
                await callback()
            except Exception as error:
                # Request exceptions can include URLs containing API keys.
                print(f"{name} refresh failed ({type(error).__name__}); keeping existing display.")

        jobs = [refresh("Weather", wM.refreshInfo)]
        if not weather_only:
            jobs.append(refresh("News", refreshNews))
        await asyncio.gather(*jobs)

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
        clock.render(canvas)
        wM.render(canvas)
        tt.render(canvas)

    def checkForChange():
        if tt.changed() or clock.changed() or wM.changed() or change != webpage.getSlider():
            return True
        
        return False

    refresh_task = asyncio.create_task(refreshAPI())
    while True:
        frame_start = time.monotonic()
        dt = frame_start - start_time
        start_time = frame_start
        fish_mode = webpage.getFishMode()
        mode_changed = fish_mode != previous_fish_mode
        previous_fish_mode = fish_mode
        if fish_mode:
            if webpage.consumeSandRequest():
                aquarium.regenerateSand()
            if webpage.consumeFishRequest():
                aquarium.regenerateFish()
            for command in webpage.consumeFishCommands():
                if command['action'] == 'add':
                    aquarium.addFish()
                elif command['action'] == 'regenerate':
                    aquarium.regenerateFish(command['id'])
                elif command['action'] == 'delete':
                    aquarium.deleteFish(command['id'])
            aquarium.setShadowMode(webpage.getShadowMode())
            aquarium.setBrightness(webpage.getSlider())
            aquarium.update(dt)
            webpage.setFishStats(aquarium.fishStats())
            canvas.Clear()
            aquarium.render(canvas)
            canvas = matrix.SwapOnVSync(canvas)
            webpage.reportFrame()
            await asyncio.sleep(max(0, 1.0 / 60 - (time.monotonic() - frame_start)))
            continue
        tt.setSpeed(webpage.getTickerSpeed())
        tt.setEnabled(webpage.getTickerEnabled())
        tt.setNowPlaying(webpage.spotifyTickerText())
        updateDeltaTime()
        if refresh_task.done() and wM.location != webpage.getWeatherLocation():
            wM.location = webpage.getWeatherLocation()
            refresh_task = asyncio.create_task(refreshAPI(weather_only=True))
        elif clock.newHour() and refresh_task.done():
            refresh_task = asyncio.create_task(refreshAPI())

        if mode_changed or checkForChange() or previous_spotify:
            canvas.Clear()

            if change != webpage.getSlider():
                clock.setBrightness(webpage.getSlider())
                wM.brightness(webpage.getSlider())
                tt.setBrightness(webpage.getSlider())
                change = webpage.getSlider() 

            render()
            
            

        spotify_playing = webpage.renderSpotify(canvas, dt) is True
        previous_spotify = spotify_playing
        canvas = matrix.SwapOnVSync(canvas)
        webpage.reportFrame()

        #adjusts sleep time to account for fluxuations in time
        await asyncio.sleep(max(0, 1.0 / 60 - (time.monotonic() - frame_start)))
        



if __name__ == '__main__':
    try:
        matrix, canvas = create_display()
        asyncio.run(main(matrix, canvas))
    except KeyboardInterrupt:
        pass
    
  
    
