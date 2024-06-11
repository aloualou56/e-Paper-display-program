#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import psutil
import subprocess
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd2in13_V3
import time
from PIL import Image,ImageDraw,ImageFont
import traceback
import requests, json

lat = ""
lon = ""

API_KEY = ""


complete_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}"

def get_cpu_temp():
    try:
        
        result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
        output = result.stdout

       
        if 'temp=' in output:
            temp_str = output.split('=')[1].split("'")[0]
            return f"{temp_str}\u00B0C"
        else:
            return "Could not parse temperature output"
    except Exception as e:
        return f"Error: {str(e)}"


def system_usage():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    ram_usage = memory.percent
    cpu_temp = get_cpu_temp()
    return cpu_temp, cpu_usage, ram_usage
    


def fetch_weather():
    response = requests.get(complete_url)
    response.raise_for_status()
    x = response.json()
    main = x["main"]
    weather = x["weather"]
    temperature1 = main["temp"]
    pressure = main["pressure"]
    humidity = main["humidity"]
    temperature2 = temperature1 - 273.15
    temperature = round(temperature2, 1)
    description = weather[0]["description"]
    return temperature, humidity, description




try:
        
    logging.info("epd2in13_V3 Demo")

    epd = epd2in13_V3.EPD()
    logging.info("init and Clear")
    epd.init()
    epd.Clear(0xFF)

    font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    font48 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 48)

 

    temperature, humidity, description = fetch_weather()

    weather_image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(weather_image)
    draw.line((0, 20, epd.height, 20), fill=0) 
    draw.line((0, epd.width - 20, epd.height, epd.width - 20), fill=0) 
    weather_text = f"   {temperature}\u00B0C    {humidity}%    {description}"  #allages
    draw.text((20, 102), weather_text, font=font15, fill=0)
    
    time_image = Image.new('1', (epd.height, epd.width), 255)
    time_draw = ImageDraw.Draw(time_image)
    time_image.paste(weather_image, (0, 0))

    epd.displayPartBaseImage(epd.getbuffer(time_image))

    counter = 0
    counter_weather = 0
    counter_usage = 0

    while (True):
        if counter >= 43200:
            counter = 0
            epd.init()
            epd.Clear(0xFF)
            epd.display(epd.getbuffer(time_image))
        if counter_usage >= 10:
            counter_usage = 0
            cpu_temp, cpu_usage, ram_usage = system_usage()
            usage_text = f" {cpu_temp}   {cpu_usage}%   {ram_usage}%"
            time_draw.rectangle((40, 2, 300, 18), fill=255)
            time_draw.text((40, 2), usage_text, font=font15, fill=0)

        if counter_weather >= 60:
            counter_weather = 0
            time_draw.rectangle((20, 102, 20 + font15.getsize(weather_text)[0], 102 + font15.getsize(weather_text)[1]), fill = 255)
            time_draw.line((0, epd.width - 20, epd.height, epd.width - 20), fill=0) 
            temperature, humidity, description = fetch_weather()
            weather_text = f"   {temperature}\u00B0C    {humidity}%    {description}"  #allages
            time_draw.text((20, 102), weather_text, font=font15, fill=0)
            

        time_draw.rectangle((30, 30, 220, 85), fill = 255)      
        time_draw.text((55, 30), time.strftime('%H:%M'), font = font48, fill = 0)
        epd.displayPartial(epd.getbuffer(time_image))
        counter += 1
        counter_weather += 1
        counter_usage += 1
        


except IOError as e:
    logging.info(e)

except KeyboardInterrupt:
    logging.info("ctrl + c:")

    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    yourname = ""

    draw.text((10, 10), f"{yourname}'s raspberry", font = font24, fill = 0)

    epd.display(epd.getbuffer(image))
    
    epd2in13_V3.epdconfig.module_exit(cleanup=True)
    exit()
