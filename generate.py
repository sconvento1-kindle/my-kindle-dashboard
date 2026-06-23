import os
import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
from icalevents.icalevents import events_from_url

# 1. Canvas Configuration (Portrait layout)
WIDTH, HEIGHT = 1080, 1440
BLACK, WHITE = 0, 255
image = Image.new("L", (WIDTH, HEIGHT), WHITE)
draw = ImageDraw.Draw(image)

# 2. Font Loading Setup
try:
    font_large = ImageFont.truetype("Arial.ttf", 90)
    font_medium = ImageFont.truetype("Arial.ttf", 40)
    font_small = ImageFont.truetype("Arial.ttf", 28)
except IOError:
    font_large = font_medium = font_small = ImageFont.load_default()

# --- DATA FETCHING ---

# Fetch Live Weather (Defaulting to Seregno, IT)
weather_text = "Weather Unavailable"
temp_text = "--°C"
high_low_text = "H: -- L: --"

api_key = os.environ.get("WEATHER_API_KEY")
if api_key:
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Seregno,it&units=metric&appid={api_key}"
        data = requests.get(url).json()
        temp_text = f"{round(data['main']['temp'])}°C"
        weather_text = data['weather'][0]['description'].title()
        high_low_text = f"H: {round(data['main']['temp_max'])}° L: {round(data['main']['temp_min'])}°"
    except Exception:
        pass

# Fetch Live Calendar Events (Next 24 Hours)
calendar_events = ["No upcoming events today."]
ical_url = os.environ.get("CALENDAR_ICAL_URL")

if ical_url:
    try:
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(days=1)
        # Fetch and sort events chronologically
        fetched_events = events_from_url(ical_url, start=start_time, end=end_time)
        fetched_events.sort(key=lambda x: x.start)
        
        if fetched_events:
            calendar_events = []
            for ev in fetched_events[:8]: # Limit to top 8 events to fit screen
                time_str = ev.start.strftime("%H:%M")
                calendar_events.append(f"[{time_str}] {ev.summary}")
    except Exception as e:
        calendar_events = ["Could not sync calendar feed."]

# --- DRAW LAYOUT ---

# Top Border Line & Section Grids
draw.line([(50, 40), (WIDTH - 50, 40)], fill=BLACK, width=4)
draw.line([(50, 320), (WIDTH - 50, 320)], fill=BLACK, width=3)
draw.line([(WIDTH // 2, 40), (WIDTH // 2, 320)], fill=BLACK, width=2)

# Pull Time & Date Context
now = datetime.datetime.now()
time_string = now.strftime("%H:%M")
date_string = now.strftime("%A, %B %d")

# Draw Time, Date, and Weather Strings
draw.text((80, 80), time_string, fill=BLACK, font=font_large)
draw.text((80, 210), date_string, fill=BLACK, font=font_medium)

draw.text((WIDTH // 2 + 50, 90), "Seregno, IT", fill=BLACK, font=font_medium)
draw.text((WIDTH // 2 + 50, 160), f"{temp_text} • {weather_text}", fill=BLACK, font=font_medium)
draw.text((WIDTH // 2 + 50, 220), high_low_text, fill=BLACK, font=font_small)

# Draw Calendar Section Title
draw.text((80, 370), "UPCOMING EVENTS", fill=BLACK, font=font_medium)
draw.line([(80, 430), (450, 430)], fill=BLACK, width=2)

# Print Out the Sorted Calendar Items
y_offset = 480
for event in calendar_events:
    draw.text((80, y_offset), event, fill=BLACK, font=font_small)
    y_offset += 75

# Save Output
image.save("dashboard.png", "PNG")
print("Live structured dashboard rendered successfully!")
