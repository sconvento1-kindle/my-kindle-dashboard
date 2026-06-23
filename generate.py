# --- BULLETPROOF FONT LOADING ---
import glob

# Search the GitHub server for any standard true type font
system_fonts = glob.glob("/usr/share/fonts/truetype/**/*.ttf", recursive=True)
selected_font = None

for f in system_fonts:
    if "LiberationSans-Bold" in f or "DejaVuSans-Bold" in f:
        selected_font = f
        break

# Fallback to the first available system font if our favorites aren't there
if not selected_font and system_fonts:
    selected_font = system_fonts[0]

try:
    if selected_font:
        font_large = ImageFont.truetype(selected_font, 110)   # Giant Clock
        font_medium = ImageFont.truetype(selected_font, 45)   # Subheaders
        font_small = ImageFont.truetype(selected_font, 32)    # Agenda items
    else:
        raise IOError
except Exception:
    # Absolute emergency fallback
    font_large = font_medium = font_small = ImageFont.load_default()
