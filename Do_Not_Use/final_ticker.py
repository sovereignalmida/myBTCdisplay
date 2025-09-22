import time
import subprocess
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7735 as st7735r

# --- FINAL Configuration ---
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

# Create the ST7735R display object with the color fix (bgr=True)
disp = st7735r.ST7735R(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    bgr=True, # This fixes the red/blue color swap!
    rotation=90,
)

# Font and color settings
font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
WHITE = "#FFFFFF"

# --- Main Functions ---

def get_btc_price(currency="USD"):
    """Fetches the current BTC price from the CASA_RPCEXPLORER container."""
    try:
        cmd = f"docker exec CASA_RPCEXPLORER /usr/bin/node /app/api/price.js {currency}"
        price_str = subprocess.check_output(cmd, shell=True, text=True).strip()
        price_float = float(price_str)
        return f"${price_float:,.0f}"
    except Exception:
        # If the command fails for any reason, return "Error"
        return "Error"

def draw_screen(price):
    """Draws the price and other info onto the display."""
    # Get the display's dimensions
    if disp.rotation % 180 == 90:
        height = disp.width
        width = disp.height
    else:
        width = disp.width
        height = disp.height

    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, height), outline=0, fill="black")

    # --- Layout ---
    # "BTC Price (USD)" - Top
    draw.text((10, 5), "BTC Price (USD)", font=font_medium, fill=WHITE)

    # The Price - Center
    price_bbox = draw.textbbox((0, 0), price, font=font_large)
    price_width = price_bbox[2] - price_bbox[0]
    price_height = price_bbox[3] - price_bbox[1]
    price_x = (width - price_width) // 2
    price_y = (height - price_height) // 2
    draw.text((price_x, price_y), price, font=font_large, fill=WHITE)

    # Current Time - Bottom Left
    current_time = time.strftime("%H:%M:%S")
    draw.text((10, height - 20), current_time, font=font_small, fill=WHITE)

    # Display the image
    disp.image(image)

# --- Main Loop ---

print("Final ticker starting. Press Ctrl+C to exit.")
while True:
    try:
        btc_price = get_btc_price("USD")
        print(f"Current Price: {btc_price}")
        draw_screen(btc_price)
        time.sleep(60) # Update every 60 seconds
    except KeyboardInterrupt:
        print("\nExiting.")
        break
    except Exception as e:
        print(f"An error occurred in the main loop: {e}")
        time.sleep(30)
