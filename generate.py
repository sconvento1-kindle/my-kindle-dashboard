import os
import datetime
import json
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
        "font_large_size": 74,
        "font_medium_size": 28,
        "font_regular_size": 22,
        "margin_x": 80,
        "time_y": 40,
        "date_y": 130,
        "line1_y": 190,
        "cal_title_y": 220,
        "events_start_y": 270,
        "event_step": 40,
        "line2_y": 430,
        "weather_title_y": 455,
        "weather_info_y": 500,
        "battery_y": 540,
        "max_event_len": 55
    },
    "KINDLE_PW4_LANDSCAPE": {
        "width": 1448,
        "height": 1072,
        "font_large_size": 130,
        "font_medium_size": 50,
        "font_regular_size": 40,
        "margin_x": 144,
        "time_y": 72,
        "date_y": 234,
        "line1_y": 342,
        "cal_title_y": 396,
        "events_start_y": 486,
        "event_step": 72,
        "line2_y": 774,
        "weather_title_y": 819,
        "weather_info_y": 900,
        "battery_y": 972,
        "max_event_len": 55
    },
    "KINDLE_PW4_PORTRAIT": {
        "width": 1072,
        "height": 1448,
        "font_large_size": 99,
        "font_medium_size": 37,
        "font_regular_size": 29,
        "margin_x": 107,
        "time_y": 96,
        "date_y": 313,
        "line1_y": 457,
        "cal_title_y": 530,
        "events_start_y": 650,
        "event_step": 96,
        "line2_y": 1036,
        "weather_title_y": 1096,
        "weather_info_y": 1205,
        "battery_y": 1301,
        "max_event_len": 45
    }
}

# Select profile
PROFILE_NAME = os.environ.get("KINDLE_PROFILE", "KINDLE_PW4_LANDSCAPE")
cfg = PROFILES.get(PROFILE_NAME, PROFILES["KINDLE_PW4_LANDSCAPE"])

WIDTH, HEIGHT = cfg["width"], cfg["height"]
OUTPUT_DIR = "output"
BG_COLOR = 255
FG_COLOR = 0

def get_real_weather():
    if os.environ.get("MOCK_MODE") == "1":
        return "18°C, Pioggia Leggera (Mock)"
    
    LAT, LON = 45.6485, 9.2044
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,weather_code&timezone=Europe%2FRome"
    weather_codes = {
        0: "Cielo Sereno", 1: "Preval. Sereno", 2: "Parz. Nuvoloso", 3: "Nuvoloso",
        45: "Nebbia", 48: "Nebbia Brinata", 51: "Pioggerella Leggera", 53: "Pioggerella",
        61: "Pioggia Leggera", 63: "Pioggia Modesta", 65: "Pioggia Forte",
        71: "Neve Leggera", 73: "Neve Modesta", 75: "Neve Forte",
        80: "Rovesci di Pioggia", 95: "Temporale"
    }
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        current = data["current"]
        temp = round(current["temperature_2m"])
        code = current["weather_code"]
        condizione = weather_codes.get(code, "Variabile")
        return f"{temp}°C, {condizione}"
    except Exception:
        return "Dati Non Disponibili"

def get_google_calendar_events():
    if os.environ.get("MOCK_MODE") == "1":
        return [
            "- Oggi, 18:30: Aperitivo con amici",
            "- 27/06 09:00: Riunione di condominio",
            "- 28/06 (Tutto il giorno): Compleanno Mamma"
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
        maxResults=3, 
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
    # Crea l'immagine in scala di grigi nativa (8-bit)
    img = Image.new('L', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Try to use a system font, fallback to default if not found
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    
    # Fallback to local directory if they are there (for GitHub Actions)
    if not os.path.exists(font_path):
        font_path = "DejaVuSans.ttf"
        font_bold_path = "DejaVuSans-Bold.ttf"

    try:
        font_large = ImageFont.truetype(font_bold_path, cfg["font_large_size"])
        font_medium = ImageFont.truetype(font_bold_path, cfg["font_medium_size"])
        font_regular = ImageFont.truetype(font_path, cfg["font_regular_size"])
    except IOError:
        print("Font non trovati, uso font di default (il layout potrebbe essere sballato)")
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_regular = ImageFont.load_default()

    fuso_orario = pytz.timezone('Europe/Rome')
    now = datetime.datetime.now(fuso_orario)
    
    time_str = now.strftime("%H:%M")
    days = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    months = ["GEN", "FEB", "MAR", "APR", "MAG", "GIU", "LUG", "AGO", "SET", "OTT", "NOV", "DIC"]
    date_str = f"{days[now.weekday()]} {now.day} {months[now.month-1]} {now.year}"

    w_time = draw.textlength(time_str, font=font_large)
    draw.text(((WIDTH - w_time) / 2, cfg["time_y"]), time_str, font=font_large, fill=FG_COLOR)
    
    w_date = draw.textlength(date_str, font=font_medium)
    draw.text(((WIDTH - w_date) / 2, cfg["date_y"]), date_str, font=font_medium, fill=FG_COLOR)

    draw.line([(cfg["margin_x"], cfg["line1_y"]), (WIDTH - cfg["margin_x"], cfg["line1_y"])], fill=FG_COLOR, width=2)

    draw.text((cfg["margin_x"], cfg["cal_title_y"]), "IL TUO CALENDARIO", font=font_medium, fill=FG_COLOR)
    
    try:
        eventi = get_google_calendar_events()
    except Exception as e:
        error_msg = str(e).replace('\n', ' ').strip()
        if "HttpError" in error_msg or "API" in error_msg:
            eventi = [f"- Errore Google: {error_msg[:45]}..."]
        else:
            eventi = [f"- Errore: {error_msg[:50]}"]
    
    y_offset = cfg["events_start_y"]
    for evento in eventi:
        if len(evento) > cfg["max_event_len"]:
            evento = evento[:cfg["max_event_len"]-3] + "..."
        draw.text((cfg["margin_x"], y_offset), evento, font=font_regular, fill=FG_COLOR)
        y_offset += cfg["event_step"]

    draw.line([(cfg["margin_x"], cfg["line2_y"]), (WIDTH - cfg["margin_x"], cfg["line2_y"])], fill=FG_COLOR, width=2)

    weather_info = get_real_weather()
    draw.text((cfg["margin_x"], cfg["weather_title_y"]), "METEO SEREGNO", font=font_medium, fill=FG_COLOR)
    draw.text((cfg["margin_x"], cfg["weather_info_y"]), weather_info, font=font_regular, fill=FG_COLOR)
    draw.text((cfg["margin_x"], cfg["battery_y"]), "🔋 82%   |   Temp. Esterna", font=font_regular, fill=FG_COLOR)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # Forza la conversione in scala di grigi 'L' (8-bit)
    img_grayscale = img.convert('L')
    
    # TRUCCO FONDAMENTALE: Coloriamo il primissimo pixel (0,0) in alto a sinistra 
    # con un grigio quasi invisibile (250 invece di 255 bianco).
    # Questo costringe Pillow a salvare una PNG a 8-bit REALI, disattivando l'ottimizzazione a 1-bit.
    img_grayscale.putpixel((0, 0), 250)
    
    # Salviamo in formato PNG originale
    img_grayscale.save(os.path.join(OUTPUT_DIR, "dashboard.png"), "PNG")
    
    print(f"Dashboard generata con successo alle ore: {time_str} del {date_str}")


if __name__ == "__main__":
    create_dashboard()
