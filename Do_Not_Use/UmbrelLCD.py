#-------------------------------------------------------------------------------
# Umbrel LCD - Final Portrait Version
# Version: 15.0.0
#-------------------------------------------------------------------------------
import time
import datetime
import subprocess
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import requests
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from st7735 import ST7735

#-------------------------------------------------------------------------------
# Display configuration
#-------------------------------------------------------------------------------
ROTATION_VALUE = 90  # <--- SET THIS TO 90

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

disp.begin()

#-------------------------------------------------------------------------------
# RPC setup
#-------------------------------------------------------------------------------
rpc_user = "bitcoinrpc"
rpc_pass = "Aloha1828108"

def get_rpc_connection():
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
# Utility and Drawing Functions for Portrait Mode
#-------------------------------------------------------------------------------
def place_value(number): 
    return f"{number:,}" if number is not None else "N/A"

def draw_text(draw, text, position, font, fill="white", align="left"):
    x, y = position
    if align == "center":
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
    elif align == "right":
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = WIDTH - text_width - x
    draw.text((x, y), text, font=font, fill=fill)

def display_background_image(image, name):
    try:
        with Image.open(os.path.join(images_path, name)) as bg:
            # The original assets are landscape, so we resize and rotate them for our portrait buffer
            bg_final = bg.resize((WIDTH, HEIGHT))#.rotate(0, expand=True)
            image.paste(bg_final, (0,0))

    except FileNotFoundError:
        print(f"Background not found: {name}")
        ImageDraw.Draw(image).rectangle((0,0,WIDTH,HEIGHT), fill="black")

def display_icon(image, image_path, position):
    try:
        with Image.open(image_path) as picimage:
            pic_rgba = picimage.convert("RGBA")                 # ← force RGBA
            rotated_icon = pic_rgba.rotate(270, expand=True)
            image.paste(rotated_icon, position, rotated_icon)
            icon = picimage.convert("RGBA")
            icon = icon.resize((27, 27), Image.LANCZOS)
            icon = icon.rotate(90, expand=True)
            image.paste(icon, position, icon)
    except FileNotFoundError:
        print(f"Icon not found: {image_path}")

#-------------------------------------------------------------------------------
# Data Fetching Functions
#-------------------------------------------------------------------------------
def get_btc_price(curr):
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={curr.lower()}", timeout=10)
        return int(r.json()['bitcoin'][curr.lower()])
    except: return 0

def get_block_count():
    rpc = get_rpc_connection(); return str(rpc.getblockcount()) if rpc else "..."
    
def get_temperature():
    try:
        temp_result = subprocess.run(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE, check=True).stdout.decode('utf-8')
        return temp_result.split('=')[1].strip("'C\n")
    except: return "N/A"

#-------------------------------------------------------------------------------
# Screen Drawing Functions for Portrait Mode
#-------------------------------------------------------------------------------
def draw_screen1(image):
    draw = ImageDraw.Draw(image)
    # 1) draw the rotated background
    display_background_image(image, 'Screen1@288x.png')

    # 2) fetch data
    price = get_btc_price(currency)
    price_str = place_value(price) if price else "N/A"
    sats_per_usd = int(1e8 / price) if price else 0
    sats_str = place_value(sats_per_usd)
    temperature = get_temperature() + "’C"

    # 3) fonts
    font_price = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 32)
    font_footer = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 12)

    # 4) currency code, top right
    draw_text(draw, currency, (5, 5), font_footer, align="right")

    # 5) icons (you may need to tweak their coordinates slightly)
    display_icon(image,
                 os.path.join(images_path, 'bitcoin_seeklogo.png'),
                 (5, 10))
    display_icon(image,
                 os.path.join(images_path, 'Satoshi_regular_elipse.png'),
                 (5, 70))

    # 6) price and sats, centered
    draw_text(draw, price_str, (0, 10), font_price, align="center")
    draw_text(draw, sats_str,  (0, 70), font_price, align="center")

    # 7) footer: left = “SATS/USD”, right = temp
    draw_text(draw, f"SATS/{currency}", (5, 135), font_footer, align="left")
    draw_text(draw, temperature,       (5, 125), font_footer, align="right")



def draw_screen_placeholder(image, screen_name):
    draw = ImageDraw.Draw(image)
    display_background_image(image, 'Screen1@288x.png')
    font = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 18)
    draw_text(draw, screen_name, (0, 40), font, align="center")
    draw_text(draw, "To be implemented", (0, 70), font, align="center")

#-------------------------------------------------------------------------------
# Main loop
#-------------------------------------------------------------------------------
print("Starting Umbrel LCD...")

# Map screen names to their drawing functions
screen_draw_map = {
    "Screen1": draw_screen1,
    # Add other final screen functions here as we build them
    "Screen2": lambda img: draw_screen_placeholder(img, "Fees"),
    "Screen3": lambda img: draw_screen_placeholder(img, "Block Height"),
    "Screen4": lambda img: draw_screen_placeholder(img, "Time"),
    "Screen5": lambda img: draw_screen_placeholder(img, "Network"),
    "Screen6": lambda img: draw_screen_placeholder(img, "Channels"),
    "Screen7": lambda img: draw_screen_placeholder(img, "Storage"),
}

# Initial logo screen
image_buffer = Image.new("RGB", (WIDTH, HEIGHT))
display_background_image(image_buffer, 'umbrel_logo.png')
disp.display(image_buffer)
time.sleep(10)

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