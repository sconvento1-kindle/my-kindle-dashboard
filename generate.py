import os
import datetime
import glob
import requests
from PIL import Image, ImageDraw, ImageFont
from icalendar import Calendar

# 1. Canvas Configuration (Portrait layout)
WIDTH, HEIGHT = 1080, 1440
BLACK, WHITE = 0, 255
image = Image.new("L", (WIDTH, HEIGHT), WHITE)
draw = ImageDraw.Draw(image)

# 2. Font Setup
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
        font_large = ImageFont.truetype(selected_font, 120)   # Main Clock
        font_medium = ImageFont.truetype(selected_font, 42)   # Date / Headers
        font_small = ImageFont.truetype(selected_font, 28)    # Regular Details
        font_tiny = ImageFont.truetype(selected_font, 22)     # Forecast labels
    else:
        raise IOError
except Exception:
    font_large = font_medium = font_small = font_tiny = ImageFont.load_default()

# 3. Weather Fetching (Current + Forecast)
weather_main = "Sunny"
temp_current = "18.6°C"
temp_high_low = "28.7°C / 14.9°C"

# Default fallback forecast data (Tue - Sat)
forecast_data = [
    {"day": "Tue", "icon": "sunny", "high": "28.7°", "low": "14.9°"},
    {"day": "Wed", "icon": "cloudy", "high": "24.1°", "low": "14.2°"},
    {"day": "Thu", "icon": "cloudy", "high": "23.7°", "low": "9.5°"},
    {"day": "Fri", "icon": "cloudy", "high": "20.2°", "low": "9.3°"},
    {"day": "Sat", "icon": "cloudy", "high": "19.2°", "low": "8.5°"}
]

api_key = os.environ.get("WEATHER_API_KEY")
if api_key:
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q=Seregno,it&units=metric&appid={api_key}"
        data = requests.get(url).json()
        
        current = data['list'][0]
        temp_current = f"{round(current['main']['temp'], 1)}°C"
        weather_main = current['weather'][0]['main']
        
        daily_temps = {}
        for item in data['list']:
            date_str = item['dt_txt'].split(" ")[0]
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            day_name = dt.strftime("%a")
            
            if day_name not in daily_temps:
                daily_temps[day_name] = {"temps": [], "icons": []}
            daily_temps[day_name]["temps"].append(item['main']['temp'])
            daily_temps[day_name]["icons"].append(item['weather'][0]['main'].lower())

        today_name = datetime.datetime.now().strftime("%a")
        if today_name in daily_temps:
            temp_high_low = f"{round(max(daily_temps[today_name]['temps']), 1)}°C / {round(min(daily_temps[today_name]['temps']), 1)}°C"

        forecast_data = []
        now_dt = datetime.datetime.now()
        
        for i in range(5):
            target_day = (now_dt + datetime.timedelta(days=i)).strftime("%a")
            if target_day in daily_temps:
                temps = daily_temps[target_day]["temps"]
                weather_type = daily_temps[target_day]["icons"][0]
                icon_type = "sunny" if "clear" in weather_type or "sun" in weather_type else "cloudy"
                
                forecast_data.append({
                    "day": target_day,
                    "icon": icon_type,
                    "high": f"{round(max(temps), 1)}°",
                    "low": f"{round(min(temps), 1)}°"
                })
    except Exception:
        pass

# 4. Calendar Fetching
calendar_events = []
ical_url = os.environ.get("CALENDAR_ICAL_URL")
if ical_url:
    try:
        response = requests.get(ical_url, timeout=10)
        gcal = Calendar.from_ical(response.content)
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        future_dt = now_dt + datetime.timedelta(days=14)
        
        raw_events = []
        for component in gcal.walk():
            if component.name == "VEVENT":
                summary = str(component.get('summary'))
                start = component.get('dtstart').dt
                if isinstance(start, datetime.date) and not isinstance(start, datetime.datetime):
                    start_dt = datetime.datetime.combine(start, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
                    all_day = True
                else:
                    start_dt = start.astimezone(datetime.timezone.utc) if start.tzinfo else start.replace(tzinfo=datetime.timezone.utc)
                    all_day = False
                
                if now_dt <= start_dt <= future_dt:
                    raw_events.append((start_dt, summary, all_day))
        
        raw_events.sort(key=lambda x: x[0])
        for start_dt, summary, all_day in raw_events[:10]:
            local_start = start_dt.astimezone()
            date_str = local_start.strftime("%b %d - %H:%M") if not all_day else f"{local_start.strftime('%b %d')} - All Day"
            calendar_events.append(f"[{date_str}] {summary}")
    except Exception:
        calendar_events = ["Could not sync calendar feed."]

if not calendar_events:
    calendar_events = ["No upcoming events today."]

# --- DRAW COMPACT CONTAINER INTERFACE ---

# 1. Left Column / Top Section: Clock & Date
now = datetime.datetime.now()
draw.text((60, 80), now.strftime("%H:%M"), fill=BLACK, font=font_large)
draw.text((60, 210), now.strftime("%A, %b %d"), fill=BLACK, font=font_medium)

# 2. Weather Container Card
card_x1, card_y1 = 60, 320
card_x2, card_y2 = WIDTH - 60, 780
card_r = 24

draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=card_r, outline=BLACK, width=3)

# Helper function to draw crisp icons manually with validated closures
def draw_weather_icon(cx, cy, type_str):
    if type_str == "sunny":
        draw.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], fill=WHITE, outline=BLACK, width=4)
    else:  # Cloudy overlapping shapes
        draw.ellipse([cx - 22, cy - 10, cx + 10, cy + 22], fill=WHITE, outline=BLACK, width=4)
        draw.ellipse([cx - 5, cy - 22, cx + 25, cy + 18], fill=WHITE, outline=BLACK, width=4)

# Render main card info
main_icon_type = "sunny" if "sun" in weather_main.lower() or "clear" in weather_main.lower() else "cloudy"
draw_weather_icon(140, 420, main_icon_type)

draw.text((230, 370), weather_main, fill=BLACK, font=font_medium)
draw.text((230, 425), "AccuWeather", fill=BLACK, font=font_small)

draw.text((card_x2 - 250, 370), temp_current, fill=BLACK, font=font_medium)
draw.text((card_x2 - 250, 425), temp_high_low, fill=BLACK, font=font_small)

# Draw horizontal forecast segment labels inside card
start_row_x = card_x1 + 40
row_width = (card_x2 - card_x1 - 80) // 4
icon_y = 570

for idx, day in enumerate(forecast_data[:5]):
    pos_x = start_row_x + (idx * row_width)
    if idx == 4:
        pos_x = card_x2 - 70
        
    draw.text((pos_x - 20, 500), day["day"], fill=BLACK, font=font_small)
    draw_weather_icon(pos_x, icon_y, day["icon"])
    draw.text((pos_x - 30, 640), day["high"], fill=BLACK, font=font_small)
    draw.text((pos_x - 30, 685), day["low"], fill=BLACK, font=font_small)

# 3. Bottom Section: Upcoming Agenda Box
draw.text((60, 840), "UPCOMING AGENDA", fill=BLACK, font=font_medium)
draw.line([(60, 900), (WIDTH - 60, 900)], fill=BLACK, width=4)

y_offset = 940
for event in calendar_events[:5]:
    if len(event) > 65:
        event = event[:62] + "..."
    draw.text((60, y_offset), event, fill=BLACK, font=font_small)
    y_offset += 80

# Save final graphic
image.save("dashboard.png", "PNG")
