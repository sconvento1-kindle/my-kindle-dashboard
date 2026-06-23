import os
import requests
from datetime import datetime
from icalendar import Calendar
from PIL import Image, ImageDraw, ImageFont

# 1. Setup Canvas (Kindle Paperwhite Landscape: 1448 x 1072)
WIDTH, HEIGHT = 1448, 1072
image = Image.new("L", (WIDTH, HEIGHT), 255) # Pure White
draw = ImageDraw.Draw(image)

# 2. Safely Load Fonts (GitHub Actions compatible fallback)
font_large = ImageFont.load_default()
font_medium = ImageFont.load_default()
font_small = ImageFont.load_default()

# Try downloading a clean font so it looks professional, otherwise fallback gracefully
try:
    font_url = "https://github.com/google/fonts/raw/main/ofl/dejavusans/DejaVuSans-Bold.ttf"
    r = requests.get(font_url)
    with open("font.ttf", "wb") as f:
        f.write(r.content)
    font_large = ImageFont.truetype("font.ttf", 110)
    font_medium = ImageFont.truetype("font.ttf", 36)
    font_small = ImageFont.truetype("font.ttf", 26)
    print("Custom E-ink fonts loaded successfully!")
except Exception as e:
    print(f"Font download failed, using basic system fallback: {e}")

# 3. Fetch Weather Data (Left Column)
print("Fetching weather...")
weather_url = "https://api.open-meteo.com/v1/forecast?latitude=45.6&longitude=9.2&current_weather=true"
try:
    res = requests.get(weather_url).json()
    temp = f"{round(res['current_weather']['temperature'])}°C"
    condition_code = res['current_weather']['weathercode']
    
    if condition_code == 0: cond_text = "Clear Skies"
    elif condition_code in [1, 2, 3]: cond_text = "Partly Cloudy"
    elif condition_code in [45, 48]: cond_text = "Foggy"
    elif condition_code in [51, 53, 55, 61, 63, 65]: cond_text = "Raining"
    else: cond_text = "Overcast"
except Exception:
    temp, cond_text = "--°C", "Weather Error"

# Draw Left Side Panel
now = datetime.now()
time_str = now.strftime("%H:%M")
date_str = now.strftime("%A, %b %d")

draw.text((60, 120), time_str, font=font_large, fill=0)
draw.text((60, 260), date_str, font=font_medium, fill=0)
draw.text((60, 480), f"Local: {temp}", font=font_large, fill=0)
draw.text((60, 620), cond_text, font=font_medium, fill=0)

# Draw Column Separator
draw.line([(680, 80), (680, 992)], fill=0, width=4)

# 4. Fetch & Process Calendar (Right Column)
draw.text((740, 120), "UPCOMING AGENDA", font=font_medium, fill=0)
draw.line([(740, 180), (1380, 180)], fill=0, width=2)

calendar_url = os.environ.get("CALENDAR_URL")
y_offset = 220

if calendar_url and "http" in calendar_url:
    print("Fetching calendar events...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        ics_data = requests.get(calendar_url, headers=headers).text
        cal = Calendar.from_ical(ics_data)
        events = []
        
        for component in cal.walk():
            if component.name == "VEVENT":
                summary = component.get('summary')
                dtstart = component.get('dtstart').dt
                
                if isinstance(dtstart, datetime):
                    event_date = dtstart.date()
                    time_label = dtstart.strftime("%H:%M")
                else:
                    event_date = dtstart
                    time_label = "All Day"
                
                if event_date >= now.date():
                    events.append((event_date, time_label, str(summary)))
        
        events.sort(key=lambda x: (x[0], x[1]))
        
        if not events:
            draw.text((740, y_offset), "No upcoming events found", font=font_small, fill=0)
        else:
            for ev_date, ev_time, ev_sum in events[:7]:
                date_display = ev_date.strftime("%b %d")
                display_text = f"[{date_display} - {ev_time}] {ev_sum}"
                if len(display_text) > 42:
                    display_text = display_text[:39] + "..."
                
                draw.text((740, y_offset), display_text, font=font_small, fill=0)
                y_offset += 95
                
    except Exception as e:
        draw.text((740, y_offset), f"Calendar Error: Sync failed", font=font_small, fill=0)
else:
    draw.text((740, y_offset), "Status: Awaiting Calendar URL...", font=font_small, fill=0)

# Save high contrast PNG asset
image.save("dashboard.png", "PNG")
print("Dashboard image built successfully!")
