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
        "date_y": 65,
        "line1_y": 95,
        "curr_weather_y": 105,
        "curr_weather_icon_size": 60,
        "forecast_y": 190,
        "forecast_icon_size": 40,
        "line2_y": 310,
        "cal_title_y": 325,
        "events_start_y": 365,
        "event_step": 32,
        "quote_box_y1": 460,
        "quote_box_height": 90,
        "font_quote_size": 13,
        "font_quote_song_size": 10,
        "last_update_y": 570,
        "max_event_len": 45
    },
    "KINDLE_PW4_PORTRAIT": {
        "width": 1072,
        "height": 1448,
        "font_header_size": 60,
        "font_medium_size": 35,
        "font_regular_size": 26,
        "font_small_size": 20,
        "margin_x": 80,
        "header_y": 70,
        "date_y": 145,
        "line1_y": 210,
        "curr_weather_y": 230,
        "curr_weather_icon_size": 120,
        "forecast_y": 400,
        "forecast_icon_size": 100,
        "line2_y": 620,
        "cal_title_y": 650,
        "events_start_y": 720,
        "event_step": 85,
        "quote_box_y1": 1090,
        "quote_box_height": 210,
        "font_quote_size": 24,
        "font_quote_song_size": 18,
        "last_update_y": 1360,
        "max_event_len": 50
    }
}

# Select profile
PROFILE_NAME = os.environ.get("KINDLE_PROFILE", "KINDLE_PW4_PORTRAIT")
cfg_base = PROFILES.get(PROFILE_NAME, PROFILES["KINDLE_PW4_PORTRAIT"])

# Super-sampling scale factor (2x for anti-aliasing)
SCALE = 2

# Scale the configuration values dynamically
cfg = {}
for k, v in cfg_base.items():
    if k in ["width", "height", "max_event_len"]:
        cfg[k] = v
    elif isinstance(v, int):
        cfg[k] = v * SCALE
    else:
        cfg[k] = v
cfg["curr_weather_icon_size"] = cfg_base["curr_weather_icon_size"] * SCALE
cfg["forecast_icon_size"] = cfg_base["forecast_icon_size"] * SCALE

TARGET_WIDTH, TARGET_HEIGHT = cfg_base["width"], cfg_base["height"]
WIDTH, HEIGHT = TARGET_WIDTH * SCALE, TARGET_HEIGHT * SCALE

OUTPUT_DIR = "output"
BG_COLOR = 255
FG_COLOR = 0
BOX_BG_COLOR = 242 # Light gray (out of 255) for quote box background

# Helper to draw weather icons
def draw_sun(draw, cx, cy, r):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=FG_COLOR, width=4*SCALE)
    for i in range(8):
        angle = math.radians(i * 45)
        x1 = cx + int((r + r*0.15) * math.cos(angle))
        y1 = cy + int((r + r*0.15) * math.sin(angle))
        x2 = cx + int((r + r*0.5) * math.cos(angle))
        y2 = cy + int((r + r*0.5) * math.sin(angle))
        draw.line([(x1, y1), (x2, y2)], fill=FG_COLOR, width=4*SCALE)

def draw_cloud(draw, cx, cy, r):
    # Left circle
    draw.ellipse([cx - r, cy - r*0.2, cx - r*0.2, cy + r*0.6], fill=BG_COLOR, outline=FG_COLOR, width=4*SCALE)
    # Right circle
    draw.ellipse([cx + r*0.2, cy - r*0.1, cx + r, cy + r*0.5], fill=BG_COLOR, outline=FG_COLOR, width=4*SCALE)
    # Center circle
    draw.ellipse([cx - r*0.6, cy - r*0.7, cx + r*0.6, cy + r*0.5], fill=BG_COLOR, outline=FG_COLOR, width=4*SCALE)
    # Erase inner lines
    draw.ellipse([cx - r*0.5, cy - r*0.6, cx + r*0.5, cy + r*0.4], fill=BG_COLOR)
    draw.ellipse([cx - r*0.9, cy - r*0.1, cx - r*0.3, cy + r*0.5], fill=BG_COLOR)
    draw.ellipse([cx + r*0.3, cy, cx + r*0.9, cy + r*0.4], fill=BG_COLOR)
    draw.rectangle([cx - r*0.6, cy, cx + r*0.6, cy + r*0.5], fill=BG_COLOR)
    # Draw bottom flat line
    draw.line([(cx - r, cy + r*0.5), (cx + r, cy + r*0.5)], fill=FG_COLOR, width=4*SCALE)

def draw_sun_behind_cloud(draw, cx, cy, r):
    # Sun shifted top-right, slightly smaller
    draw_sun(draw, cx + r*0.4, cy - r*0.3, r*0.6)
    # Cloud centered-left, filled with white to cover sun
    draw_cloud(draw, cx - r*0.2, cy + r*0.2, r*0.9)

def draw_two_clouds(draw, cx, cy, r):
    # Back cloud, smaller
    draw_cloud(draw, cx + r*0.3, cy - r*0.2, r*0.75)
    # Front cloud, filled with white
    draw_cloud(draw, cx - r*0.2, cy + r*0.2, r*0.9)

def draw_rain(draw, cx, cy, r):
    draw_cloud(draw, cx, cy - r*0.2, r)
    # Rain drops
    y_start = cy + r*0.4
    y_end = cy + r*0.8
    draw.line([(cx - r*0.4, y_start), (cx - r*0.5, y_end)], fill=FG_COLOR, width=4*SCALE)
    draw.line([(cx, y_start), (cx - r*0.1, y_end)], fill=FG_COLOR, width=4*SCALE)
    draw.line([(cx + r*0.4, y_start), (cx + r*0.3, y_end)], fill=FG_COLOR, width=4*SCALE)

def draw_thunder(draw, cx, cy, r):
    draw_cloud(draw, cx, cy - r*0.2, r)
    # Lightning bolt
    y1 = cy + r*0.3
    y2 = cy + r*0.6
    y3 = cy + r*1.0
    draw.line([(cx, y1), (cx - r*0.3, y2)], fill=FG_COLOR, width=4*SCALE)
    draw.line([(cx - r*0.3, y2), (cx + r*0.2, y2)], fill=FG_COLOR, width=4*SCALE)
    draw.line([(cx + r*0.2, y2), (cx - r*0.1, y3)], fill=FG_COLOR, width=4*SCALE)

def draw_snow(draw, cx, cy, r):
    draw_cloud(draw, cx, cy - r*0.2, r)
    # Snowflakes (dots)
    y = cy + r*0.6
    dot_r = 2 * SCALE
    draw.ellipse([cx - r*0.5 - dot_r, y - dot_r, cx - r*0.5 + dot_r, y + dot_r], fill=FG_COLOR)
    draw.ellipse([cx - dot_r, y + r*0.3 - dot_r, cx + dot_r, y + r*0.3 + dot_r], fill=FG_COLOR)
    draw.ellipse([cx + r*0.5 - dot_r, y - dot_r, cx + r*0.5 + dot_r, y + dot_r], fill=FG_COLOR)

def draw_fog(draw, cx, cy, r):
    draw.line([(cx - r, cy - r*0.4), (cx + r, cy - r*0.4)], fill=FG_COLOR, width=4*SCALE)
    draw.line([(cx - r*0.8, cy), (cx + r*0.8, cy)], fill=FG_COLOR, width=4*SCALE)
    draw.line([(cx - r, cy + r*0.4), (cx + r, cy + r*0.4)], fill=FG_COLOR, width=4*SCALE)

def draw_music_note(draw, cx, cy, size):
    r_head = size // 4
    head_cx = cx - r_head
    head_cy = cy + r_head
    
    # Note head
    draw.ellipse([head_cx - r_head, head_cy - r_head, head_cx + r_head, head_cy + r_head], fill=FG_COLOR)
    
    # Stem
    stem_x = head_cx + r_head - 1*SCALE
    stem_top_y = cy - size // 2
    draw.line([(stem_x, head_cy), (stem_x, stem_top_y)], fill=FG_COLOR, width=3*SCALE)
    
    # Flag
    flag_end_x = stem_x + int(size * 0.4)
    flag_end_y = stem_top_y + int(size * 0.3)
    draw.line([(stem_x, stem_top_y), (flag_end_x, flag_end_y)], fill=FG_COLOR, width=3*SCALE)

def draw_weather_icon(draw, code, x, y, size):
    cx = x + size // 2
    cy = y + size // 2
    r = size // 4
    
    # Map WMO codes to drawing functions
    if code == 0:
        draw_sun(draw, cx, cy, r)
    elif code in [1, 2]:
        draw_sun_behind_cloud(draw, cx, cy, r)
    elif code == 3:
        draw_two_clouds(draw, cx, cy, r)
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
        return {
            "current_temp": 34,
            "current_humidity": 35,
            "current_wind": 12,
            "current_code": 1,
            "current_condition": "Parz. Nuvoloso",
            "forecast": [
                {"day": "Oggi", "temp_max": 34, "temp_min": 23, "code": 1},
                {"day": "Domani", "temp_max": 37, "temp_min": 27, "code": 80},
                {"day": "Dom", "temp_max": 35, "temp_min": 26, "code": 3},
                {"day": "Lun", "temp_max": 32, "temp_min": 22, "code": 0},
                {"day": "Mar", "temp_max": 30, "temp_min": 20, "code": 2}
            ]
        }
    
    LAT, LON = 45.6485, 9.2044
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe%2FRome&forecast_days=5"
    
    weather_codes = {
        0: "Sereno", 1: "Quasi Sereno", 2: "Parz. Nuvoloso", 3: "Nuvoloso",
        45: "Nebbia", 48: "Nebbia", 51: "Pioggerella", 53: "Pioggerella", 55: "Pioggerella",
        61: "Pioggia Leggera", 63: "Pioggia", 65: "Pioggia Forte",
        71: "Neve Leggera", 73: "Neve", 75: "Neve Forte",
        77: "Nevischio",
        80: "Rovesci Pioggia", 81: "Rovesci Pioggia", 82: "Rovesci Pioggia",
        85: "Rovesci Neve", 86: "Rovesci Neve",
        95: "Temporale", 96: "Temporale", 99: "Temporale"
    }
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        current = data["current"]
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
            
        return {
            "current_temp": round(current["temperature_2m"]),
            "current_humidity": round(current["relative_humidity_2m"]),
            "current_wind": round(current["wind_speed_10m"]),
            "current_code": current["weather_code"],
            "current_condition": weather_codes.get(current["weather_code"], "Variabile"),
            "forecast": forecast_data
        }
    except Exception as e:
        print(f"Errore meteo: {e}")
        return None

def get_google_calendar_events():
    if os.environ.get("MOCK_MODE") == "1":
        return [
            "- Oggi, 18:30: Aperitivo con amici",
            "- 27/06 09:00: Riunione di condominio",
            "- 28/06 11:00: Pranzo dai nonni",
            "- 29/06 14:00: Dentista"
        ]

    calendar_id = os.environ.get("CALENDAR_URL")
    creds_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")
    
    if not calendar_id or not creds_json:
        return ["- Errore: Secrets non configurati"]
    
    creds_data = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_data, scopes=['https://www.googleapis.com/auth/calendar.readonly'])
    service = build('calendar', 'v3', credentials=credentials)
    
    # Calculate timeMin (start of today in Rome time, converted to UTC)
    fuso_orario = pytz.timezone('Europe/Rome')
    now_rome = datetime.datetime.now(fuso_orario)
    start_of_today_rome = now_rome.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_today_utc = start_of_today_rome.astimezone(pytz.utc)
    time_min_str = start_of_today_utc.isoformat().replace('+00:00', 'Z')
    
    # Calculate timeMax (start of today + 8 days in Rome time, to cover all of the 7th day, converted to UTC)
    end_of_period_rome = start_of_today_rome + datetime.timedelta(days=8)
    end_of_period_utc = end_of_period_rome.astimezone(pytz.utc)
    time_max_str = end_of_period_utc.isoformat().replace('+00:00', 'Z')
    
    events_result = service.events().list(
        calendarId=calendar_id, 
        timeMin=time_min_str,
        timeMax=time_max_str,
        maxResults=4, # Limit to 4 events to prevent overlap with quote
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    # --- RIGHE DI DEBUG ---
    print(f"DEBUG: API returned {len(events)} events raw.")
    for e in events:
        print(f"DEBUG: Event: {e.get('summary')} at {e['start'].get('dateTime', e['start'].get('date'))}")
    # ----------------------
    
    if not events:
        return ["Nessun impegno in programma"]
    
    formatted_events = []
    
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

def get_lyrics():
    # Load lyrics from local JSON file
    try:
        json_path = "lyrics.json"
        if not os.path.exists(json_path):
            # Try path relative to script directory
            script_dir = os.path.dirname(os.path.realpath(__file__))
            json_path = os.path.join(script_dir, "lyrics.json")
            
        with open(json_path, "r", encoding="utf-8") as f:
            lyrics_list = json.load(f)
        if not lyrics_list:
            return None
        
        fuso_orario = pytz.timezone('Europe/Rome')
        now = datetime.datetime.now(fuso_orario)
        day_of_year = now.timetuple().tm_yday
        
        # Select based on day of year to change once a day
        return lyrics_list[day_of_year % len(lyrics_list)]
    except Exception as e:
        print(f"Errore caricamento lyrics: {e}")
        return None

def wrap_text(text, font, max_width, draw):
    words = text.split(' ')
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        width = draw.textlength(test_line, font=font)
        if width <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines

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
        font_temp_large = ImageFont.truetype(font_bold_path, cfg["font_header_size"] + 30*SCALE)
        font_quote = ImageFont.truetype(font_path, cfg["font_quote_size"])
        font_quote_song = ImageFont.truetype(font_path, cfg["font_quote_song_size"])
    except IOError:
        print("Font non trovati, uso default")
        font_header = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_regular = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_bold_small = ImageFont.load_default()
        font_temp_large = ImageFont.load_default()
        font_quote = ImageFont.load_default()
        font_quote_song = ImageFont.load_default()

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
    draw.line([(cfg["margin_x"], cfg["line1_y"]), (WIDTH - cfg["margin_x"], cfg["line1_y"])], fill=FG_COLOR, width=2*SCALE)

    # Fetch weather data
    weather = get_real_weather()

    # 2. Current Weather Block (Hybrid Layout)
    if weather:
        curr_y = cfg["curr_weather_y"]
        icon_size_large = cfg["curr_weather_icon_size"]
        
        # Left: Large Icon
        icon_x = cfg["margin_x"]
        draw_weather_icon(draw, weather["current_code"], icon_x, curr_y, icon_size_large)
        
        # Center: Location, Condition, Humidity/Wind
        text_x = icon_x + icon_size_large + 30 * SCALE
        draw.text((text_x, curr_y + 5 * SCALE), "Seregno", font=font_medium, fill=FG_COLOR)
        draw.text((text_x, curr_y + 45 * SCALE), weather["current_condition"], font=font_regular, fill=FG_COLOR)
        
        details_str = f"Umidità: {weather['current_humidity']}%  |  Vento: {weather['current_wind']} km/h"
        draw.text((text_x, curr_y + 80 * SCALE), details_str, font=font_small, fill=FG_COLOR)
        
        # Right: Large Temp (No min/max below it)
        temp_str = f"{weather['current_temp']}°"
        w_temp = draw.textlength(temp_str, font=font_temp_large)
        temp_x = WIDTH - cfg["margin_x"] - w_temp
        draw.text((temp_x, curr_y + 10 * SCALE), temp_str, font=font_temp_large, fill=FG_COLOR)

    # 3. Weather Section (Weekly Forecast)
    if weather:
        y_forecast = cfg["forecast_y"]
        col_width = (WIDTH - 2 * cfg["margin_x"]) / 5
        icon_size = cfg["forecast_icon_size"]
        
        for i, fc in enumerate(weather["forecast"]):
            col_x = cfg["margin_x"] + i * col_width
            cx = col_x + col_width // 2
            
            # Day name
            w_day = draw.textlength(fc["day"], font=font_regular)
            draw.text((cx - w_day / 2, y_forecast), fc["day"], font=font_regular, fill=FG_COLOR)
            
            # Icon
            icon_x = cx - icon_size // 2
            icon_y = y_forecast + 40 * SCALE
            draw_weather_icon(draw, fc["code"], icon_x, icon_y, icon_size)
            
            # Temp Max / Min
            temp_str = f"{fc['temp_max']}° / {fc['temp_min']}°"
            w_temp = draw.textlength(temp_str, font=font_small)
            draw.text((cx - w_temp / 2, icon_y + icon_size + 15 * SCALE), temp_str, font=font_bold_small, fill=FG_COLOR)
            
            # Vertical separator
            if i > 0:
                draw.line([(col_x, y_forecast), (col_x, y_forecast + icon_size + 70 * SCALE)], fill=FG_COLOR, width=1*SCALE)
    else:
        draw.text((cfg["margin_x"], cfg["forecast_y"]), "Dati Meteo Non Disponibili", font=font_regular, fill=FG_COLOR)

    # Linea 2
    draw.line([(cfg["margin_x"], cfg["line2_y"]), (WIDTH - cfg["margin_x"], cfg["line2_y"])], fill=FG_COLOR, width=2*SCALE)

    # 4. Calendar Section
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

    # 5. Quote of the Day Section (Inside a rounded box card)
    quote_data = get_lyrics()
    if quote_data:
        box_y1 = cfg["quote_box_y1"]
        box_y2 = box_y1 + cfg["quote_box_height"]
        box_x1 = cfg["margin_x"]
        box_x2 = WIDTH - cfg["margin_x"]
        
        # Draw light gray rounded rectangle card
        draw.rounded_rectangle(
            [box_x1, box_y1, box_x2, box_y2], 
            radius=15*SCALE, 
            fill=BOX_BG_COLOR, 
            outline=FG_COLOR, 
            width=2*SCALE
        )
        
        # Draw Music Note Icon centered in the top part of the box
        music_icon_size = 25 * SCALE
        draw_music_note(draw, WIDTH // 2, box_y1 + 35 * SCALE, music_icon_size)
        
        # Quote Text wrapped (with extra padding for box borders)
        quote_text_formatted = f'"{quote_data["text"]}"'
        max_text_width = (box_x2 - box_x1) - 60 * SCALE # 30px padding on each side
        quote_lines = wrap_text(quote_text_formatted, font_quote, max_text_width, draw)
        
        y_curr = box_y1 + 75 * SCALE # Start drawing text below music note
        for line in quote_lines:
            w_line = draw.textlength(line, font=font_quote)
            draw.text(((WIDTH - w_line) / 2, y_curr), line, font=font_quote, fill=FG_COLOR)
            y_curr += cfg["quote_line_step"]
            
        # Song Info
        song_str = f"— {quote_data['song']}"
        w_song = draw.textlength(song_str, font=font_quote_song)
        draw.text(((WIDTH - w_song) / 2, y_curr + 10 * SCALE), song_str, font=font_quote_song, fill=FG_COLOR)

    # Footer: Info Ultimo Aggiornamento
    time_str = now.strftime("%H:%M")
    date_update_str = now.strftime("%d/%m")
    footer_str = f"Ultimo aggiornamento: {date_update_str} alle {time_str}"
    w_footer = draw.textlength(footer_str, font=font_small)
    draw.text(((WIDTH - w_footer) / 2, cfg["last_update_y"]), footer_str, font=font_small, fill=FG_COLOR)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # Resize high-res image back to target resolution with Lanczos filter
    img_grayscale = img.convert('L')
    img_grayscale.putpixel((0, 0), 250)
    
    img_resized = img_grayscale.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    img_resized.save(os.path.join(OUTPUT_DIR, "dashboard.png"), "PNG")
    
    print(f"Dashboard generata con successo alle ore: {time_str} del {date_str}")

if __name__ == "__main__":
    create_dashboard()
