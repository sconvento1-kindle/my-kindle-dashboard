import os
import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests

# Costanti di Configurazione per Kindle 10th Gen
WIDTH, HEIGHT = 800, 600
OUTPUT_DIR = "output"
BG_COLOR = 255  # Bianco assoluto
FG_COLOR = 0    # Nero assoluto

def create_dashboard():
    # 1. Inizializza l'immagine in scala di grigi (L = 8-bit pixels, black and white)
    img = Image.new('L', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # 2. Caricamento Font di Sistema (Standard in Ubuntu GitHub Runner)
    try:
        font_large = ImageFont.truetype("DejaVuSans-Bold.ttf", 74)
        font_medium = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        font_regular = ImageFont.truetype("DejaVuSans.ttf", 22)
    except IOError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_regular = ImageFont.load_default()

    # --- SEZIONE 1: OROLOGIO E DATA ---
    now = datetime.datetime.now()
    time_str = now.strftime("%H:%M")
    # Formato data in italiano (es. MERCOLEDÌ 24 GIU 2026)
    days = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    months = ["GEN", "FEB", "MAR", "APR", "MAG", "GIU", "LUG", "AGO", "SET", "OTT", "NOV", "DIC"]
    date_str = f"{days[now.weekday()]} {now.day} {months[now.month-1]} {now.year}"

    # Centra il testo dell'orologio
    w_time = draw.textlength(time_str, font=font_large)
    draw.text(((WIDTH - w_time) / 2, 40), time_str, font=font_large, fill=FG_COLOR)
    
    w_date = draw.textlength(date_str, font=font_medium)
    draw.text(((WIDTH - w_date) / 2, 130), date_str, font=font_medium, fill=FG_COLOR)

    # Linea di separazione
    draw.line([(80, 190), (WIDTH - 80, 190)], fill=FG_COLOR, width=2)

    # --- SEZIONE 2: CALENDARIO (Dati di esempio integrabili con Google API)
    draw.text((80, 220), "IL TUO CALENDARIO", font=font_medium, fill=FG_COLOR)
    
    # TODO: Integrare le chiamate reali a Google Calendar API qui.
    # Usiamo un placeholder pulito per verificare subito il layout
    eventi = [
        "- 15:30: Riunione Progetto E-Ink (30 min)",
        "- Domani, 10:00: Chiamata con Niki (1 hr)",
        "- Ven, 19:00: Calcetto h 19 (1.5 hr)"
    ]
    
    y_offset = 270
    for evento in eventi:
        draw.text((80, y_offset), evento, font=font_regular, fill=FG_COLOR)
        y_offset += 40

    # Linea di separazione
    draw.line([(80, 430), (WIDTH - 80, 430)], fill=FG_COLOR, width=2)

    # --- SEZIONE 3: METEO E PROSSIMI COMPITI ---
    draw.text((80, 460), "METEO SEREGNO", font=font_medium, fill=FG_COLOR)
    draw.text((80, 500), "22°C, Parzialmente Nuvoloso", font=font_regular, fill=FG_COLOR)
    draw.text((80, 535), "🔋 82%   |   🌡️ Interno: 21.5°C", font=font_regular, fill=FG_COLOR)

    # 4. Salva l'immagine ottimizzandola per l'E-Ink (Dithering se necessario)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # Converte in modalità 1-bit (bianco o nero netto) per la massima nitidezza sul Kindle
    img_monochrome = img.convert('1')
    img_monochrome.save(os.path.join(OUTPUT_DIR, "dashboard.png"), "PNG")
    print("Dashboard generata con successo!")

if __name__ == "__main__":
    create_dashboard()
