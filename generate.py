import os
import requests
from datetime import datetime
from icalendar import Calendar
from PIL import Image, ImageDraw, ImageFont

# 1. Setup Canvas (Kindle Paperwhite 10th Gen Landscape: 1448 x 1072)
WIDTH, HEIGHT = 1448, 1072
image = Image.new("L", (WIDTH, HEIGHT), 255) # "L" mode is 8-bit grayscale, 255 is pure white
draw = ImageDraw.Draw(image)

# Use default system fonts (clean and compatible with GitHub Actions)
try:
    font_large = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
    font_medium = ImageFont.truetype("DejaVuSans.ttf", 40)
    font_small = ImageFont.truetype("DejaVuSans.ttf", 28)
except IOError:
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()

# 2. Fetch & Draw Weather Data (Left Column)
print("Fetching weather...")
# Default coordinates set to Lombardy region. Update lat/lon if needed!
weather_url = "https://api.open-meteo.com/v1/forecast?latitude=45.6&longitude=9.2&current_weather=true"
try:
    res = requests.get(weather_url).json()
    temp = f"{round(res['current_weather']['temperature'])}°C"
    condition_code = res['current_weather']['weathercode']
    
    # Simple mapping
    if condition_code == 0: cond_text = "Clear Skies"
    elif condition_code in [1, 2, 3]: cond_text = "Partly Cloudy"
    elif condition_code in [45, 48]: cond_text = "Foggy"
    elif condition_code in [51, 53, 55, 61, 63, 65]: cond_text = "Raining"
    else: cond_text = "Overcast"
except Exception:
    temp, cond_text = "--°C", "Weather Error"

# Draw Time & Weather on the Left
now = datetime.now()
time_str = now.strftime("%H:%M")
date_str = now.strftime("%A, %b %d")

draw.text((80, 100), time_str, font=font_large, fill=0)
draw.text((80, 260), date_str, font=font_medium, fill=0)
draw.text((80, 450), f"Current: {temp}", font=font_large, fill=0)
draw.text((80, 600), cond_text, font=font_medium, fill=0)

# 3. Draw UI Divider Line
draw.line([(700, 80), (700, 992)], fill=0, width=5)

# 4. Fetch & Draw Calendar Agenda (Right Column)
draw.text((750, 100), "UPCOMING AGENDA", font=font_medium, fill=0)
draw.line([(750, 160), (1350, 160)], fill=0, width=2)

calendar_url = os.environ.get("CALENDAR_URL")
y_offset = 200

if calendar_url:
    print("Fetching calendar...")
    try:
        ics_data = requests.get(calendar_url).text
        cal = Calendar.from_ical(ics_data)
        events = []
        
        for component in cal.walk():
            if component.name == "VEVENT":
                summary = component.get('summary')
                dtstart = component.get('dtstart').dt
                
                # Handle all-day vs timed events safely
                if isinstance(dtstart, datetime):
                    event_date = dtstart.date()
                    time_label = dtstart.strftime("%H:%M")
                else:
                    event_date = dtstart
                    time_label = "All Day"
                
                # Only keep future/today events
                if event_date >= now.date():
                    events.append((event_date, time_label, str(summary)))
        
        # Sort events chronologically
        events.sort(key=lambda x: (x[0], x[1]))
        
        # Print top 6 events
        for ev_date, ev_time, ev_sum in events[:6]:
            date_display = ev_date.strftime("%b %d")
            display_text = f"[{date_display} - {ev_time}] {ev_sum}"
            
            # Text truncation to avoid overflow wrapper crash
            if len(display_text) > 40:
                display_text = display_text[:37] + "..."
                
            draw.text((750, y_offset), display_text, font=font_small, fill=0)
            y_offset += 100
            
    except Exception as e:
        draw.text((750, y_offset), f"Calendar Error: Connected link failed", font=font_small, fill=0)
else:
    draw.text((750, y_offset), "No Calendar Link Configured", font=font_small, fill=0)

# 5. Save the image completely flat for E-ink
image.save("dashboard.png", "PNG")
print("Dashboard.png successfully rendered locally!")
