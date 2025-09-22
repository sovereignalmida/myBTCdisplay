#-------------------------------------------------------------------------------
# Umbrel LCD - Final Working Version
# Version: 10.0.0
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

# This will now import from the 'st7735' package you installed via pip
from st7735 import ST7735

#-------------------------------------------------------------------------------
# Display configuration
#-------------------------------------------------------------------------------
# You found the correct rotation value in the last step.
# Make sure this value is set correctly (e.g., 90 or 270).
ROTATION_VALUE = 90 # <--- SET THIS TO YOUR WORKING ROTATION VALUE

disp = ST7735(
    port=0,
    cs=0,
    dc=24,
    rst=25,
    rotation=ROTATION_VALUE,
    invert=False,
    bgr=True  # Correct parameter for color order
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
    currency = sys.argv[1]
    userScreenChoices = sys.argv[2]
except IndexError:
    print("Usage: python UmbrelLCD.py <CURRENCY> <Screen1,Screen2,...>")
    sys.exit(1)

#-------------------------------------------------------------------------------
# Utility and Drawing Functions
#-------------------------------------------------------------------------------
def place_value(number): 
    return f"{number:,}"

def get_text_size(text, font):
    """Gets text dimensions."""
    bbox = ImageDraw.Draw(Image.new('RGB', (1,1))).textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_rotated_text(image, text, position, angle, font, fill=(255,255,255)):
    """Draws rotated text onto an image buffer."""
    draw = ImageDraw.Draw(image)
    width, height = get_text_size(text, font)
    
    text_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_image)
    text_draw.text((0, 0), text, font=font, fill=fill)

    rotated = text_image.rotate(angle, expand=True)
    image.paste(rotated, position, rotated)

def display_background(image, name):
    """Draws a background image, handling rotation."""
    try:
        with Image.open(os.path.join(images_path, name)) as bg:
            # The driver expects a pre-rotated buffer, so we rotate assets in software.
            # Assuming a portrait final display (e.g. 128x160) and landscape assets (e.g. 160x128)
            if WIDTH < HEIGHT: # Portrait mode
                bg_resized = bg.resize((HEIGHT, WIDTH))
                bg_final = bg_resized.rotate(270, expand=True)
            else: # Landscape mode
                bg_final = bg.resize((WIDTH, HEIGHT))

            image.paste(bg_final, (0,0))
    except FileNotFoundError:
        print(f"Background not found: {name}")
        ImageDraw.Draw(image).rectangle((0,0,WIDTH,HEIGHT), fill="black")

#-------------------------------------------------------------------------------
# Data Fetching Functions
#-------------------------------------------------------------------------------
def get_block_count():
    rpc = get_rpc_connection()
    if not rpc: return "..."
    try:
        return str(rpc.getblockcount())
    except Exception as e:
        print(f"Error in get_block_count: {e}")
        return "..."

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

# NOTE: LND and some other functions from the original script that relied on Docker
# have been removed as they are not applicable to your current setup.
# They can be re-added if you install those services.

#-------------------------------------------------------------------------------
# Screen Drawing Functions
#-------------------------------------------------------------------------------
def draw_screen1(image, draw): # Price Screen
    display_background(image, 'Screen1@288x.png')
    price = get_btc_price(currency)
    price_str = place_value(price) if price else "N/A"
    sats_str = place_value(int(1e8 / price)) if price else "N/A"
    
    # This drawing logic is from the original script, adapted for portrait mode
    font_price = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 38)
    font_sats = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 38)
    font_currency = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 14)
    font_sats_label = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 14)

    draw.text((10, 10), f"${price_str}", font=font_price, fill="white")
    draw.text((10, 20 + 38), f"sats/${currency}", font=font_sats_label, fill="white")
    draw.text((10, 20 + 38 + 14), sats_str, font=font_sats, fill="white")


def draw_screen3(image, draw): # Block Height
    display_background(image, 'Block_HeightBG.png')
    block_count = get_block_count()
    font = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 40)
    w, h = get_text_size(block_count, font)
    draw.text(((WIDTH - w) / 2, (HEIGHT - h) / 2), block_count, font=font, fill="white")


def draw_screen4(image, draw): # Time
    display_background(image, 'Screen1@288x.png')
    now = datetime.datetime.now()
    time_str = now.strftime('%-I:%M %p')
    day_str = now.strftime('%A')
    month_str = now.strftime('%B %d')

    font_time = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 30)
    font_day = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 26)
    font_month = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 22)

    w, _ = get_text_size(time_str, font_time)
    draw.text(((WIDTH - w) / 2, 20), time_str, font=font_time, fill="white")
    w, _ = get_text_size(day_str, font_day)
    draw.text(((WIDTH - w) / 2, 60), day_str, font=font_day, fill="white")
    w, _ = get_text_size(month_str, font_month)
    draw.text(((WIDTH - w) / 2, 95), month_str, font=font_month, fill="white")


def draw_screen_placeholder(image, draw, screen_name): # Placeholder
    """A placeholder for screens that are not fully implemented yet."""
    draw.rectangle((0,0,WIDTH,HEIGHT), fill="black")
    font = ImageFont.truetype(poppins_fonts_path + "Poppins-Bold.ttf", 18)
    w, h = get_text_size(screen_name, font)
    draw.text(((WIDTH - w) / 2, (HEIGHT / 2) - 20), screen_name, font=font, fill="white")
    w, h = get_text_size("Syncing...", font)
    draw.text(((WIDTH - w) / 2, (HEIGHT / 2) + 10), "Syncing...", font=font, fill="white")


#-------------------------------------------------------------------------------
# Main loop
#-------------------------------------------------------------------------------
print("Starting Umbrel LCD...")

# Show the startup logo
image = Image.new("RGB", (WIDTH, HEIGHT))
display_background(image, 'umbrel_logo.png')
disp.display(image)
time.sleep(10)

while True:
    # A dictionary mapping screen names to their drawing functions
    screen_draw_map = {
        "Screen1": draw_screen1,
        "Screen2": lambda img, drw: draw_screen_placeholder(img, drw, "Fees"),
        "Screen3": draw_screen3,
        "Screen4": draw_screen4,
        "Screen5": lambda img, drw: draw_screen_placeholder(img, drw, "Network"),
        "Screen6": lambda img, drw: draw_screen_placeholder(img, drw, "Channels"),
        "Screen7": lambda img, drw: draw_screen_placeholder(img, drw, "Storage"),
    }
    
    for screen_name, draw_func in screen_draw_map.items():
        if screen_name in userScreenChoices:
            try:
                print(f"Drawing {screen_name}...")
                # Create a fresh buffer for each screen
                image_buffer = Image.new("RGB", (WIDTH, HEIGHT))
                draw_context = ImageDraw.Draw(image_buffer)

                # Call the specific drawing function
                if screen_name == "Screen1":
                    draw_func(image_buffer, draw_context) # Assumes draw_screen1 handles currency
                else:
                    draw_func(image_buffer, draw_context)
                
                # Display the completed buffer
                disp.display(image_buffer)
                time.sleep(30) # Display each screen for 30 seconds

            except Exception as e:
                print(f"FATAL: An error occurred while drawing {screen_name}: {e}")
                time.sleep(10)