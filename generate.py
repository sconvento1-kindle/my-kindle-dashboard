import os
import datetime
import json
import math
from PIL import Image, ImageDraw, ImageFont
import requests
import pytz
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Configuration profiles
PROFILES = {
    "KINDLE_BASIC": {
        "width": 800,
        "height": 600,
        "font_header_size": 40,
        "font_medium_size": 22,
        "font_regular_size": 16,
        "font_small_size": 12,
        "margin_x": 40,
        "header_y": 20,
        "date_y": 70,
        "line1_y": 110,
        "weather_title_y": 130,
        "forecast_y": 170,
        "line2_y": 330,
        "cal_title_y": 350,
        "events_start_y": 390,
        "event_step": 32,
        "last_update_y": 570,
        "max_event_len": 45,
        "weather_icon_size": 50
    },
    "KINDLE_PW4_PORTRAIT": {
        "width": 1072,
        "height": 1448,
        "font_header_size": 60,
        "font_medium_size": 35,
        "font_regular_size": 26,
        "font_small_size": 20,
        "margin_x": 80,
        "header_y": 60,
        "date_y": 140,
        "line1_y": 210,
        "weather_title_y": 240,
        "forecast_y": 300,
        "line2_y": 580,
        "cal_title_y": 610,
        "events_start_y": 680,
        "event_step": 85,
        "last_update_y": 1360,
        "max_event_len": 50,
        "weather_icon_size": 80
    }
}

# Select profile
PROFILE_NAME = os.environ.get("KINDLE_PROFILE", "KINDLE_PW4_PORTRAIT")
cfg = PROFILES.get(PROFILE_NAME, PROFILES["KINDLE_PW4_PORTRAIT"])

WIDTH, HEIGHT = cfg["width"], cfg["height"]
OUTPUT_DIR = "output"
BG_COLOR = 255
FG_COLOR = 0

# Helper to draw weather icons
def draw_sun(draw, cx, cy, r):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=FG_COLOR, width=3)
    for i in range(8):
        angle = math.radians(i * 45)
        x1 = cx + int((r + 4) * math.cos(angle))
        y1 = cy + int((r + 4) * math.sin(angle))
        x2 = cx + int((r + 12) * math.cos(angle))
        y2 = cy + int((r + 12) * math.sin(angle))
        draw.line([(x1, y1), (x2, y2)], fill=FG_COLOR, width=3)

def draw_cloud(draw, cx, cy, r):
    # Left circle
    draw.ellipse([cx - r, cy - r*0.2, cx - r*0.2, cy + r*0.6], fill=BG_COLOR, outline=FG_COLOR, width=3)
    # Right circle
    draw.ellipse([cx + r*0.2, cy - r*0.1, cx + r, cy + r*0.5], fill=BG_COLOR, outline=FG_COLOR, width=3)
    # Center circle
    draw.ellipse([cx - r*0.6, cy - r*0.7, cx + r*0.6, cy + r*0.5], fill=BG_COLOR, outline=FG_COLOR, width=3)
    # Erase inner lines
    draw.ellipse([cx - r*0.5, cy - r*0.6, cx + r*0.5, cy + r*0.4], fill=BG_COLOR)
    draw.ellipse([cx - r*0.9, cy - r*0.1, cx - r*0.3, cy + r*0.5], fill=BG_COLOR)
    draw.ellipse([cx + r*0.3, cy, cx + r*0.9, cy + r*0.4], fill=BG_COLOR)
    draw.rectangle([cx - r*0.6, cy, cx + r*0.6, cy + r*0.5], fill=BG_COLOR)
    # Draw bottom flat line
    draw.line([(cx - r, cy + r*0.5), (cx + r, cy + r*0.5)], fill=FG_COLOR, width=3)

def draw_rain(draw, cx, cy, r):
    draw_cloud(draw, cx, cy - r*0.2, r)
    # Rain drops
    y_start = cy + r*0.4
    y_end = cy + r*0.8
    draw.line([(cx - r*0.4, y_start), (cx - r*0.5, y_end)], fill=FG_COLOR, width=3)
    draw.line([(cx, y_start), (cx - r*0.1, y_end)], fill=FG_COLOR, width=3)
    draw.line([(cx + r*0.4, y_start), (cx + r*0.3, y_end)], fill=FG_COLOR, width=3)

def draw_thunder(draw, cx, cy, r):
    draw_cloud(draw, cx, cy - r*0.2, r)
    # Lightning bolt
    y1 = cy + r*0.3
    y2 = cy + r*0.6
    y3 = cy + r*1.0
    draw.line([(cx, y1), (cx - r*0.3, y2)], fill=FG_COLOR, width=3)
    draw.line([(cx - r*0.3, y2), (cx + r*0.2, y2)], fill=FG_COLOR, width=3)
    draw.line([(cx + r*0.2, y2), (cx - r*0.1, y3)], fill=FG_COLOR, width=3)

def draw_snow(draw, cx, cy, r):
    draw_cloud(draw, cx, cy - r*0.2, r)
    # Snowflakes (dots)
    y = cy + r*0.6
    draw.ellipse([cx - r*0.5 - 2, y - 2, cx - r*0.5 + 2, y + 2], fill=FG_COLOR)
    draw.ellipse([cx, y + r*0.3 - 2, cx, y + r*0.3 + 2], fill=FG_COLOR)
    draw.ellipse([cx + r*0.5 - 2, y - 2, cx + r*0.5 + 2, y + 2], fill=FG_COLOR)

def draw_fog(draw, cx, cy, r):
    draw.line([(cx - r, cy - r*0.4), (cx + r, cy - r*0.4)], fill=FG_COLOR, width=3)
    draw.line([(cx - r*0.8, cy), (cx + r*0.8, cy)], fill=FG_COLOR, width=3)
    draw.line([(cx - r, cy + r*0.4), (cx + r, cy + r*0.4)], fill=FG_COLOR, width=3)

def draw_weather_icon(draw, code, x, y, size):
    cx = x + size // 2
    cy = y + size // 2
    r = size // 4
    
    # Map WMO codes to drawing functions
    if code in [0, 1]:
        draw_sun(draw, cx, cy, r)
    elif code in [2, 3]:
        draw_cloud(draw, cx, cy, r)
    elif code in [45, 48]:
        draw_fog(draw, cx, cy, r)
    elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        draw_rain(draw, cx, cy, r)
    elif code in [71, 73, 75, 77, 85, 86]:
        draw_snow(draw, cx, cy, r)
    elif code in [95, 96, 99]:
        draw_thunder(draw, cx, cy, r)
    else:
        draw_cloud(draw, cx, cy, r)

def get_italian_day_name(dt):
    days = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    return days[dt.weekday()]

def get_real_weather():
    if os.environ.get("MOCK_MODE") == "1":
        return [
            {"day": "Oggi", "temp_max": 34, "temp_min": 23, "code": 1},
            {"day": "Domani", "temp_max": 37, "temp_min": 27, "code": 80},
            {"day": "Dom", "temp_max": 35, "temp_min": 26, "code": 3},
            {"day": "Lun", "temp_max": 32, "temp_min": 22, "code": 0},
            {"day": "Mar", "temp_max": 30, "temp_min": 20, "code": 2}
        ]
    
    LAT, LON = 45.6485, 9.2044
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe%2FRome&forecast_days=5"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        daily = data["daily"]
        
        forecast_data = []
        for i in range(5):
            date_str = daily["time"][i]
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            
            if i == 0:
                day_name = "Oggi"
            elif i == 1:
                day_name = "Domani"
            else:
                day_name = get_italian_day_name(dt)
                
            forecast_data.append({
                "day": day_name,
                "temp_max": round(daily["temperature_2m_max"][i]),
                "temp_min": round(daily["temperature_2m_min"][i]),
                "code": daily["weather_code"][i]
            })
            
        return forecast_data
    except Exception as e:
        print(f"Errore meteo: {e}")
        return None

def get_google_calendar_events():
    if os.environ.get("MOCK_MODE") == "1":
        return [
            "- Oggi, 18:30: Aperitivo con amici",
            "- 27/06 09:00: Riunione di condominio",
            "- 28/06 11:00: Pranzo dai nonni",
            "- 29/06 14:00: Dentista",
            "- 02/07 (Tutto il giorno): Compleanno",
            "- 05/07 10:00: Spesa grossa"
        ]

    calendar_id = os.environ.get("CALENDAR_URL")
    creds_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")
    
    if not calendar_id or not creds_json:
        return ["- Errore: Secrets non configurati"]
    
    creds_data = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_data, scopes=['https://www.googleapis.com/auth/calendar.readonly'])
    service = build('calendar', 'v3', credentials=credentials)
    
    now_utc = datetime.datetime.utcnow().isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId=calendar_id, 
        timeMin=now_utc,
        maxResults=6,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    if not events:
        return ["Nessun impegno in programma"]
    
    formatted_events = []
    fuso_orario = pytz.timezone('Europe/Rome')
    
    for event in events:
        summary = event.get('summary', 'Impegno senza titolo')
        start = event['start'].get('dateTime', event['start'].get('date'))
        
        if 'T' in start:
            start_dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(fuso_orario)
            oggi = datetime.datetime.now(fuso_orario).date()
            if start_dt.date() == oggi:
                time_str = f"Oggi, {start_dt.strftime('%H:%M')}"
            else:
                time_str = start_dt.strftime('%d/%m %H:%M')
        else:
            start_date = datetime.date.fromisoformat(start)
            time_str = f"{start_date.strftime('%d/%m')} (Tutto il giorno)"
            
        formatted_events.append(f"- {time_str}: {summary}")
        
    return formatted_events

def create_dashboard():
    img = Image.new('L', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    
    if not os.path.exists(font_path):
        font_path = "DejaVuSans.ttf"
        font_bold_path = "DejaVuSans-Bold.ttf"

    try:
        font_header = ImageFont.truetype(font_bold_path, cfg["font_header_size"])
        font_medium = ImageFont.truetype(font_bold_path, cfg["font_medium_size"])
        font_regular = ImageFont.truetype(font_path, cfg["font_regular_size"])
        font_small = ImageFont.truetype(font_path, cfg["font_small_size"])
        font_bold_small = ImageFont.truetype(font_bold_path, cfg["font_small_size"])
    except IOError:
        print("Font non trovati, uso default")
        font_header = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_regular = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_bold_small = ImageFont.load_default()

    fuso_orario = pytz.timezone('Europe/Rome')
    now = datetime.datetime.now(fuso_orario)
    
    # 1. Header (Custom Text)
    header_str = "Silvia & Niki's Home"
    w_header = draw.textlength(header_str, font=font_header)
    draw.text(((WIDTH - w_header) / 2, cfg["header_y"]), header_str, font=font_header, fill=FG_COLOR)
    
    # Date Subheader
    days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    months = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    date_str = f"{days[now.weekday()]} {now.day} {months[now.month-1]} {now.year}"
    w_date = draw.textlength(date_str, font=font_regular)
    draw.text(((WIDTH - w_date) / 2, cfg["date_y"]), date_str, font=font_regular, fill=FG_COLOR)

    # Linea 1
    draw.line([(cfg["margin_x"], cfg["line1_y"]), (WIDTH - cfg["margin_x"], cfg["line1_y"])], fill=FG_COLOR, width=2)

    # 2. Weather Section (Weekly Forecast)
    draw.text((cfg["margin_x"], cfg["weather_title_y"]), "METEO SETTIMANALE (Seregno)", font=font_medium, fill=FG_COLOR)
    
    weather = get_real_weather()
    if weather:
        y_forecast = cfg["forecast_y"]
        col_width = (WIDTH - 2 * cfg["margin_x"]) / 5
        icon_size = cfg["weather_icon_size"]
        
        for i, fc in enumerate(weather):
            col_x = cfg["margin_x"] + i * col_width
            cx = col_x + col_width // 2
            
            # Day name
            w_day = draw.textlength(fc["day"], font=font_regular)
            draw.text((cx - w_day / 2, y_forecast), fc["day"], font=font_regular, fill=FG_COLOR)
            
            # Icon
            icon_x = cx - icon_size // 2
            icon_y = y_forecast + 50
            draw_weather_icon(draw, fc["code"], icon_x, icon_y, icon_size)
            
            # Temp Max / Min
            temp_str = f"{fc['temp_max']}° / {fc['temp_min']}°"
            w_temp = draw.textlength(temp_str, font=font_small)
            draw.text((cx - w_temp / 2, icon_y + icon_size + 20), temp_str, font=font_bold_small, fill=FG_COLOR)
            
            # Vertical separator
            if i > 0:
                draw.line([(col_x, y_forecast), (col_x, y_forecast + icon_size + 90)], fill=FG_COLOR, width=1)
    else:
        draw.text((cfg["margin_x"], cfg["forecast_y"]), "Dati Meteo Non Disponibili", font=font_regular, fill=FG_COLOR)

    # Linea 2
    draw.line([(cfg["margin_x"], cfg["line2_y"]), (WIDTH - cfg["margin_x"], cfg["line2_y"])], fill=FG_COLOR, width=2)

    # 3. Calendar Section
    draw.text((cfg["margin_x"], cfg["cal_title_y"]), "I PROSSIMI IMPEGNI", font=font_medium, fill=FG_COLOR)
    
    try:
        eventi = get_google_calendar_events()
    except Exception as e:
        error_msg = str(e).replace('\n', ' ').strip()
        eventi = [f"- Errore Calendario: {error_msg[:45]}..."]
    
    y_offset = cfg["events_start_y"]
    for evento in eventi:
        if len(evento) > cfg["max_event_len"]:
            evento = evento[:cfg["max_event_len"]-3] + "..."
        draw.text((cfg["margin_x"], y_offset), evento, font=font_regular, fill=FG_COLOR)
        y_offset += cfg["event_step"]

    # Footer: Info Ultimo Aggiornamento
    time_str = now.strftime("%H:%M")
    date_update_str = now.strftime("%d/%m")
    footer_str = f"Ultimo aggiornamento: {date_update_str} alle {time_str}"
    w_footer = draw.textlength(footer_str, font=font_small)
    draw.text(((WIDTH - w_footer) / 2, cfg["last_update_y"]), footer_str, font=font_small, fill=FG_COLOR)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    img_grayscale = img.convert('L')
    img_grayscale.putpixel((0, 0), 250)
    img_grayscale.save(os.path.join(OUTPUT_DIR, "dashboard.png"), "PNG")
    
    print(f"Dashboard generata con successo alle ore: {time_str} del {date_str}")

if __name__ == "__main__":
    create_dashboard()
