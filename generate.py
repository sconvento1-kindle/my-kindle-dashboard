import os
import datetime
import glob
import requests
from PIL import Image, ImageDraw, ImageFont
from icalevents.icalevents import events_from_url

# 1. Canvas Configuration (Portrait layout)
WIDTH, HEIGHT = 1080, 1440
BLACK, WHITE = 0, 255
image = Image.new("L", (WIDTH, HEIGHT), WHITE)
draw = ImageDraw.Draw(image)

# 2. BULLETPROOF FONT LOADING
system_fonts = glob.glob("/usr/share/fonts/truetype/**/*.ttf", recursive=True)
selected_font = None

for f in system_fonts:
    if "LiberationSans-Bold" in f or "DejaVuSans-Bold" in f:
        selected_font = f
        break

if not selected_font and system_fonts:
    selected_font = system_fonts[0]

try:
    if selected_font:
        font_large = ImageFont.truetype(selected_font, 110)   # Giant Clock
        font_medium = ImageFont.truetype(selected_font, 45)   # Subheaders
        font_small = ImageFont.truetype(selected_font, 32)    # Agenda items
    else:
        raise IOError
except Exception:
    font_large = font_medium = font_small = ImageFont.load_default()

# --- DATA FETCHING ---
weather_text = "Partly Cloudy"
temp_text = "31°C"

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
        end_time = start_time + datetime.timedelta(days=14)
        fetched_events = events_from_url(ical_url, start=start_time, end=end_time)
        fetched_events.sort(key=lambda x: x.start)
        
        if fetched_events:
            calendar_events = []
            for ev in fetched_events[:12]:
                date_str = ev.start.strftime("%b %d - %H:%M") if not ev.all_day else f"{ev.start.strftime('%b %d')} - All Day"
                calendar_events.append(f"[{date_str}] {ev.summary}")
    except Exception:
        calendar_events = ["Could not sync calendar feed."]

# --- DRAW LAYOUT ---

# Center dividing line
draw.line([(WIDTH // 2, 50), (WIDTH // 2, HEIGHT - 50)], fill=BLACK, width=5)

# Current Time & Date strings
now = datetime.datetime.now()
time_string = now.strftime("%H:%M")
date_string = now.strftime("%A, %b %d")

# Draw Left Column
draw.text((60, 100), time_string, fill=BLACK, font=font_large)
draw.text((60, 240), date_string, fill=BLACK, font=font_medium)

draw.line([(60, 380), (WIDTH // 2 - 60, 380)], fill=BLACK, width=3)

draw.text((60, 440), "WEATHER", fill=BLACK, font=font_medium)
draw.text((60, 520), f"Local: {temp_text}", fill=BLACK, font=font_small)
draw.text((60, 580), weather_text, fill=BLACK, font=font_small)

# Draw Right Column
draw.text((WIDTH // 2 + 60, 100), "UPCOMING AGENDA", fill=BLACK, font=font_medium)
draw.line([(WIDTH // 2 + 60, 160), (WIDTH - 60, 160)], fill=BLACK, width=4)

y_offset = 220
for event in calendar_events:
    if len(event) > 38:
        event = event[:35] + "..."
    draw.text((WIDTH // 2 + 60, y_offset), event, fill=BLACK, font=font_small)
    y_offset += 85

# Save Output
image.save("dashboard.png", "PNG")
