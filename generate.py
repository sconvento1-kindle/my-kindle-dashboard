import os
import datetime
import json
from PIL import Image, ImageDraw, ImageFont
import requests
import pytz
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Costanti di Configurazione per Kindle 10th Gen
WIDTH, HEIGHT = 800, 600
OUTPUT_DIR = "output"
BG_COLOR = 255  # Bianco assoluto
FG_COLOR = 0    # Nero assoluto

def get_real_weather():
    """Recupera i dati meteo reali per Seregno usando l'API gratuita di Open-Meteo"""
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
    """Scarica i prossimi 3 eventi reali da Google Calendar usando il Service Account"""
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID")
    creds_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")
    
    if not calendar_id or not creds_json:
        return ["- Errore: Secrets non configurati"]
    
    # Struttura lineare senza try/except annidati che confondono l'editor di GitHub
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
    # 1. Inizializza l'immagine in scala di grigi
    img = Image.new('L', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # 2. Caricamento Font di Sistema
    try:
        font_large = ImageFont.truetype("DejaVuSans-Bold.ttf", 74)
        font_medium = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        font_regular = ImageFont.truetype("DejaVuSans.ttf", 22)
    except IOError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_regular = ImageFont.load_default()

    # --- SEZIONE 1: OROLOGIO E DATA ---
    fuso_orario = pytz.timezone('Europe/Rome')
    now = datetime.datetime.now(fuso_orario)
    
    time_str = now.strftime("%H:%M")
    days = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    months = ["GEN", "FEB", "MAR", "APR", "MAG", "GIU", "LUG", "AGO", "SET", "OTT", "NOV", "DIC"]
    date_str = f"{days[now.weekday()]} {now.day} {months[now.month-1]} {now.year}"

    w_time = draw.textlength(time_str, font=font_large)
    draw.text(((WIDTH - w_time) / 2, 40), time_str, font=font_large, fill=FG_COLOR)
    
    w_date = draw.textlength(date_str, font=font_medium)
    draw.text(((WIDTH - w_date) / 2, 130), date_str, font=font_medium, fill=FG_COLOR)

    draw.line([(80, 190), (WIDTH - 80, 190)], fill=FG_COLOR, width=2)

    # --- SEZIONE 2: VERO CALENDARIO GOOGLE ---
    draw.text((80, 220), "IL TUO CALENDARIO", font=font_medium, fill=FG_COLOR)
    
    try:
        eventi = get_google_calendar_events()
    except Exception as e:
        print(f"Errore generale: {e}")
        eventi = ["- Impossibile leggere il calendario"]
    
    y_offset = 270
    for evento in eventi:
        if len(evento) > 55:
            evento = evento[:52] + "..."
        draw.text((80, y_offset), evento, font=font_regular, fill=FG_COLOR)
        y_offset += 40

    draw.line([(80, 430), (WIDTH - 80, 430)], fill=FG_COLOR, width=2)

    # --- SEZIONE 3: METEO REALE DI SEREGNO ---
    weather_info = get_real_weather()
    
    draw.text((80, 455), "METEO SEREGNO", font=font_medium, fill=FG_COLOR)
    draw.text((80, 500), weather_info, font=font_regular, fill=FG_COLOR)
    draw.text((80, 540), "🔋 82%   |   Temp. Esterna", font=font_regular, fill=FG_COLOR)

    # 4. Salva l'immagine
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    img_monochrome = img.convert('1')
    img_monochrome.save(os.path.join(OUTPUT_DIR, "dashboard.png"), "PNG")
    
    print(f"Dashboard generata con successo alle ore: {time_str} del {date_str}")

if __name__ == "__main__":
    create_dashboard()
