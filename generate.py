import os
import datetime
import json
from PIL import Image, ImageDraw, ImageFont
import requests
import pytz
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

WIDTH, HEIGHT = 800, 600
OUTPUT_DIR = "output"
BG_COLOR = 255
FG_COLOR = 0

def get_real_weather():
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
    
    try:
        font_large = ImageFont.truetype("DejaVuSans-Bold.ttf", 74)
        font_medium = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        font_regular = ImageFont.truetype("DejaVuSans.ttf", 22)
    except IOError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_regular = ImageFont.load_default()

    fuso_orario = pytz.timezone('Europe/Rome')
    now = datetime.datetime.now(fuso_orario)
    
    time_str = now.strftime("%H:%M")
    days = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    months =
