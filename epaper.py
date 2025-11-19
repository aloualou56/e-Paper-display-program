#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import psutil
import subprocess
import logging
import time
import traceback
import requests
from PIL import Image, ImageDraw, ImageFont

# Import configuration and initialize paths
try:
    import config
except ImportError:
    logging.critical("Error: config.py not found. Please create it.")
    sys.exit(1)

picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V3

# --- Constants ---
# Update Intervals (in seconds)
FULL_REFRESH_INTERVAL = 43200  # 12 hours
WEATHER_UPDATE_INTERVAL = 1800  # 30 minutes
SYSTEM_UPDATE_INTERVAL = 10
TIME_UPDATE_INTERVAL = 1

# Fonts
FONT_FILE = os.path.join(picdir, 'Font.ttc')
FONT_SIZE_SMALL = 15
FONT_SIZE_MEDIUM = 24
FONT_SIZE_LARGE = 48

# API URL
WEATHER_URL = f"https://api.openweathermap.org/data/2.5/weather?lat={config.LATITUDE}&lon={config.LONGITUDE}&appid={config.API_KEY}&units=metric"

def get_cpu_temp():
    """Returns the CPU temperature as a formatted string."""
    try:
        result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True, check=True)
        temp_str = result.stdout.split('=')[1].split("'")[0]
        return f"{temp_str}°C"
    except (FileNotFoundError, IndexError, subprocess.CalledProcessError) as e:
        logging.error(f"Could not get CPU temperature: {e}")
        return "N/A"

def get_system_usage():
    """Returns CPU temperature, CPU usage, and RAM usage."""
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    cpu_temp = get_cpu_temp()
    return f" {cpu_temp}   {cpu_usage:.1f}%   {ram_usage:.1f}%"

def fetch_weather():
    """Fetches weather data from OpenWeatherMap."""
    try:
        response = requests.get(WEATHER_URL)
        response.raise_for_status()
        data = response.json()
        main = data["main"]
        weather = data["weather"][0]
        temp = round(main["temp"], 1)
        humidity = main["humidity"]
        description = weather["description"].capitalize()
        return f"   {temp}°C    {humidity}%    {description}"
    except requests.RequestException as e:
        logging.error(f"Weather API request failed: {e}")
        return "Weather data unavailable"

def update_time_display(draw, font):
    """Draws the current time on the image."""
    draw.rectangle((30, 30, 220, 85), fill=255)
    draw.text((55, 30), time.strftime('%H:%M'), font=font, fill=0)

def main():
    """Main function to run the e-paper display."""
    logging.basicConfig(level=logging.INFO)

    try:
        epd = epd2in13_V3.EPD()
        logging.info("Initializing and clearing display...")
        epd.init()
        epd.Clear(0xFF)

        # Load fonts
        font_small = ImageFont.truetype(FONT_FILE, FONT_SIZE_SMALL)
        font_medium = ImageFont.truetype(FONT_FILE, FONT_SIZE_MEDIUM)
        font_large = ImageFont.truetype(FONT_FILE, FONT_SIZE_LARGE)

        # Create image buffer
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)

        # Draw static lines
        draw.line((0, 20, epd.height, 20), fill=0)
        draw.line((0, epd.width - 20, epd.height, epd.width - 20), fill=0)
        
        epd.displayPartBaseImage(epd.getbuffer(image))

        last_full_refresh = time.time()
        last_weather_update = 0
        last_system_update = 0

        while True:
            current_time = time.time()

            # Full refresh to prevent burn-in
            if current_time - last_full_refresh >= FULL_REFRESH_INTERVAL:
                logging.info("Performing full refresh...")
                epd.init()
                epd.Clear(0xFF)
                epd.display(epd.getbuffer(image))
                last_full_refresh = current_time

            # Update system stats
            if current_time - last_system_update >= SYSTEM_UPDATE_INTERVAL:
                usage_text = get_system_usage()
                draw.rectangle((40, 2, 300, 18), fill=255)
                draw.text((40, 2), usage_text, font=font_small, fill=0)
                last_system_update = current_time

            # Update weather
            if current_time - last_weather_update >= WEATHER_UPDATE_INTERVAL:
                weather_text = fetch_weather()
                draw.rectangle((20, 102, 230, 118), fill=255)
                draw.line((0, epd.width - 20, epd.height, epd.width - 20), fill=0)
                draw.text((20, 102), weather_text, font=font_small, fill=0)
                last_weather_update = current_time

            # Update time
            update_time_display(draw, font_large)

            # Partial update for the screen
            epd.displayPartial(epd.getbuffer(image))

            time.sleep(TIME_UPDATE_INTERVAL)

    except IOError as e:
        logging.error(e)
    except KeyboardInterrupt:
        logging.info("Ctrl+C received, exiting...")
        epd.init()
        epd.Clear(0xFF)
        logging.info("Clearing display and putting to sleep.")
        epd.sleep()
        epd2in13_V3.epdconfig.module_exit(cleanup=True)
        sys.exit(0)

if __name__ == "__main__":
    main()
