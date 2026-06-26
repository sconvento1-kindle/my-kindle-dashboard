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
        "font_large_size": 48,
        "font_medium_size": 24,
        "font_regular_size": 18,
        "font_small_size": 14,
        "margin_x": 50,
        "date_y": 30,
        "line1_y": 100,
        "cal_title_y": 120,
        "events_start_y": 160,
        "event_step": 35,
        "line2_y": 380,
        "weather_title_y": 400,
        "weather_temp_y": 440,
        "weather_details_y": 500,
        "forecast_y": 530,
        "last_update_y": 575,
        "max_event_len": 45
    },
    "KINDLE_PW4_PORTRAIT": {
        "width": 1072,
        "height": 1448,
        "font_large_size": 80,
        "font_medium_size": 38,
        "font_regular_size": 28,
        "font_small_size": 22,
        "margin_x": 80,
        "date_y": 60,
        "line1_y": 210,
        "cal_title_y": 250,
        "events_start_y": 320,
        "event_step": 75,
        "line2_y": 780,
        "weather_title_y": 820,
        "weather_temp_y": 880,
        "weather_details_y": 1000,
        "forecast_y": 1120,
        "last_update_y": 1380,
        "max_event_len": 50
    },
    "KINDLE_PW4_LANDSCAPE": {
        "width": 1448,
        "height": 1072,
        "font_large_size": 80,
        "font_medium_size": 38,
        "font_regular_size": 28,
        "font_small_size": 22,
        "margin_x": 144,
        "date_y": 60,
        "line1_y": 160,
        "cal_title_y": 190,
        "events_start_y": 250,
        "event_step": 70,
        "line2_y": 680,
        "weather_title_y": 710,
        "weather_temp_y": 760,
        "weather_details_y": 880,
        "forecast_y": 950,
        "last_update_y": 1030,
        "max_event_len": 70
    }
}

# Select profile - Default to PORTRAIT now
PROFILE_NAME = os.environ.get("KINDLE_PROFILE", "KINDLE_PW4_PORTRAIT")
cfg = PROFILES.get(PROFILE_NAME, PROFILES["KINDLE_PW4_PORTRAIT"])

WIDTH, HEIGHT = cfg["width"], cfg["height"]
OUTPUT_DIR = "output"
BG_COLOR = 255
FG_COLOR = 0

def get_real_weather():
    if os.environ.get("MOCK_MODE") == "1":
        return {
            "current": {
                "temp": 34,
                "apparent": 36,
                "humidity": 35,
                "wind": 12,
                "condition": "Parz. Nuvoloso"
            },
            "forecast": [
                {"day": "Sab 27", "temp_max": 37, "temp_min": 27, "condition": "Rovesci Pioggia"},
                {"day": "Dom 28", "temp_max": 35, "temp_min": 26, "condition": "Nuvoloso"}
            ]
        }
    
    LAT, LON = 45.6485, 9.2044
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe%2FRome&forecast_days=3"
    
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
        
        current_data = {
            "temp": round(current["temperature_2m"]),
            "apparent": round(current["apparent_temperature"]),
            "humidity": round(current["relative_humidity_2m"]),
            "wind": round(current["wind_speed_10m"]),
            "condition": weather_codes.get(current["weather_code"], "Variabile")
        }
        
        forecast_data = []
        for i in range(1, 3):
            date_str = daily["time"][i]
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            day_formatted = dt.strftime("%d/%m")
            
            forecast_data.append({
                "day": day_formatted,
                "temp_max": round(daily["temperature_2m_max"][i]),
                "temp_min": round(daily["temperature_2m_min"][i]),
                "condition": weather_codes.get(daily["weather_code"][i], "Variabile")
            })
            
        return {
            "current": current_data,
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
            "- 29/06 14:00: Dentista",
            "- 02/07 (Tutto il giorno): Compleanno"
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
        maxResults=5,
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
        font_large = ImageFont.truetype(font_bold_path, cfg["font_large_size"])
        font_medium = ImageFont.truetype(font_bold_path, cfg["font_medium_size"])
        font_regular = ImageFont.truetype(font_path, cfg["font_regular_size"])
        font_small = ImageFont.truetype(font_path, cfg["font_small_size"])
        font_temp = ImageFont.truetype(font_bold_path, cfg["font_large_size"] + 20)
    except IOError:
        print("Font non trovati, uso default")
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_regular = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_temp = ImageFont.load_default()

    fuso_orario = pytz.timezone('Europe/Rome')
    now = datetime.datetime.now(fuso_orario)
    
    # Intestazione Data
    days = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]
    months = ["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"]
    date_str = f"{days[now.weekday()]} {now.day} {months[now.month-1]}"
    year_str = str(now.year)
    
    # Disegna Data Centrata
    w_date = draw.textlength(date_str, font=font_large)
    draw.text(((WIDTH - w_date) / 2, cfg["date_y"]), date_str, font=font_large, fill=FG_COLOR)
    
    w_year = draw.textlength(year_str, font=font_medium)
    draw.text(((WIDTH - w_year) / 2, cfg["date_y"] + cfg["font_large_size"] + 10), year_str, font=font_medium, fill=FG_COLOR)

    # Linea 1
    draw.line([(cfg["margin_x"], cfg["line1_y"]), (WIDTH - cfg["margin_x"], cfg["line1_y"])], fill=FG_COLOR, width=2)

    # Titolo Calendario
    draw.text((cfg["margin_x"], cfg["cal_title_y"]), "I PROSSIMI IMPEGNI", font=font_medium, fill=FG_COLOR)
    
    # Eventi Calendario
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

    # Linea 2
    draw.line([(cfg["margin_x"], cfg["line2_y"]), (WIDTH - cfg["margin_x"], cfg["line2_y"])], fill=FG_COLOR, width=2)

    # Sezione Meteo
    draw.text((cfg["margin_x"], cfg["weather_title_y"]), "METEO SEREGNO", font=font_medium, fill=FG_COLOR)
    
    weather = get_real_weather()
    if weather:
        curr = weather["current"]
        # Temperatura attuale gigante
        temp_str = f"{curr['temp']}°"
        draw.text((cfg["margin_x"], cfg["weather_temp_y"]), temp_str, font=font_temp, fill=FG_COLOR)
        
        # Condizioni e dettagli affiancati
        w_temp = draw.textlength(temp_str, font=font_temp)
        details_x = cfg["margin_x"] + w_temp + 40
        
        cond_str = curr["condition"]
        draw.text((details_x, cfg["weather_temp_y"] + 10), cond_str, font=font_medium, fill=FG_COLOR)
        
        details_str = f"Percepita: {curr['apparent']}°C  |  Vento: {curr['wind']} km/h  |  Umidità: {curr['humidity']}%"
        draw.text((cfg["margin_x"], cfg["weather_details_y"]), details_str, font=font_regular, fill=FG_COLOR)
        
        # Previsioni future (2 giorni) in colonne
        y_forecast = cfg["forecast_y"]
        col_width = (WIDTH - 2 * cfg["margin_x"]) / 2
        
        for i, fc in enumerate(weather["forecast"]):
            fc_x = cfg["margin_x"] + i * col_width
            # Linea verticale separatrice
            if i > 0:
                draw.line([(fc_x - 20, y_forecast), (fc_x - 20, y_forecast + 80)], fill=FG_COLOR, width=1)
                
            fc_title = f"{fc['day']}: {fc['temp_max']}° / {fc['temp_min']}°"
            draw.text((fc_x, y_forecast), fc_title, font=font_regular, fill=FG_COLOR)
            draw.text((fc_x, y_forecast + 35), fc["condition"], font=font_small, fill=FG_COLOR)
            
    else:
        draw.text((cfg["margin_x"], cfg["weather_temp_y"]), "Dati Meteo Non Disponibili", font=font_regular, fill=FG_COLOR)

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
