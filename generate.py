from PIL import Image, ImageDraw, ImageFont
import datetime

# 1. Define Kindle screen dimensions (Portrait layout)
WIDTH, HEIGHT = 1080, 1440
BLACK = 0  # 8-bit grayscale black
WHITE = 255  # 8-bit grayscale white

# 2. Create a blank white canvas (L mode = 8-bit pixels, black and white)
image = Image.new("L", (WIDTH, HEIGHT), WHITE)
draw = ImageDraw.Draw(image)

# 3. Load clean, readable system fonts (adjust sizes for high-contrast visibility)
try:
    font_large = ImageFont.truetype("Arial.ttf", 90)  # For the time
    font_medium = ImageFont.truetype("Arial.ttf", 40)  # For dates & weather headline
    font_small = ImageFont.truetype("Arial.ttf", 28)  # For calendar items
except IOError:
    # Fallback to default if Arial isn't available in your GitHub action environment
    font_large = font_medium = font_small = ImageFont.load_default()

# --- DESIGN LAYOUT ---

# Top Border Line
draw.line([(50, 40), (WIDTH - 50, 40)], fill=BLACK, width=4)

# Section Split: Horizontal line separating Header from Calendar
draw.line([(50, 320), (WIDTH - 50, 320)], fill=BLACK, width=3)

# Section Split: Vertical line separating Time from Weather
draw.line([(WIDTH // 2, 40), (WIDTH // 2, 320)], fill=BLACK, width=2)

# --- DRAW DATA ---

# Fetch current time variables
now = datetime.datetime.now()
time_string = now.strftime("%H:%M")
date_string = now.strftime("%A, %B %d")

# Place Time & Date (Left Header Block)
draw.text((80, 80), time_string, fill=BLACK, font=font_large)
draw.text((80, 210), date_string, fill=BLACK, font=font_medium)

# Placeholder Weather Data (Right Header Block)
draw.text((WIDTH // 2 + 50, 90), "Seregno, IT", fill=BLACK, font=font_medium)
draw.text((WIDTH // 2 + 50, 160), "24°C • Sunny", fill=BLACK, font=font_medium)
draw.text(
    (WIDTH // 2 + 50, 220), "H: 26° L: 14°", fill=BLACK, font=font_small
)

# Placeholder Calendar Section (Bottom Block)
draw.text((80, 370), "UPCOMING EVENTS", fill=BLACK, font=font_medium)
draw.line([(80, 430), (450, 430)], fill=BLACK, width=2)

events = [
    "[17:00] Account Surfaces Review Meeting",
    "[18:30] Walk Zoe and Stache 🐾",
    "[20:00] Dinner with team",
]

y_offset = 480
for event in events:
    draw.text((80, y_offset), event, fill=BLACK, font=font_small)
    y_offset += 65

# --- SAVE IMAGE ---
image.save("dashboard.png", "PNG")
print("Dashboard blueprint generated successfully!")
