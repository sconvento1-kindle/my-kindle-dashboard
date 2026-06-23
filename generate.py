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

# 2. Correctly Load a Scalable Default Font for GitHub Actions
# This uses Pillow's built-in font scaler since Arial.ttf won't exist on the server
try:
    font_large = ImageFont.load_default(size=90)
    font_medium = ImageFont.load_default(size=40)
    font_small = ImageFont.load_default(size=32)
except AttributeError:
    # Older Pillow versions fallback
    font_large = font_medium = font_small = ImageFont.load_default()

# --- DATA FETCHING ---
weather_text = "Partly Cloudy"
temp_text = "31°C"
high_low_text = ""

api_key = os.environ.get("WEATHER_API_KEY")
if api_key:
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Seregno,it&units=metric&appid={api_key}"
        data = requests.get(url).json()
        temp_text = f"{round(data['main']['temp'])}°C"
        weather_text = data['weather'][0]['description'].title()
    except Exception:
        pass

calendar_events = ["No upcoming events today."]
ical_url = os.environ.get("CALENDAR_ICAL_URL")

if ical_url:
    try:
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(days=14) # Look ahead 2 weeks
        fetched_events = events_from_url(ical_url, start=start_time, end=end_time)
        fetched_events.sort(key=lambda x: x.start)
        
        if fetched_events:
            calendar_events = []
            for ev in fetched_events[:12]: # Allow more events to fill space
                date_str = ev.start.strftime("%b %d - %H:%M") if not ev.all_day else f"{ev.start.strftime('%b %d')} - All Day"
                calendar_events.append(f"[{date_str}] {ev.summary}")
    except Exception:
        calendar_events = ["Could not sync calendar feed."]

# --- DRAW LAYOUT (Adjusted for clean formatting) ---

# Center dividing line
draw.line([(WIDTH // 2, 50), (WIDTH // 2, HEIGHT - 50)], fill=BLACK, width=4)

# Pull Time & Date Context
now = datetime.datetime.now()
time_string = now.strftime("%H:%M")
date_string = now.strftime("%A, %b %d")

# Draw Left Column: Clock & Weather
draw.text((60, 100), time_string, fill=BLACK, font=font_large)
draw.text((60, 220), date_string, fill=BLACK, font=font_medium)

draw.line([(50, 350), (WIDTH // 2 - 50, 350)], fill=BLACK, width=2)

draw.text((60, 400), "WEATHER", fill=BLACK, font=font_medium)
draw.text((60, 480), f"Local: {temp_text}", fill=BLACK, font=font_small)
draw.text((60, 540), weather_text, fill=BLACK, font=font_small)

# Draw Right Column: Upcoming Agenda
draw.text((WIDTH // 2 + 50, 100), "UPCOMING AGENDA", fill=BLACK, font=font_medium)
draw.line([(WIDTH // 2 + 50, 160), (WIDTH - 50, 160)], fill=BLACK, width=3)

y_offset = 200
for event in calendar_events:
    # Basic text wrapping check to ensure long events don't bleed off screen
    if len(event) > 40:
        event = event[:37] + "..."
    draw.text((WIDTH // 2 + 50, y_offset), event, fill=BLACK, font=font_small)
    y_offset += 80

# Save Output
image.save("dashboard.png", "PNG")
