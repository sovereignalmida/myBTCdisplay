#-------------------------------------------------------------------------------
# Umbrel LCD - Final Assembled & Fully Functional Version
# Version: 12.0.0
#-------------------------------------------------------------------------------
# Python Standard Libraries
import time
import datetime
import subprocess
import os
import sys
import json

# Third-Party Libraries
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from PIL import Image, ImageDraw, ImageFont
import requests

# This will import from the 'st7735' package you installed via pip
from st7735 import ST7735

#-------------------------------------------------------------------------------
# Display configuration
#-------------------------------------------------------------------------------
# This is the most important setting.
# Make sure this is the value that correctly oriented your screen (e.g., 90 or 270).
ROTATION_VALUE = 90 # <--- SET THIS TO YOUR WORKING ROTATION VALUE

disp = ST7735(
    port=0,
    cs=0,
    dc=24,
    rst=25,
    rotation=ROTATION_VALUE,
    invert=False,
    bgr=True
)

WIDTH = disp.width
HEIGHT = disp.height

# Initialize display
disp.begin()

#-------------------------------------------------------------------------------
# RPC setup
#-------------------------------------------------------------------------------
rpc_user = "bitcoinrpc"
rpc_pass = "Aloha1828108"

def get_rpc_connection():
    """Creates and returns a new RPC connection object."""
    try:
        return AuthServiceProxy(f"http://{rpc_user}:{rpc_pass}@127.0.0.1:8332", timeout=120)
    except Exception as e:
        print(f"Error creating RPC connection: {e}")
        return None

#-------------------------------------------------------------------------------
# Paths and args
#-------------------------------------------------------------------------------
base_dir = os.path.abspath(os.path.dirname(__file__))
images_path = os.path.join(base_dir, 'images') + '/'
poppins_fonts_path = os.path.join(base_dir, 'poppins') + '/'

try:
    currency = sys.argv[1].upper()
    userScreenChoices = sys.argv[2]
except IndexError:
    print("Usage: python UmbrelLCD.py <CURRENCY> <Screen1,Screen2,...>")
    sys.exit(1)

#-------------------------------------------------------------------------------
# Utility and Drawing Functions
#-------------------------------------------------------------------------------
def place_value(number): 
    return f"{number:,}" if number is not None else "N/A"

def get_text_size(text, font):
    """Gets text dimensions."""
    bbox = ImageDraw.Draw(Image.new('RGB', (1,1))).textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_text(draw, text, position, font, fill="white", align="left"):
    """Draws text with specified alignment."""
    x, y = position
    if align == "center":
        width, _ = get_text_size(text, font)
        x = (WIDTH - width) // 2
    elif align == "right":
        width, _ = get_text_size(text, font)
        x = WIDTH - width - x
    draw.text((x, y), text, font=font, fill=fill)

def display_background_image(image, name):
    """Draws a background image, handling rotation."""
    try:
        with Image.open(os.path.join(images_path, name)) as bg:
            # The driver handles rotation, so we just resize to the logical dimensions
            bg_final = bg.resize((WIDTH, HEIGHT))
            image.paste(bg_final, (0,0))
    except FileNotFoundError:
        print(f"Background not found: {name}")
        ImageDraw.Draw(image).rectangle((0,0,WIDTH,HEIGHT), fill="black")

def display_icon(image, image_path, position, icon_size):
    """Draws an icon without rotation."""
    try:
        with Image.open(image_path) as picimage:
            picimage = picimage.convert('RGBA')
            picimage = picimage.resize((icon_size, icon_size), Image.BICUBIC)
            image.paste(picimage, position, picimage)
    except FileNotFoundError:
        print(f"Icon not found: {image_path}")

#-------------------------------------------------------------------------------
# Data Fetching Functions (with error handling)
#-------------------------------------------------------------------------------
def get_rpc_data(method, *params):
    rpc = get_rpc_connection()
    if not rpc: return None
    try:
        return rpc.__call__(method, *params)
    except Exception as e:
        print(f"RPC Error calling '{method}': {e}")
        return None

def get_btc_price(curr):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={curr.lower()}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        price_data = r.json()
        return int(price_data['bitcoin'][curr.lower()])
    except Exception as e:
        print(f"Error getting price: {e}")
        return 0

def get_disk_storage_info():
    try:
        df = subprocess.check_output(['df', '-h', '/']).decode('utf-8').splitlines()[1].split()
        return {"total": df[1], "used": df[2], "avail": df[3], "pct": int(df[4].replace('%', ''))}
    except Exception:
        return {"total": "N/A", "used": "N/A", "avail": "N/A", "pct": 0}

#-------------------------------------------------------------------------------
# Screen Drawing Functions
#-------------------------------------------------------------------------------
def draw_screen1(image):
    draw = ImageDraw.Draw(image)
    display_background_image(image, 'Screen1@288x.png')

    # --- Get Data ---
    price = get_btc_price(currency)
    price_str = place_value(price) if price else "N/A"
    sats_str = place_value(int(1e8 / price)) if price else "N/A"
    try:
        temp_result = subprocess.run(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE, check=True).stdout.decode('utf-8')
        temperature = temp_result.split('=')[1].strip()
    except Exception:
        temperature = "N/A"
    
    # --- Define Fonts (Smaller) ---
    font_vals = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 32)
    font_currency = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 12)
    font_footer = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 12)

    # --- Draw Elements with Adjusted Y-coordinates ---
    # Top right currency
    draw_text(draw, currency, (5, 5), font_currency, align="right")

    # Row 1: Price
    display_icon(image, os.path.join(images_path, 'bitcoin_seeklogo.png'), (5, 15), 40)
    draw.text((55, 15), price_str, font=font_vals, fill="white")
    
    # Row 2: Sats
    display_icon(image, os.path.join(images_path, 'Satoshi_regular_elipse.png'), (5, 75), 40)
    draw.text((55, 75), sats_str, font=font_vals, fill="white")

    # Row 3: Footer Labels
    draw.text((5, 130), f"SATS / {currency}", font=font_footer, fill="white")
    draw_text(draw, temperature, (5, 130), font_footer, align="right")

def draw_screen2(image): # Fees & Transactions
    draw = ImageDraw.Draw(image)
    display_background_image(image, 'TxsBG.png')

    # Get Data (with fallback for syncing node)
    mempool = get_rpc_data('getmempoolinfo')
    unconfirmed_txs = place_value(mempool.get('size')) if mempool else "..."
    
    fees = get_rpc_data('estimatesmartfee', 1) # High priority fee
    high_fee = "..."
    if fees and fees.get('feerate'):
        high_fee = f"~{round(fees['feerate'] * 1e8 / 1000)}"

    low_fees = get_rpc_data('estimatesmartfee', 6) # Medium priority fee
    low_fee = "..."
    if low_fees and low_fees.get('feerate'):
        low_fee = f"~{round(low_fees['feerate'] * 1e8 / 1000)}"

    # Define Fonts
    font_l = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 34)
    font_m = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 22)
    font_s = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 12)

    # Draw Elements based on reference image
    # Top Section: Unconfirmed Txs
    draw_text(draw, "Mempool", (0, 8), font_s, align="center")
    draw_text(draw, unconfirmed_txs, (0, 22), font_l, align="center")
    draw_text(draw, "Transactions", (0, 60), font_s, align="center")

    # Bottom Section: Fees
    draw_text(draw, "High Pri", (35, 90), font_s, align="center")
    draw_text(draw, high_fee, (35, 105), font_m, align="center")
    
    draw_text(draw, "Med Pri", (93, 90), font_s, align="center")
    draw_text(draw, low_fee, (93, 105), font_m, align="center")

    draw_text(draw, "sat/vB", (0, 135), font_s, align="center")

def draw_screen3(image): # Block Height
    draw = ImageDraw.Draw(image)
    display_background_image(image, 'Block_HeightBG.png')
    block_count = place_value(get_rpc_data('getblockcount'))
    font = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 40)
    draw_text(draw, block_count, (0, (HEIGHT - 40) // 2), font, align="center")

def draw_screen4(image): # Time
    draw = ImageDraw.Draw(image)
    display_background_image(image, 'Screen1@288x.png')
    now = datetime.datetime.now()
    time_str = now.strftime('%-I:%M %p')
    day_str = now.strftime('%A')
    month_str = now.strftime('%B %d')

    font_time = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 30)
    font_day = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 26)
    font_month = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 22)

    draw_text(draw, time_str, (0, 20), font_time, align="center")
    draw_text(draw, day_str, (0, 60), font_day, align="center")
    draw_text(draw, month_str, (0, 95), font_month, align="center")

def draw_screen5(image): # Network Info
    draw = ImageDraw.Draw(image)
    display_background_image(image, 'network.png')
    font = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 16)
    
    peers = get_rpc_data('getconnectioncount')
    draw_text(draw, "Peers", (0, 20), font, align="center")
    draw_text(draw, place_value(peers), (0, 40), font, align="center")
    
    info = get_rpc_data('getblockchaininfo')
    chain_size = "Syncing..."
    if info:
        chain_size = f"{info['size_on_disk'] / 1e9:.2f} GB"

    draw_text(draw, "Chain Size", (0, 90), font, align="center")
    draw_text(draw, chain_size, (0, 110), font, align="center")

def draw_screen7(image): # Storage Info
    draw = ImageDraw.Draw(image)
    display_background_image(image, 'storage.png')
    info = get_disk_storage_info()
    pct = info['pct']
    
    font_l = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 22)
    font_s = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 14)
    
    draw_text(draw, f"Disk Usage: {pct}%", (0, 20), font_l, align="center")
    draw_text(draw, f"Used: {info['used']}", (10, 60), font_s)
    draw_text(draw, f"Avail: {info['avail']}", (10, 80), font_s)
    draw_text(draw, f"Total: {info['total']}", (10, 100), font_s)

    # Progress bar
    bar_x, bar_y, bar_w, bar_h = 10, 130, 108, 15
    draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), outline="white", fill="black")
    fill_w = (bar_w / 100) * pct
    draw.rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), outline="white", fill="#FFA500")

def draw_screen_placeholder(image, screen_name):
    """A placeholder for screens that are not fully implemented yet."""
    draw = ImageDraw.Draw(image)
    display_background_image(image, 'Screen1@288x.png')
    font = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 18)
    draw_text(draw, screen_name, (0, 40), font, align="center")
    draw_text(draw, "(Not Available)", (0, 70), font, align="center")    

#-------------------------------------------------------------------------------
# Main loop
#-------------------------------------------------------------------------------
print("Starting Umbrel LCD...")

# Show the startup logo
image = Image.new("RGB", (WIDTH, HEIGHT))
display_background_image(image, 'umbrel_logo.png')
disp.display(image)
time.sleep(10)

# Map screen names to their drawing functions
screen_draw_map = {
    "Screen1": draw_screen1,
    "Screen2": draw_screen2,
    "Screen3": draw_screen3,
    "Screen4": draw_screen4,
    "Screen5": draw_screen5,
    "Screen6": lambda img: draw_screen_placeholder(img, "LND Channels"),
    "Screen7": draw_screen7,
}

while True:
    for screen_name, draw_func in screen_draw_map.items():
        if screen_name in userScreenChoices:
            try:
                print(f"Drawing {screen_name}...")
                image_buffer = Image.new("RGB", (WIDTH, HEIGHT))
                
                draw_func(image_buffer)
                
                disp.display(image_buffer)
                time.sleep(30)

            except Exception as e:
                print(f"FATAL: An error occurred while drawing {screen_name}: {e}")
                time.sleep(10)