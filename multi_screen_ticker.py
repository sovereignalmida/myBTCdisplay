import time
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7735 as st7735r
import requests
import json

# --- Configuration ---
RPC_USER = ""
RPC_PASS = "aloha108"
LOGO_PATH = "/home/casaroot/TBM_LCD_FIXED/images/penguinLogo.png"

cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)
BAUDRATE = 24000000

# Backlight control
backlight = digitalio.DigitalInOut(board.D18)
backlight.direction = digitalio.Direction.OUTPUT
backlight.value = True

# Setup SPI bus
spi = board.SPI()

# Create the ST7735R display object
disp = st7735r.ST7735R(
    spi, cs=cs_pin, dc=dc_pin, rst=reset_pin,
    baudrate=BAUDRATE, bgr=True, rotation=90, invert=True,
)

# Font and color settings
font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
WHITE = "#FFFFFF"

# --- Data Fetching Function ---
def get_btc_price(currency="USD"):
    url = "http://192.168.1.116:3002/api/price"
    try:
        response = requests.get(url, auth=(RPC_USER, RPC_PASS), timeout=5)
        response.raise_for_status()
        data = response.json()
        price_value = data.get(currency.lower())

        if price_value is not None:
            price_float = float(price_value)
            return f"${price_float:,.0f}"
        else:
            return "Error"
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return "Error"

# --- Screen Drawing Functions ---

def get_display_dims():
    """Gets the correct width and height based on rotation."""
    if disp.rotation % 180 == 90:
        return disp.height, disp.width
    return disp.width, disp.height

def draw_logo_screen():
    """Draws the logo screen."""
    width, height = get_display_dims()
    image = Image.new("RGB", (width, height))

    try:
        logo = Image.open(LOGO_PATH).convert("RGB")
        # Resize the logo to fit the display
        logo = logo.resize((width, height))
        image.paste(logo, (0, 0))
    except FileNotFoundError:
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, height), outline=0, fill="black")
        draw.text((10, 10), "Logo Not Found", font=font_medium, fill="red")

    disp.image(image)

def draw_price_screen(price):
    """Draws the price and other info onto the display."""
    width, height = get_display_dims()
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, height), outline=0, fill="black")

    draw.text((10, 5), "BTC Price (USD)", font=font_medium, fill=WHITE)

    price_bbox = draw.textbbox((0, 0), price, font=font_large)
    price_width = price_bbox[2] - price_bbox[0]
    price_height = price_bbox[3] - price_bbox[1]
    price_x = (width - price_width) // 2
    price_y = (height - price_height) // 2
    draw.text((price_x, price_y), price, font=font_large, fill=WHITE)

    current_time = time.strftime("%H:%M:%S")
    draw.text((10, height - 20), current_time, font=font_small, fill=WHITE)

    disp.image(image)

# --- UPDATED Main Loop ---
print("Multi-screen ticker starting. Press Ctrl+C to exit.")
while True:
    try:
        # --- Show Logo Screen ---
        print("Displaying logo screen...")
        draw_logo_screen()
        time.sleep(15)  # Show for 15 seconds

        # --- Show Price Screen ---
        print("Displaying price screen...")
        btc_price = get_btc_price("USD")
        print(f"Current Price: {btc_price}")
        draw_price_screen(btc_price)
        time.sleep(45)  # Show for 45 seconds

    except KeyboardInterrupt:
        print("\nExiting.")
        break
    except Exception as e:
        print(f"An error occurred in the main loop: {e}")
        time.sleep(30)
