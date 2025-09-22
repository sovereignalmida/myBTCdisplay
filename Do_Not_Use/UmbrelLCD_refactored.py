#-------------------------------------------------------------------------------
#   The Bitcoin Machine LCD - The Clean Slate
#   Version: 12.0.0
#-------------------------------------------------------------------------------
#   This version adds a hardware "hard reset" sequence before initializing
#   the driver to ensure the display starts in a clean, non-garbled state.
#-------------------------------------------------------------------------------

import time
import datetime
import pathlib
import sys
import requests
from PIL import Image, ImageDraw, ImageFont
from bitcoinrpc.authproxy import AuthServiceProxy
from st7735 import ST7735
import RPi.GPIO as GPIO # Import the low-level GPIO library

# --- CONFIGURATION ---
WIDTH, HEIGHT = 128, 160
RPC_USER = "bitcoinrpc"
RPC_PASS = "Aloha1828108"
DC, RST, SPI_PORT, DEVICE = 24, 25, 0, 0

try:
    CURRENCY = sys.argv[1].upper()
    USER_SCREENS = sys.argv[2]
except IndexError:
    print("Usage: python3 script.py <CURRENCY> <Screen1,Screen2,...>")
    sys.exit(1)


# --- HARDWARE RESET SEQUENCE ---
# This is the new, critical section. It ensures the display is in a clean
# state before the ST7735 driver tries to initialize it.
print("Performing hardware reset...")
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RST, GPIO.OUT)
GPIO.output(RST, GPIO.HIGH)
time.sleep(0.1)
GPIO.output(RST, GPIO.LOW)
time.sleep(0.1)
GPIO.output(RST, GPIO.HIGH)
time.sleep(0.1)
print("Reset complete.")

# --- INITIALIZATION ---
# This now runs after the display has been properly reset.
disp = ST7735(
    port=SPI_PORT, cs=DEVICE, dc=DC, rst=RST,
    rotation=270,
    width=WIDTH, height=HEIGHT,
    spi_speed_hz=4000000,
    bgr=True, invert=False
)
disp.begin()

# --- PATHS ---
BASE_DIR = pathlib.Path(__file__).parent.absolute()
IMAGES_PATH = BASE_DIR / 'images'
FONTS_PATH = BASE_DIR / 'poppins'

# --- DATA FETCHING ---
def get_data():
    """Fetches all data points at once to minimize RPC/API calls."""
    data = {'price': 'N/A', 'height': '...', 'sats': '...'}
    try:
        price_val = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={CURRENCY.lower()}", timeout=10).json()['bitcoin'][CURRENCY.lower()]
        data['price'] = f"${price_val:,}"
        data['sats'] = f"{int(1e8 / price_val):,}"
    except Exception: pass

    try:
        rpc = AuthServiceProxy(f"http://{RPC_USER}:{RPC_PASS}@127.0.0.1:8332", timeout=10)
        data['height'] = f"{rpc.getblockcount():,}"
    except Exception: pass
    
    return data

# --- MODERN, CLEAN DRAWING PRIMITIVES ---
def draw_background(image, filename):
    try:
        with Image.open(IMAGES_PATH / filename) as img:
            bg = img.resize((WIDTH, HEIGHT))
            image.paste(bg, (0, 0))
    except Exception as e:
        print(f"Error drawing background {filename}: {e}")
        ImageDraw.Draw(image).rectangle((0, 0, WIDTH, HEIGHT), fill="black")

def draw_text(draw, text, xy, font_size, align="left", weight="Bold", fill="white"):
    try:
        font = ImageFont.truetype(str(FONTS_PATH / f"Poppins-{weight}.ttf"), font_size)
    except IOError:
        font = ImageFont.load_default()
        
    if align == "right":
        text_width = draw.textlength(text, font=font)
        xy = (WIDTH - text_width - xy[0], xy[1])
    elif align == "center":
        text_width = draw.textlength(text, font=font)
        xy = ((WIDTH - text_width) // 2, xy[1])
    draw.text(xy, text, font=font, fill=fill)

# --- REIMPLEMENTED SCREEN LAYOUTS (FOR 128x160 PORTRAIT) ---
def draw_screen1(image, data):
    draw = ImageDraw.Draw(image)
    draw_background(image, 'Screen1@288x.png')
    draw_text(draw, data['price'], (8, 5), 38)
    draw_text(draw, f"sats / {CURRENCY}", (8, 50), 14)
    draw_text(draw, data['sats'], (8, 68), 38)

def draw_screen3(image, data):
    draw = ImageDraw.Draw(image)
    draw_background(image, 'Block_HeightBG.png')
    draw_text(draw, data['height'], (0, 40), 42, align="center")

def draw_screen4(image, data):
    draw = ImageDraw.Draw(image)
    draw_background(image, 'Screen1@288x.png')
    now = datetime.datetime.now()
    draw_text(draw, now.strftime('%-I:%M %p'), (0, 20), 30, align="center")
    draw_text(draw, now.strftime('%A'), (0, 60), 26, align="center")
    draw_text(draw, now.strftime('%B %d'), (0, 95), 22, align="center")

def draw_placeholder(image, name):
    draw = ImageDraw.Draw(image)
    draw_background(image, 'Block_HeightBG.png')
    draw_text(draw, name, (0, 40), 24, align="center")
    draw_text(draw, "Coming Soon", (0, 70), 16, align="center")

# --- MAIN LOOP ---
if __name__ == '__main__':
    print(f"Starting TBM LCD Script v12.0 (The Clean Slate)")
    print(f"Targeting canvas (WxH): {WIDTH}x{HEIGHT}")

    screen_map = {
        "Screen1": (draw_screen1, 30), "Screen3": (draw_screen3, 30),
        "Screen4": (draw_screen4, 30),
        "Screen2": (lambda img, data: draw_placeholder(img, "Fees"), 10),
        "Screen5": (lambda img, data: draw_placeholder(img, "Network"), 10),
        "Screen6": (lambda img, data: draw_placeholder(img, "Channels"), 10),
        "Screen7": (lambda img, data: draw_placeholder(img, "Storage"), 10),
    }

    cycle = [("Logo", (lambda img, data: draw_background(img, 'umbrel_logo.png'), 10))]
    for screen, action in screen_map.items():
        if screen in USER_SCREENS: cycle.append((screen, action))
    
    data_cache = {}; last_data_fetch = 0

    while True:
        if time.time() - last_data_fetch > 300 or not data_cache:
            print("Fetching fresh data..."); data_cache = get_data(); last_data_fetch = time.time()

        for name, (draw_function, sleep_duration) in cycle:
            print(f"Drawing {name}..."); image = Image.new('RGB', (WIDTH, HEIGHT))
            try:
                draw_function(image, data_cache)
                disp.display(image)
                time.sleep(sleep_duration)
            except KeyboardInterrupt: print("\nExiting."); GPIO.cleanup(); sys.exit(0)
            except Exception as e: print(f"!!! ERROR drawing {name}: {e}"); time.sleep(5)