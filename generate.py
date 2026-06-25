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
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID")
    creds_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")
    
    if not calendar_id or not creds_json:
        return ["- Errore: Secrets non configurati su GitHub"]
    
    try:
        # Carica le credenziali dal Secret JSON
        creds_data = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)
        
        # Prende il tempo attuale in UTC per la richiesta API
        now_utc = datetime.datetime.utcnow().isoformat() + 'Z'
        
        # Richiede i prossimi 3 eventi
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
